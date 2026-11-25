#pragma once
#include "detection.h"
#include <functional>
#include <stdexcept>
struct sqlite3;

namespace antiscript {
struct State {
    int strikes = 0;
    int64_t banUntil = 0, lastSeen = 0;
    bool banned(int64_t now) const { return banUntil == -1 || banUntil > now; }
};
class Ledger {
    sqlite3* db_ = nullptr;
public:
    explicit Ledger(const std::string& path);
    ~Ledger();
    Ledger(const Ledger&) = delete;
    Ledger& operator=(const Ledger&) = delete;
    State lookup(const std::string& account);
    void observe(const std::string& account,const std::string& kind,const std::string& detail,int64_t now);
    int confirm(Mode mode, const std::string& account, const std::string& incident,
                const Claim&, const Pattern&, int64_t now);
    bool overrideState(const std::string& account, bool clearStrikes, int64_t now);
    void evidence(const std::string& account, int64_t before,
                  const std::function<void(const std::string&)>& print);
};
bool validAccount(const std::string&);
}
