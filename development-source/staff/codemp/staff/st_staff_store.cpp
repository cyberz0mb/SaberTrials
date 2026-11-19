#include "st_staff_store.h"
#include <sqlite3.h>
#ifdef _WIN32
#include <windows.h>
#else
#include "st_private_linux.h"
#include <sys/stat.h>
#include <cerrno>
#endif
namespace st {
namespace {
struct Statement {
 sqlite3_stmt* p=nullptr;
 Statement(sqlite3* db,const char* sql){if(db)sqlite3_prepare_v2(db,sql,-1,&p,nullptr);}
 ~Statement(){sqlite3_finalize(p);}
 void Text(int i,const std::string& s){sqlite3_bind_text(p,i,s.c_str(),(int)s.size(),SQLITE_TRANSIENT);}
};
std::string Text(sqlite3_stmt* p,int col){auto s=sqlite3_column_text(p,col);return s?(const char*)s:"";}
Account Row(sqlite3_stmt* p){Account a;a.id=Text(p,0);a.label=Text(p,1);a.role=(Role)sqlite3_column_int(p,2);a.enabled=sqlite3_column_int(p,3)!=0;a.revision=(uint64_t)sqlite3_column_int64(p,4);return a;}
}
Store::~Store(){Close();}
void Store::Close(){if(db_)sqlite3_close_v2(db_);db_=nullptr;}
bool Store::Sql(const char* sql){if(!db_)return false;char* err=nullptr;int rc=sqlite3_exec(db_,sql,nullptr,nullptr,&err);if(rc!=SQLITE_OK){error_=err?err:"Database error";sqlite3_free(err);return false;}return true;}
bool Store::Open(const std::string& path){
 Close();error_.clear();
 // GetFileAttributesW avoids lossy paths. An existing empty/corrupt DB is never initialized.
#ifdef _WIN32
 int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path.c_str(),-1,NULL,0);if(!n)return false;std::wstring w(n,0);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path.c_str(),-1,&w[0],n);
 DWORD attr=GetFileAttributesW(w.c_str());bool exists=attr!=INVALID_FILE_ATTRIBUTES;
 if(exists&&(attr&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY)))return false;
 if(!exists&&GetLastError()!=ERROR_FILE_NOT_FOUND)return false;
#else
 struct stat info{};bool exists=lstat(path.c_str(),&info)==0;
 if(exists&&!PrivateFile(path))return false;
 if(!exists&&(errno!=ENOENT||!PrivateWrite(path,{},false)))return false;
#endif
 if(sqlite3_open_v2(path.c_str(),&db_,SQLITE_OPEN_READWRITE|(exists?0:SQLITE_OPEN_CREATE)|SQLITE_OPEN_FULLMUTEX,nullptr)!=SQLITE_OK){error_="Cannot open private account store";Close();return false;}
 sqlite3_busy_timeout(db_,1000);
 sqlite3_db_config(db_,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr);
 if(!Sql("PRAGMA trusted_schema=OFF; PRAGMA foreign_keys=ON; PRAGMA synchronous=FULL; PRAGMA journal_mode=DELETE;")){Close();return false;}
 if(!exists){
  if(!Sql("BEGIN IMMEDIATE; CREATE TABLE accounts(id TEXT PRIMARY KEY CHECK(length(id)=64),label TEXT NOT NULL,role INTEGER NOT NULL CHECK(role BETWEEN 0 AND 3),enabled INTEGER NOT NULL CHECK(enabled IN(0,1)),revision INTEGER NOT NULL CHECK(revision>0)); CREATE TABLE audit(number INTEGER PRIMARY KEY,actor TEXT NOT NULL,target TEXT NOT NULL,role INTEGER NOT NULL,enabled INTEGER NOT NULL,revision INTEGER NOT NULL,at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP); PRAGMA user_version=1; COMMIT;")){Sql("ROLLBACK");Close();return false;}
 }
 Statement version(db_,"PRAGMA user_version");Statement check(db_,"PRAGMA quick_check");
 if(!version.p||sqlite3_step(version.p)!=SQLITE_ROW||sqlite3_column_int(version.p,0)!=1||!check.p||sqlite3_step(check.p)!=SQLITE_ROW||Text(check.p,0)!="ok") {error_="Unsupported or corrupt staff store; restore from backup";Close();return false;}
 Statement schema(db_,"SELECT id,label,role,enabled,revision FROM accounts LIMIT 1");Statement audit(db_,"SELECT actor,target,role,enabled,revision,at FROM audit LIMIT 1");
 if(!schema.p||!audit.p){error_="Invalid staff schema";Close();return false;}return true;
}
Account Store::Get(const std::string& id){
 Account a;if(!ValidId(id)||!db_)return a;Statement s(db_,"SELECT id,label,role,enabled,revision FROM accounts WHERE id=?");if(!s.p)return a;s.Text(1,id);if(sqlite3_step(s.p)==SQLITE_ROW)a=Row(s.p);return a;
}
std::vector<Account> Store::List(){std::vector<Account> out;Statement s(db_,"SELECT id,label,role,enabled,revision FROM accounts ORDER BY role DESC,label LIMIT 1024");if(s.p)while(sqlite3_step(s.p)==SQLITE_ROW)out.push_back(Row(s.p));return out;}
bool Store::Write(const std::string& actor,const std::string& target,Role role,const std::string& label,bool enabled){
 Account old=Get(target);if(old.revision>=INT64_MAX)return false;
 Statement s(db_,"INSERT INTO accounts(id,label,role,enabled,revision) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET label=excluded.label,role=excluded.role,enabled=excluded.enabled,revision=excluded.revision");if(!s.p)return false;s.Text(1,target);s.Text(2,label);sqlite3_bind_int(s.p,3,(int)role);sqlite3_bind_int(s.p,4,enabled);sqlite3_bind_int64(s.p,5,old.revision+1);
 if(sqlite3_step(s.p)!=SQLITE_DONE)return false;
 if(failNext_){failNext_=false;error_="Injected write failure";return false;}
 Statement a(db_,"INSERT INTO audit(actor,target,role,enabled,revision) VALUES(?,?,?,?,?)");if(!a.p)return false;a.Text(1,actor);a.Text(2,target);sqlite3_bind_int(a.p,3,(int)role);sqlite3_bind_int(a.p,4,enabled);sqlite3_bind_int64(a.p,5,old.revision+1);return sqlite3_step(a.p)==SQLITE_DONE;
}
bool Store::BootstrapOwner(const std::string& id,const std::string& label){return ConsoleChange(id,Role::Owner,label,true);}
bool Store::ConsoleChange(const std::string& target,Role role,const std::string& label,bool enabled){
 if(!ValidId(target)||!ValidLabel(label)||(int)role<0||(int)role>3||(enabled&&role==Role::None))return false;
 if(!Sql("BEGIN IMMEDIATE"))return false;bool ok=true;auto old=Get(target);
 if(old.enabled&&old.role==Role::Owner&&(!enabled||role!=Role::Owner)){int count=0;for(auto a:List())if(a.enabled&&a.role==Role::Owner)count++;ok=count>1;}
 ok=ok&&Write("console",target,role,label,enabled);if(ok)ok=Sql("COMMIT");if(!ok)Sql("ROLLBACK");return ok;
}
bool Store::Change(const std::string& actor,const std::string& target,Role role,const std::string& label,bool enabled){
 if(!ValidId(actor)||!ValidId(target)||!ValidLabel(label)||actor==target||(int)role<0||role>=Role::Owner||(enabled&&role==Role::None))return false;
 if(!Sql("BEGIN IMMEDIATE"))return false;auto a=Get(actor);auto t=Get(target);
 bool ok=a.enabled&&a.role>=Role::Admin&&a.role>t.role&&a.role>role;
 if(ok)ok=Write(actor,target,role,label,enabled);
 if(ok)ok=Sql("COMMIT");if(!ok)Sql("ROLLBACK");return ok;
}
int Store::AuditCount(){Statement s(db_,"SELECT count(*) FROM audit");return s.p&&sqlite3_step(s.p)==SQLITE_ROW?sqlite3_column_int(s.p,0):-1;}
}
