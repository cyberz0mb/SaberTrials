#include "detection.h"
#include <algorithm>
#include <cstdlib>
#include <cstring>

namespace antiscript {
static const char digits[] = "0123456789abcdef";
Mode mode(const std::string& setting) {
    if (setting == "1") return Mode::Monitor;
    if (setting == "2") return Mode::Enforce;
    return Mode::Off;
}
int edge(const char* command) {
    if (*command != '+' && *command != '-') return -1;
    static const char* names[] = {"attack","altattack","forward","back","moveleft","moveright","moveup","movedown"};
    std::string name(command + 1);
    for (char& c : name) if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
    if (name == "button0") name = "attack";
    if (name == "button7") name = "altattack";
    for (int i = 0; i < 8; ++i)
        if (name == names[i]) return i * 2 + (*command == '-');
    return -1;
}
bool balanced(const std::string& s) {
    if (s.size() < 2 || s.size() > 8 || s.size() % 2) return false;
    unsigned held = 0;
    for (char c : s) {
        const char* p = c ? std::strchr(digits, c) : nullptr;
        if (!p) return false;
        int e = static_cast<int>(p - digits), bit = 1 << (e / 2);
        if (bool(held & bit) != bool(e & 1)) return false;
        held ^= bit;
    }
    return held == 0;
}
void Execution::wait(uint32_t origin) {
    if (origin && origin == origin_) waited_ = true;
}
Claim Execution::action(uint32_t origin, int e, int time) {
    if (e < 0 || e > 15) return {};
    if (!origin || origin != origin_) {
        *this = {};
        origin_ = origin;
    }
    if (!origin || time <= 0) return {};
    if (edges_.size() == 8) edges_.erase(0,1);
    edges_ += digits[e];
    waits_ = ((waits_ << 1) | waited_) & 255;
    waited_ = false;
    // Require a wait between each pair of actions. A prelude wait, a chord
    // or separate physical press/release invocations cannot qualify.
    for (int n = static_cast<int>(edges_.size()); n >= 2; --n) {
        unsigned required = (1u << (n - 1)) - 1;
        if ((waits_ & required) != required) continue;
        auto suffix = edges_.substr(edges_.size() - n);
        if (balanced(suffix)) return {suffix,time,origin};
    }
    return {};
}
Pattern Behavior::sample(int mask, int time, int serverFrameTime) {
    // Seed on discontinuities. Ignore duplicate/reordered commands.
    if (time < 0 || (lastTime_ >= 0 && time <= lastTime_)) return {};
    int change = mask ^ mask_;
    if (lastTime_ < 0 || time - lastTime_ > 250 || (change & (change-1))) {
        count_ = 0;
        change = 0;
    }
    mask_ = mask;
    lastTime_ = time;
    if (!change) return {};
    int bit = 0;
    while (bit < 8 && !(change & (1 << bit))) ++bit;
    if (bit == 8) return {};
    if (count_ == int(history_.size())) {
        std::move(history_.begin()+1, history_.end(), history_.begin());
        --count_;
    }
    history_[count_++] = {digits[bit*2 + !(mask & change)],time,serverFrameTime};
    for (int n : {4,6,8,2}) {
        if (count_ < 3*n) continue;
        const auto* first = history_.data() + count_ - 3*n;
        int clientSpan = time - first->time;
        if (clientSpan > 8000) continue;
        // Packet timestamps are supplied by the client. Also require each cycle
        // to span real server frames, and reject a compressed catch-up burst.
        int arrivalSpan = serverFrameTime - first->arrival;
        if (arrivalSpan < clientSpan*3/4 || arrivalSpan > clientSpan+200) continue;
        if (first[n-1].arrival <= first[0].arrival ||
            first[2*n-1].arrival <= first[n].arrival ||
            first[3*n-1].arrival <= first[2*n].arrival) continue;
        Pattern p;
        bool matches = true;
        for (int i = 0; i < 3*n && matches; ++i) {
            if (i < n) p.signature += first[i].edge;
            if (first[i].edge != first[i%n].edge) matches = false;
            if (i % n == 0) continue; // a player can trigger each run separately
            int delta = first[i].time - first[i-1].time;
            int ref = first[i%n].time - first[i%n-1].time;
            if (delta < 20 || delta > 400 || std::abs(delta - ref) > 8) matches = false;
            if (!p.intervals.empty()) p.intervals += ',';
            p.intervals += std::to_string(delta);
        }
        if (matches && balanced(p.signature)) { p.time = time; p.arrivalSpan = arrivalSpan; return p; }
    }
    return {};
}
bool corroborates(const Claim& c, const Pattern& p) {
    if (!balanced(c.signature) || !balanced(p.signature) || p.signature.size() < 4 ||
        (c.signature != p.signature && c.signature != p.signature+p.signature) ||
        std::llabs(static_cast<long long>(c.time) - p.time) > 100) return false;
    // Single-button cadence, including repeated attack, stays review-only.
    for (char e : c.signature) if ((std::strchr(digits,e)-digits)/2 !=
        (std::strchr(digits,c.signature[0])-digits)/2) return true;
    return false;
}
}
