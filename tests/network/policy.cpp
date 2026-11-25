#include "../../development-source/network/st_network.h"
#include <cassert>

int main() {
    using namespace stnet;
    assert(requestedRate(0, 90000) == 90000);
    assert(requestedRate(0, 250000) == 250000);
    assert(requestedRate(30000, 0) == 1000000);
    assert(requestedSnaps(30, 0, 0) == 30);
    assert(requestedSnaps(125, 0, 0) == 125);
    assert(requestedSnaps(125, 15, 60) == 60);
    assert(requestedSnaps(0, 0, 0) == 125);
    Window good;
    good.received = good.snapshots = good.timingSamples = good.pingSamples = 200;
    good.pingSum = 24000;
    good.variation = 400;
    Window spectator = good;
    spectator.pingSamples = spectator.pingSum = 0;
    Controller observing;
    observing.evaluate(spectator);
    observing.evaluate(spectator);
    assert(observing.active == Profile::Stable);
    PacketBudget budget;
    spectator.sent = 2400;
    budget.evaluate(spectator, 10000);
    assert(budget.target == 1000);
    spectator.missing = 20;
    budget.evaluate(spectator, 10000);
    assert(budget.target == 1000);
    budget.evaluate(spectator, 10000);
    assert(budget.target == 180);
    budget.evaluate(spectator, 10000);
    assert(budget.target == 1000);  // Backoff did not improve incoming loss.
    spectator.missing = 0;
    budget.evaluate(spectator, 10000);
    budget.evaluate(spectator, 10000);
    spectator.missing = 20;
    budget.evaluate(spectator, 10000);
    budget.evaluate(spectator, 10000);
    spectator.missing = 8;
    budget.evaluate(spectator, 10000);
    assert(budget.target == 180);
    spectator.missing = 0;
    budget.evaluate(spectator, 10000);
    budget.evaluate(spectator, 10000);
    assert(budget.target == 1000);
    assert(good.ping() == 120 && good.jitter() == 2 && good.loss() == 0);
    Controller c;
    c.evaluate(good);
    assert(c.active == Profile::Personal);
    c.evaluate(good);
    assert(c.active == Profile::Distant && c.trial == 2);
    Window loss = good;
    loss.missing = 50;
    assert(loss.loss() == 20 && recommend(loss) == Profile::Lossy);
    c.evaluate(loss);
    assert(c.active == Profile::Personal && c.cooldown == 6);
    for (int i = 0; i < 6; ++i) c.evaluate(loss);
    assert(c.active == Profile::Personal);
    c.evaluate(loss);
    c.evaluate(loss);
    assert(c.active == Profile::Lossy);
    c.evaluate(loss);
    c.evaluate(loss);
    assert(!c.trial);
    Window jitter = good;
    jitter.variation = 2800;
    assert(recommend(jitter) == Profile::Variable);
    Window choked = good;
    choked.delayed = 80;
    assert(recommend(choked) == Profile::RateLimited);
    c.evaluate(jitter);
    c.evaluate(jitter);
    assert(c.active == Profile::Variable);
    c.evaluate({});
    assert(c.active == Profile::Lossy);
    Pacer p;
    int sent = 0;
    for (int ms = 0; ms < 10000; ms += 8) sent += p.ready(ms, 85);
    assert(sent >= 849 && sent <= 851);
    assert(p.ready(60000, 85));
    assert(!p.ready(60000, 85) && !p.ready(60001, 85));
    for (int fps : {60, 125, 250, 1000}) {
        Pacer full;
        for (int frame = 0; frame < fps; ++frame)
            assert(full.ready(frame * 1000 / fps, MaxPackets));
    }
}
