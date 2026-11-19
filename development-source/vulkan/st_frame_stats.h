#pragma once
#include <algorithm>
#include <numeric>
#include <vector>
struct STFrameStats {
    std::vector<double> values;
    void clear() { values.clear(); }
    void add(double value) { if (values.size() < 6000) values.push_back(value); }
    double mean() const {
        return values.empty() ? 0 : std::accumulate(values.begin(), values.end(), 0.0) / values.size();
    }
    double percentile(double fraction) const {
        if (values.empty()) return 0;
        auto sorted = values;
        std::sort(sorted.begin(), sorted.end());
        return sorted[(size_t)((sorted.size()-1)*fraction)];
    }
};
