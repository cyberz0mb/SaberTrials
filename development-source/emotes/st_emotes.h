#pragma once

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace stemote {
constexpr int groups = 5, slots = 8, maxDlc = 32;
constexpr int catalogString = CS_MAX;
constexpr int playerString = CS_MAX + 1;
static_assert(playerString + MAX_CLIENTS <= MAX_CONFIGSTRINGS, "Emote configstrings exceed protocol capacity");

inline bool sharedGla(std::string name) {
    std::transform(name.begin(),name.end(),name.begin(),[](unsigned char c) { return char(std::tolower(c)); });
    return name == "models/players/_humanoid/_humanoid" || name == "models/players/_humanoid/_humanoid.gla";
}

struct Clip {
    std::string id, label;
    int first = 0, frames = 0, fps = 20;
    uint32_t signature = 0;
    int stock = -1;
    bool stationary() const { return signature != 0 || stock == BOTH_MEDITATE; }
    std::string token() const {
        char fingerprint[9];
        std::snprintf(fingerprint, sizeof(fingerprint), "%08x", signature);
        return id + "@" + fingerprint;
    }
};

inline bool idValid(const std::string& id) {
    return !id.empty() && id.size() <= 20 && id.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_-") == std::string::npos;
}

inline bool labelValid(const std::string& label) {
    return !label.empty() && label.size() <= 40 && std::all_of(label.begin(), label.end(), [](unsigned char c) {
        return c >= 32 && c <= 126 && c != '"' && c != '\\' && c != ';';
    });
}

inline std::vector<Clip> builtins() {
    return {{"taunt","Taunt",5045,23,20,0,BOTH_ENGAGETAUNT},
        {"bow","Bow",1864,45,20,0,BOTH_BOW},
        {"meditate","Meditate",10310,31,20,0,BOTH_MEDITATE},
        {"flourish","Flourish",13448,20,20,0,BOTH_SHOWOFF_MEDIUM},
        {"celebrate","Celebrate",19140,66,20,0,BOTH_VICTORY_MEDIUM}};
}

inline const Clip* find(const std::vector<Clip>& clips, const std::string& id) {
    const auto it = std::find_if(clips.begin(), clips.end(), [&](const Clip& clip) { return clip.id == id; });
    return it == clips.end() ? nullptr : &*it;
}

template<class Read>
std::vector<Clip> catalog(Read read) {
    auto result = builtins();
    for (int i = 0; i < maxDlc; ++i) {
        char name[32], value[160];
        std::snprintf(name, sizeof(name), "st_emoteClip%d", i);
        read(name, value, sizeof(value));
        if (!*value) break;
        std::istringstream row(value);
        Clip clip;
        row >> clip.id >> clip.first >> clip.frames >> clip.fps >> std::hex >> clip.signature;
        if (!row || row.get() != '\t') continue;
        std::getline(row, clip.label);
        if (idValid(clip.id) && labelValid(clip.label) && clip.first >= 22443 && clip.first <= 100000 &&
            clip.frames >= 2 && clip.frames <= 240 && clip.fps >= 10 && clip.fps <= 60 &&
            clip.signature && !find(result, clip.id)) result.push_back(clip);
    }
    return result;
}

inline bool offered(const std::string& offer, const Clip& clip) {
    return offer.find(" " + clip.token() + " ") != std::string::npos;
}

inline std::string slotVar(int group, int slot) {
    return "st_emoteG" + std::to_string(group + 1) + "S" + std::to_string(slot + 1);
}

inline std::string nameVar(int group) { return "st_emoteGroupName" + std::to_string(group + 1); }

inline std::string directBinding(const Clip& clip) { return "st_emote " + clip.id; }
}
