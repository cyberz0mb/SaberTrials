#pragma once

#include <array>
#include <cstdint>
#include <string>

namespace antiscript {
// Eight observable actions. The low bit marks a release. Signatures contain
// only these hexadecimal symbols, never CFG text, cvar values or key names.
int edge(const char* command);
bool balanced(const std::string& signature);
struct Claim {
    std::string signature;
    int time = 0;
    uint32_t origin = 0;
};
class Execution {
    uint32_t origin_ = 0;
    std::string edges_;
    unsigned waits_ = 0;
    bool waited_ = false;
public:
    void wait(uint32_t origin);
    Claim action(uint32_t origin, int edge, int time);
};
struct Pattern {
    std::string signature, intervals;
    int time = 0;
    int arrivalSpan = 0;
};
class Behavior {
    struct Sample { char edge; int time, arrival; };
    std::array<Sample,24> history_{};
    int count_ = 0, mask_ = 0, lastTime_ = -1;
public:
    Pattern sample(int mask, int time, int serverFrameTime);
};
enum class Mode { Off, Monitor, Enforce };
Mode mode(const std::string& setting);
bool corroborates(const Claim&, const Pattern&);
}
