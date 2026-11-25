#include "ledger.h"
#include "sqlite3.h"
#include <algorithm>
#include <sstream>

namespace antiscript {
namespace {
void check(sqlite3* db, int rc) {
    if (rc != SQLITE_OK) throw std::runtime_error(db ? sqlite3_errmsg(db) : "SQLite unavailable");
}
void execute(sqlite3* db, const char* sql) { check(db,sqlite3_exec(db,sql,nullptr,nullptr,nullptr)); }
class Statement {
    sqlite3_stmt* stmt_ = nullptr;
    sqlite3* db_;
public:
    Statement(sqlite3* db,const char* sql) : db_(db) {
        check(db,sqlite3_prepare_v2(db,sql,-1,&stmt_,nullptr));
    }
    ~Statement() { sqlite3_finalize(stmt_); }
    void bind(int i, const std::string& v) { check(db_,sqlite3_bind_text(stmt_,i,v.data(),int(v.size()),SQLITE_TRANSIENT)); }
    void bind(int i, int64_t v) { check(db_,sqlite3_bind_int64(stmt_,i,v)); }
    bool row() {
        int rc = sqlite3_step(stmt_);
        if (rc == SQLITE_ROW) return true;
        if (rc != SQLITE_DONE) check(db_,rc);
        return false;
    }
    int64_t number(int i) { return sqlite3_column_int64(stmt_,i); }
    std::string text(int i) { return reinterpret_cast<const char*>(sqlite3_column_text(stmt_,i)); }
};
class Transaction {
    sqlite3* db_;
public:
    explicit Transaction(sqlite3* db) : db_(db) { execute(db_,"BEGIN IMMEDIATE"); }
    ~Transaction() { if (db_) sqlite3_exec(db_,"ROLLBACK",nullptr,nullptr,nullptr); }
    void commit() { execute(db_,"COMMIT"); db_ = nullptr; }
};
const char* penalties[] = {"observe","private-warning","public-warning","kick","temporary-ban","permanent-ban"};
void requireAccount(const std::string& a) {
    if (!validAccount(a)) throw std::invalid_argument("expected verified 32-digit account ID");
}
}
bool validAccount(const std::string& a) {
    return a.size() == 32 && a.find_first_not_of("0123456789abcdef") == std::string::npos;
}
Ledger::Ledger(const std::string& path) {
    try {
        int rc = sqlite3_open_v2(path.c_str(),&db_,SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE,nullptr);
        check(db_,rc);
        execute(db_,"PRAGMA synchronous=FULL;"
            "CREATE TABLE IF NOT EXISTS players(account TEXT PRIMARY KEY,strikes INTEGER NOT NULL DEFAULT 0,"
            "ban_until INTEGER NOT NULL DEFAULT 0,last_seen INTEGER NOT NULL DEFAULT 0);"
            "CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,account TEXT NOT NULL,ts INTEGER NOT NULL,"
            "incident TEXT,kind TEXT NOT NULL,evidence TEXT NOT NULL,penalty TEXT NOT NULL,"
            "strike INTEGER NOT NULL,ban_until INTEGER NOT NULL,UNIQUE(account,incident));"
            "CREATE INDEX IF NOT EXISTS account_events ON events(account,id);");
    } catch (...) { sqlite3_close(db_); throw; }
}
Ledger::~Ledger() { sqlite3_close(db_); }
State Ledger::lookup(const std::string& a) {
    requireAccount(a);
    Statement q(db_,"SELECT strikes,ban_until,last_seen FROM players WHERE account=?");
    q.bind(1,a);
    if (!q.row()) return {};
    return {int(q.number(0)),q.number(1),q.number(2)};
}
int Ledger::confirm(Mode m,const std::string& a,const std::string& incident,
                    const Claim& c,const Pattern& p,int64_t now) {
    if (m == Mode::Off || !validAccount(a) || incident.empty() || now <= 0 || !corroborates(c,p)) return 0;
    Transaction tx(db_);
    auto state = lookup(a);
    Statement duplicate(db_,"SELECT 1 FROM events WHERE account=? AND incident=?");
    duplicate.bind(1,a); duplicate.bind(2,incident);
    bool seen = duplicate.row();
    int strike = 0;
    if (m == Mode::Enforce) {
        if (!seen && !state.banned(now) && (!state.lastSeen || now-state.lastSeen >= 600))
            strike = std::min(5,state.strikes+1);
        if (strike) {
            state.strikes = strike;
            state.banUntil = strike == 5 ? -1 : strike == 4 ? now + 30LL*86400 : 0;
        }
        Statement save(db_,"INSERT INTO players VALUES(?,?,?,?) ON CONFLICT(account) DO UPDATE SET "
                           "strikes=excluded.strikes,ban_until=excluded.ban_until,last_seen=excluded.last_seen");
        save.bind(1,a); save.bind(2,state.strikes); save.bind(3,state.banUntil);
        save.bind(4,std::max(now,state.lastSeen)); save.row();
    }
    if (!seen) {
        const bool combat = p.signature.find_first_of("0123") != std::string::npos;
        Statement add(db_,"INSERT INTO events(account,ts,incident,kind,evidence,penalty,strike,ban_until) VALUES(?,?,?,?,?,?,?,?)");
        add.bind(1,a); add.bind(2,now); add.bind(3,incident); add.bind(4,combat?"timed-combat":"timed-movement");
        add.bind(5,"script="+c.signature+" at="+std::to_string(c.time)+" server="+p.signature+
                   " at="+std::to_string(p.time)+" repeats=3 arrival_span_ms="+std::to_string(p.arrivalSpan)+" intervals_ms="+p.intervals);
        add.bind(6,penalties[strike]); add.bind(7,state.strikes); add.bind(8,state.banUntil); add.row();
    }
    tx.commit();
    return strike;
}
bool Ledger::overrideState(const std::string& a,bool clear,int64_t now) {
    Transaction tx(db_);
    auto s = lookup(a);
    if (!(clear ? s.strikes != 0 : s.banUntil != 0)) return false;
    Statement change(db_,clear ? "UPDATE players SET strikes=0 WHERE account=?" :
                                 "UPDATE players SET ban_until=0 WHERE account=?");
    change.bind(1,a); change.row();
    Statement audit(db_,"INSERT INTO events(account,ts,kind,evidence,penalty,strike,ban_until) "
                        "VALUES(?,?,'admin','operator console or RCON',?,?,?)");
    audit.bind(1,a); audit.bind(2,now); audit.bind(3,clear?"clear-strikes":"revoke-ban");
    audit.bind(4,clear?0:s.strikes); audit.bind(5,clear?s.banUntil:0); audit.row();
    tx.commit();
    return true;
}
void Ledger::observe(const std::string& a,const std::string& kind,const std::string& detail,int64_t now) {
    if (a != "guest") requireAccount(a);
    Statement q(db_,"INSERT INTO events(account,ts,kind,evidence,penalty,strike,ban_until) "
                    "VALUES(?,?,?,?,'observe',0,0)");
    q.bind(1,a); q.bind(2,now); q.bind(3,kind); q.bind(4,detail); q.row();
}
void Ledger::evidence(const std::string& a,int64_t before,const std::function<void(const std::string&)>& print) {
    if (a != "guest") requireAccount(a);
    Statement q(db_,"SELECT id,ts,kind,evidence,penalty,strike,ban_until,coalesce(incident,'-') "
                    "FROM events WHERE account=? AND id<? ORDER BY id DESC LIMIT 25");
    q.bind(1,a); q.bind(2,before);
    while (q.row()) {
        std::ostringstream line;
        line << "#" << q.number(0) << " utc=" << q.number(1) << ' ' << q.text(2) << ' ' << q.text(3)
             << " action=" << q.text(4) << " strikes=" << q.number(5) << " ban_until=" << q.number(6)
             << " incident=" << q.text(7);
        print(line.str());
    }
}
}
