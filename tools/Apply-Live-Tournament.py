"""Apply the event controller hooks to the combined beta game source."""
from pathlib import Path
import sys, shutil
src = Path(__file__).resolve().parents[1]/"development-source/bot-roles/codemp/game"
target = Path(sys.argv[1])
for name in ("g_event.c","g_event.h","g_event_ui.inc","st_event.c","st_event.h","st_event_ui.h","st_event_account_api.h"):
    shutil.copyfile(src/name,target/name)
def change(name, pairs):
    path=target/name
    raw=path.read_bytes()
    s=raw.decode("latin1").replace("\r\n","\n")
    for old,new in pairs:
        if new in s: continue
        if old not in s: raise ValueError((name,old))
        s=s.replace(old,new)
    if b"\r\n" in raw:s=s.replace("\n","\r\n")
    path.write_bytes(s.encode("latin1"))
def after(marker,code):return marker,marker+"\n"+code
def before(marker,code):return marker,code+"\n"+marker
change("CMakeLists.txt",[after('"${MPDir}/game/g_staff.c"', '    "${MPDir}/game/g_event.c"\n    "${MPDir}/game/st_event.c"')])
change("g_local.h",[after('#include "g_staff.h"','#include "g_event.h"')])
change("g_staff.h",[after("int ST_StaffRoleForClient(int slot);","int ST_StaffGenerationForClient(int slot,unsigned char generation[16]);")])
change("g_staff.c",[after("static const STStaffImports* engine;","int ST_StaffGenerationForClient(int slot,unsigned char generation[16]) { return engine && engine->GenerationForClient(slot,generation); }"),before(" if(ent->client->ps.duelInProgress)", " if(ST_EventActive() && ent->client->sess.sessionTeam!=TEAM_SPECTATOR)return qtrue;")])
change("g_active.c",[(f"if (ST_Staff{op}(ent))",f"if (ST_Event{op}(ent) || ST_Staff{op}(ent))") for op in ("Think","Blocked")])
change("g_combat.c",[("if (ST_StaffBlocked(targ)","if (ST_EventBlocked(targ) || ST_EventBlocked(attacker) || ST_EventBlocked(inflictor) || ST_StaffBlocked(targ)")])
change("g_client.c",[after("void ClientDisconnect( int clientNum ) {","    ST_EventDisconnect(clientNum);"),("if ( !stMvpLeaving && level.gametype == GT_DUEL","if ( !ST_EventActive() && !stMvpLeaving && level.gametype == GT_DUEL"),("if ( ST_FormatMode()!=2 && level.gametype == GT_DUEL","if ( !ST_EventActive() && ST_FormatMode()!=2 && level.gametype == GT_DUEL")])
change("g_main.c",[after("void CheckExitRules( void ) {","    if (ST_EventActive()) return;"),after("ST_TournamentFrame();","    if (ST_EventActive()) return;"),after("for (i=0 ; i<level.num_entities ; i++, ent++) {","        if (ST_EventHoldEntity(ent)) continue;\n        if (ent->inuse && i<MAX_CLIENTS && ST_EventThink(ent)) continue;"),after("void CheckVote( void ) {","    if (ST_EventActive()) {\n        if (level.voteTime || level.voteExecuteTime) {\n            level.voteTime=level.voteExecuteTime=0;\n            trap->SetConfigstring(CS_VOTE_TIME, \"\");\n        }\n        return;\n    }")])
change("g_cmds.c",[("if ( level.gametype == GT_TEAM && level.stTeamsLocked &&","if ( !ST_EventPlacing() && level.gametype == GT_TEAM && level.stTeamsLocked &&"),("if (g_teamForceBalance.integer &&","if (!ST_EventPlacing() && g_teamForceBalance.integer &&"),("else if ( g_teamForceBalance.integer &&","else if ( !ST_EventPlacing() && g_teamForceBalance.integer &&"),before("if ( ST_TournamentControlsDuel() && team != TEAM_SPECTATOR","if (!ST_EventCanJoin(clientNum, team)) return;\n\t"),("if ( (level.gametype == GT_DUEL)\n\t\t&& level.numNonSpectatorClients","if ( !ST_EventPlacing() && (level.gametype == GT_DUEL)\n\t\t&& level.numNonSpectatorClients"),("else if ( g_maxGameClients.integer > 0 &&","else if ( !ST_EventPlacing() && g_maxGameClients.integer > 0 &&"),before("// decide if we will allow the change","if (!ST_EventCanJoin(clientNum, team)) return;"),after("voteString_t\t*vote = NULL;","    if (ST_EventActive()) { trap->SendServerCommand(ent-g_entities, \"print \\\"The host manages this tournament.\\\\n\\\"\"); return; }"),after("trap->Argv( 0, cmd, sizeof( cmd ) );","    if (!ST_EventAllowCommand(clientNum, cmd)) return;")])
change("g_sabertrials.c",[("ST_TournamentLoadState();","ST_EventInit();\n    if (ST_EventActive()) ST_TournamentClearLevelState();\n    else ST_TournamentLoadState();"),after("qboolean ST_TournamentControlsDuel( void ) {","    if (ST_EventActive()) return level.gametype==GT_DUEL;"),after("qboolean ST_TournamentCanEnterArena( int clientNum ) {","    if (ST_EventActive()) return ST_EventCanJoin(clientNum,TEAM_FREE);"),after("void ST_TournamentFrame( void ) {","    if (ST_EventActive()) { ST_EventFrame(); return; }"),after("void Cmd_STTournament_f( gentity_t *ent ) {","    if (ST_EventClientCommand(ent)) return;"),after("void Svcmd_STTournament_f( void ) {","    if (ST_EventActive()) { ST_EventConsole(); return; }")])
change("g_svcmds.c",[before('{ "st_tournament",','{ "st_event", ST_EventConsole, qfalse },\n\t')])

change("w_force.c", [('if ( !g_teamAutoJoin.integer ) {\n\t\t\t\t\t\t// make them a spectator', 'if ( !ST_EventActive() && !g_teamAutoJoin.integer ) {\n\t\t\t\t\t\t// make them a spectator'),('g_maxForceRank.integer, 1, ent->client->sess.sessionTeam','g_maxForceRank.integer, !ST_EventActive(), ent->client->sess.sessionTeam')])
change("g_cmds.c",[after("trap->Argv( 0, cmd, sizeof( cmd ) );",'    if (!Q_stricmp(cmd,"st_lobby")) { if (ST_EventActive()) ST_EventClientCommand(ent); return; }')])
