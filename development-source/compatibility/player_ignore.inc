// Local player chat filter. Included by cl_cgame.cpp.
#include <string>

namespace playerIgnore {
enum class Rule { Inherit, Ignore, Allow };
struct PlayerRule {
    Rule rule = Rule::Inherit;
    std::string name;
};
static PlayerRule players[MAX_CLIENTS];
static bool ignoreEveryone;
static std::string notice;
static int noticeUntil;

static void feedback(const std::string &message) {
    notice = message;
    noticeUntil = cls.realtime + 2500;
    Com_Printf("%s\n", notice.c_str());
}

static const char *playerName(int slot) {
    const int offset = cl.gameState.stringOffsets[CS_PLAYERS + slot];
    return Info_ValueForKey(cl.gameState.stringData + offset, "n");
}

static std::string plainName(const char *text) {
    std::string result;
    for (; *text; ++text) {
        if (Q_IsColorString(text)) ++text;
        else if (*text != '\x19') result += *text;
    }
    return result;
}

static bool ignored(int slot) {
    if (slot == clc.clientNum) return false;
    return players[slot].rule == Rule::Ignore ||
        (ignoreEveryone && players[slot].rule != Rule::Allow);
}

static void reset(bool all) {
    ignoreEveryone = all;
    for (auto &player : players) player = PlayerRule{};
}

// Distinguish an invalid numeric slot from a name. Never turn bad input into slot zero.
static bool readSlot(const char *text, int &slot) {
    slot = -1;
    bool explicitSlot = *text == '#';
    if (explicitSlot) ++text;
    if (!*text) return explicitSlot;
    unsigned value = 0;
    for (const char *p = text; *p; ++p) {
        if (*p < '0' || *p > '9') return explicitSlot;
        if (value < MAX_CLIENTS) value = value * 10 + (*p - '0');
    }
    if (value < MAX_CLIENTS) slot = static_cast<int>(value);
    return true;
}

static int uniqueName(const std::string &name) {
    int found = -1;
    if (name.empty()) return found;
    for (int i = 0; i < MAX_CLIENTS; ++i) {
        if (Q_stricmp(plainName(playerName(i)).c_str(), name.c_str())) continue;
        if (found >= 0) return -2;
        found = i;
    }
    return found;
}

static void command() {
    if (cls.state != CA_ACTIVE || !cls.cgameStarted || clc.demoplaying) {
        Com_Printf("Join a match to use player ignore.\n");
        return;
    }
    bool mute = !Q_stricmp(Cmd_Argv(0), "ignore");
    int slot = -1;
    if (Cmd_Argc() == 1) {
        slot = CGVM_CrosshairPlayer();
        if (slot < 0 || slot >= MAX_CLIENTS || slot == clc.clientNum || !*playerName(slot)) {
            feedback("Aim at a player.");
            return;
        }
        if (mute) mute = !ignored(slot);
    } else {
        std::string target = Cmd_Argv(1);
        for (int i = 2; i < Cmd_Argc(); ++i) {
            target += ' ';
            target += Cmd_Argv(i);
        }
        if (!Q_stricmp(target.c_str(), "all")) {
            reset(mute);
            feedback(mute ? "All players are now ignored." : "All player chat restored.");
            return;
        }
        if (!readSlot(target.c_str(), slot)) slot = uniqueName(plainName(target.c_str()));
        if (slot == -2) {
            Com_Printf("Several players have that name. Use their slot number.\n");
            return;
        }
        if (slot < 0 || !*playerName(slot)) {
            Com_Printf("Player not found. Use an exact name or an occupied slot number.\n");
            return;
        }
        if (slot == clc.clientNum) {
            Com_Printf("You cannot ignore yourself.\n");
            return;
        }
    }
    const std::string name = plainName(playerName(slot));
    players[slot].rule = mute == ignoreEveryone ? Rule::Inherit : (mute ? Rule::Ignore : Rule::Allow);
    players[slot].name = name;
    feedback(name + (mute ? " is now ignored" : " is now unignored"));
}

// Older game modules may send the stock marked name without a sender slot.
// Only match the formatted sender field; a name in the message body is ordinary text.
static int legacySender(const char *text) {
    const char *delimiter = strstr(text, "\x19: ");
    if (!delimiter || delimiter - text > 2 * MAX_NETNAME) return -1;
    std::string prefix(text, delimiter);
    if (prefix.size() >= 4 && prefix[0] == '\x19' && prefix[prefix.size()-2] == '\x19' &&
        ((prefix[1] == '(' && prefix.back() == ')') || (prefix[1] == '[' && prefix.back() == ']'))) {
        prefix = prefix.substr(2, prefix.size()-4);
    }
    return uniqueName(plainName(prefix.c_str()));
}

static bool filtersCommand() {
    const char *op = Cmd_Argv(0);
    const bool location = !strcmp(op, "lchat") || !strcmp(op, "ltchat");
    if (!location && strcmp(op, "chat") && strcmp(op, "tchat")) return false;
    const int senderField = location ? 5 : 2;
    int slot = -1;
    if (Cmd_Argc() > senderField) readSlot(Cmd_Argv(senderField), slot);
    else if (Cmd_Argc() == senderField) slot = legacySender(Cmd_Argv(1));
    return slot >= 0 ? ignored(slot) : ignoreEveryone;
}
}

void CL_IgnoreRegister() {
    Cmd_AddCommand("ignore", playerIgnore::command, "Ignore chat from the aimed player, a name, a slot or all players");
    Cmd_AddCommand("unignore", playerIgnore::command, "Restore chat from a player or all players");
}

void CL_IgnoreReset() {
    playerIgnore::reset(false);
    playerIgnore::notice.clear();
}

void CL_DrawIgnoreNotice() {
    using namespace playerIgnore;
    if (notice.empty() || cls.realtime >= noticeUntil) return;
    const float scale = .8f;
    const int x = (640 - re->Font_StrLenPixels(notice.c_str(), cls.menuFont, scale)) / 2;
    const vec4_t shade = {0, 0, 0, .9f}, color = {.90f, .96f, 1, 1};
    re->Font_DrawString(x+1, 280, notice.c_str(), shade, cls.menuFont, -1, scale);
    re->Font_DrawString(x, 279, notice.c_str(), color, cls.menuFont, -1, scale);
}

void CL_IgnoreNewGameState() {
    for (int slot = 0; slot < MAX_CLIENTS; ++slot) {
        auto &entry = playerIgnore::players[slot];
        if (entry.rule != playerIgnore::Rule::Inherit &&
            Q_stricmp(entry.name.c_str(), playerIgnore::plainName(playerIgnore::playerName(slot)).c_str()))
            entry = playerIgnore::PlayerRule{};
    }
}

static void CL_IgnorePlayerInfo(int slot, const char *info) {
    auto &entry = playerIgnore::players[slot];
    if (!*info) entry = playerIgnore::PlayerRule{};
    else if (entry.rule != playerIgnore::Rule::Inherit)
        entry.name = playerIgnore::plainName(Info_ValueForKey(info, "n"));
}
