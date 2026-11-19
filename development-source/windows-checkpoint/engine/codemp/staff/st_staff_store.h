#pragma once
#include "st_staff_types.h"
struct sqlite3;
namespace st {
struct Account { std::string id,label;Role role=Role::None;bool enabled=false;uint64_t revision=0; };
class Store {
 sqlite3* db_=nullptr;bool failNext_=false;std::string error_;
 bool Sql(const char*);
 bool Write(const std::string& actor,const std::string& target,Role,const std::string& label,bool enabled);
public:
 ~Store(); bool Open(const std::string& path);void Close();
 const std::string& Error()const{return error_;}
 Account Get(const std::string& id);
 std::vector<Account> List();
 bool BootstrapOwner(const std::string& id,const std::string& label);
 bool ConsoleChange(const std::string& target,Role,const std::string& label,bool enabled);
 bool Change(const std::string& actor,const std::string& target,Role,const std::string& label,bool enabled);
 int AuditCount();
 void FailNextWriteForTest(){failNext_=true;}
};
}
