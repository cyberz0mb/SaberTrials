/* Cosmetic state only. Shared movement, saber timers and hitboxes are untouched. */
#include <algorithm>
#include <sstream>
#include <string>
#include <vector>
extern "C" {
#include "g_local.h"
#include "g_staff.h"
}
#include "qcommon/st_emotes.h"

static std::vector<stemote::Clip> stServerEmotes;
struct STEmotePlayer {
    int until = 0, cooldown = 0, health = 0, armor = 0, spawn = 0;
    bool stationary = false;
};
static STEmotePlayer stEmotePlayers[MAX_CLIENTS];
static bool stEmotesAdvertised;

static bool G_EmotesEnabled() {
    return g_stEmotes.integer && !ST_TournamentControlsDuel() &&
        (level.gametype == GT_FFA || level.gametype == GT_TEAM);
}

extern "C" void G_EmotesInit() {
    stServerEmotes = stemote::catalog(trap->Cvar_VariableStringBuffer);
    std::fill_n(stEmotePlayers,MAX_CLIENTS,STEmotePlayer());
    stEmotesAdvertised = false;
    for (int i = 0; i < MAX_CLIENTS; ++i) trap->SetConfigstring(stemote::playerString+i,"");
}

static void G_EndEmote(int num) {
    if (!stEmotePlayers[num].until) return;
    stEmotePlayers[num].until = 0;
    trap->SetConfigstring(stemote::playerString+num,"");
    if (trap->Cvar_VariableIntegerValue("developer")) trap->Print("ST_EMOTE_END %d\n",num);
}

static bool G_EmoteCanPlay(const gentity_t* ent) {
    const auto& client = *ent->client;
    const auto& ps = client.ps;
    const auto& cmd = client.pers.cmd;
    return ent->health > 0 && client.sess.sessionTeam != TEAM_SPECTATOR && !level.intermissiontime &&
        !level.intermissionQueued && !ST_StaffBlocked(ent) &&
        ps.pm_type == PM_NORMAL && !ps.m_iVehicleNum && !ps.duelInProgress &&
        ps.saberLockTime <= level.time && !ps.saberInFlight && !ps.forceHandExtend &&
        !BG_SaberInAttack(ps.saberMove) && ps.weaponstate != WEAPON_FIRING &&
        !(cmd.buttons & (BUTTON_ATTACK|BUTTON_ALT_ATTACK|BUTTON_USE|BUTTON_FORCEPOWER|BUTTON_USE_HOLDABLE));
}

static bool G_EmoteStationary(const gclient_t& client) {
    const auto& ps = client.ps;
    const auto& cmd = client.pers.cmd;
    return ps.groundEntityNum != ENTITYNUM_NONE && !(ps.pm_flags & PMF_DUCKED) &&
        ps.velocity[0]*ps.velocity[0] + ps.velocity[1]*ps.velocity[1] <= 144.0f &&
        std::abs(int(cmd.forwardmove)) <= 8 && std::abs(int(cmd.rightmove)) <= 8 && cmd.upmove <= 0;
}

extern "C" void G_EmotesFrame() {
    const bool enabled = G_EmotesEnabled();
    if (enabled != stEmotesAdvertised) {
        stEmotesAdvertised = enabled;
        std::string offer = enabled ? "v1 " : "";
        if (enabled) for (const auto& clip : stServerEmotes) {
            if (clip.signature && trap->Cvar_VariableIntegerValue("sv_pure")) continue;
            const auto token = clip.token();
            if (offer.size()+token.size()+1 >= MAX_STRING_CHARS-32) break;
            offer += token + " ";
        }
        trap->SetConfigstring(stemote::catalogString,offer.c_str());
    }
    for (int i = 0; i < level.maxclients; ++i) {
        const auto& state = stEmotePlayers[i];
        if (!state.until) continue;
        auto* ent = &g_entities[i];
        if (!enabled || !ent->inuse || ent->client->pers.connected != CON_CONNECTED ||
            level.time >= state.until || !G_EmoteCanPlay(ent) || ent->health != state.health ||
            ent->client->ps.stats[STAT_ARMOR] != state.armor ||
            ent->client->ps.persistant[PERS_SPAWN_COUNT] != state.spawn ||
            (state.stationary && !G_EmoteStationary(*ent->client))) G_EndEmote(i);
    }
}

extern "C" void G_EmoteInterrupt(gentity_t* ent) {
    if (ent && ent->client && ent->s.number >= 0 && ent->s.number < MAX_CLIENTS)
        G_EndEmote(ent->s.number);
}

extern "C" void Cmd_STEmote_f(gentity_t* ent) {
    auto& state = stEmotePlayers[ent->s.number];
    if (level.time < state.cooldown) return;
    state.cooldown = level.time + 650;
    char id[64];
    trap->Argv(1,id,sizeof(id));
    const auto* clip = stemote::find(stServerEmotes,id);
    if (trap->Argc() != 2 || !clip || !G_EmotesEnabled() ||
        (clip->signature && trap->Cvar_VariableIntegerValue("sv_pure"))) {
        trap->SendServerCommand(ent->s.number,"print \"Emote unavailable on this server.\n\"");
        return;
    }
    if (!G_EmoteCanPlay(ent)) return;
    if (clip->stationary() && !G_EmoteStationary(*ent->client)) {
        trap->SendServerCommand(ent->s.number,va("print \"%s needs you to stand on the ground.\n\"",clip->label.c_str()));
        return;
    }
    state.until = level.time + (1000*clip->frames)/clip->fps;
    state.health = ent->health;
    state.armor = ent->client->ps.stats[STAT_ARMOR];
    state.spawn = ent->client->ps.persistant[PERS_SPAWN_COUNT];
    state.stationary = clip->stationary();
    trap->SetConfigstring(stemote::playerString+ent->s.number,
        va("%s %d %d",clip->token().c_str(),level.time,state.until));
    if (trap->Cvar_VariableIntegerValue("developer"))
        trap->Print("ST_EMOTE_START %d %s moving=%d\n",ent->s.number,clip->id.c_str(),
            !G_EmoteStationary(*ent->client));
}
