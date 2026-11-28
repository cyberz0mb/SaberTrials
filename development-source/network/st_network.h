#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace stnet {
// All intervals are measured on the local monotonic clock. Sequence numbers
// count complete incoming netchan messages, including non-snapshot messages.
struct Window {
    int received = 0, sent = 0, snapshots = 0, pingSamples = 0, timingSamples = 0, delayed = 0;
    int64_t missing = 0, pingSum = 0;
    double variation = 0;

    double loss() const { return 100.0 * missing / std::max<int64_t>(1, missing + received); }
    double jitter() const { return variation / std::max(1, timingSamples); }
    double ping() const { return double(pingSum) / std::max(1, pingSamples); }
    bool ready() const { return received >= 8 && timingSamples >= 6; }
    bool hasPing() const { return pingSamples >= 4; }
};

enum class Profile { Personal, Stable, Distant, Variable, Lossy, RateLimited };

inline Profile recommend(const Window& w) {
    if (w.loss() >= 2.0) return Profile::Lossy;
    if (w.delayed * 4 > w.snapshots) return Profile::RateLimited;
    if (w.jitter() >= 9.0) return Profile::Variable;
    return w.hasPing() && w.ping() >= 90 ? Profile::Distant : Profile::Stable;
}

// The Internet send gate supports one command packet per millisecond and
// CL_SendCmd runs once per client frame.
constexpr int MaxPackets = 1000;
struct PacketBudget {
    int target = MaxPackets, badWindows = 0, goodWindows = 0;
    bool triedReduction = false;
    double lossBeforeTrial = -1;

    void evaluate(const Window& w, int elapsed) {
        if (!w.ready() || elapsed <= 0 || !w.sent) {
            badWindows = goodWindows = 0;
            return;
        }
        const double loss = w.loss();
        badWindows = loss >= 2 ? std::min(2, badWindows + 1) : 0;
        goodWindows = loss < 2 ? std::min(2, goodWindows + 1) : 0;
        if (goodWindows == 2) {
            target = MaxPackets;
            triedReduction = false;
            lossBeforeTrial = -1;
        } else if (lossBeforeTrial >= 0) {
            // Incoming loss may be unrelated to the uplink. Keep a reduction
            // only if the next measured window improves by a percentage point.
            if (loss >= 2 && loss > lossBeforeTrial - 1) target = MaxPackets;
            lossBeforeTrial = -1;
        } else if (badWindows == 2 && !triedReduction) {
            const int actual = static_cast<int>(std::min<double>(MaxPackets, 1000.0 * w.sent / elapsed));
            target = std::max(20, actual * 3 / 4);
            triedReduction = true;
            lossBeforeTrial = loss;
        }
    }
};

inline int requestedRate(int minimum, int maximum) {
    // The existing Setup range goes to 1 MB/s. A server may explicitly
    // advertise another budget or enforce its own fixed rate.
    return std::max(1000, maximum > 0 ? maximum : std::max(minimum, 1000000));
}
inline int requestedSnaps(int fps, int minimum, int maximum) {
    int target = fps > 0 ? fps : (maximum > 0 ? maximum : std::max(125, minimum));
    return maximum > 0 ? std::min(target, maximum) : target;
}
struct Values { int nudge, dup; };
inline Values values(Profile profile) {
    switch (profile) {
    case Profile::Lossy:       return {8, 2};
    case Profile::Variable:    return {6, 1};
    case Profile::RateLimited: return {4, 1};
    default:                   return {0, 1};
    }
}

struct Controller {
    Profile active = Profile::Personal, previous = Profile::Personal, candidate = Profile::Personal;
    Window baseline;
    int votes = 0, trial = 0, cooldown = 0;
    void rollback() {
        active = previous;
        trial = votes = 0;
        cooldown = 6;
    }
    void evaluate(const Window& w) {
        if (trial) {
            if (!w.ready() || w.loss() > baseline.loss() + 3 ||
                w.jitter() > baseline.jitter() + 12 ||
                (w.hasPing() && baseline.hasPing() && w.ping() > baseline.ping() + 45)) {
                rollback();
            } else {
                --trial;
            }
            return;
        }
        if (!w.ready() || cooldown) {
            if (cooldown) --cooldown;
            votes = 0;
            return;
        }
        Profile next = recommend(w);
        if (next == Profile::Stable && !w.hasPing() && active == Profile::Distant)
            next = active;
        if (next != candidate) { candidate = next; votes = 0; }
        if (next == active) { votes = 0; return; }
        if (++votes < 2) return;
        previous = active;
        active = next;
        baseline = w;
        trial = 2;
        votes = 0;
    }
};

// Carry fractional frame time forward. Missed deadlines expire after a stall.
struct Pacer {
    double due = 0;
    int lastRate = 0;
    bool ready(int now, int rate) {
        if (rate != lastRate) { lastRate = rate; due = now; }
        if (now < due) return false;
        double interval = 1000.0 / rate;
        due = now - due >= interval ? now + interval : due + interval;
        return true;
    }
};
}
