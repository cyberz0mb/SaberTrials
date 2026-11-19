"""Apply the local fidelity-proof hooks to isolated matching source trees."""
from pathlib import Path
import re
import shutil

SOURCE = Path(__file__).resolve().parent


def replace(path, old, new):
    text = path.read_text(encoding='utf-8')
    if text.count(old) != 1:
        raise ValueError(f'Expected one anchor in {path}: {old[:90]!r}')
    path.write_text(text.replace(old, new), encoding='utf-8')


def apply(root, kind):
    for name in ('st_mvp_api.h', 'st_mvp_timing.h', 'st_mvp_montage.h', 'st_mvp_wire.h', 'st_mvp_scene_wire.h', 'st_mvp_retention.h'):
        shutil.copy2(SOURCE / name, root / 'codemp/qcommon' / name)
    for sub, token, previous, current in (('game', 'GAME', 218, 239), ('cgame', 'CGAME', 219, 238)):
        path = root / f'codemp/{sub}/{"g" if sub == "game" else "cg"}_public.h'
        text = path.read_text(encoding='utf-8')
        pattern = rf'(#define\s+{token}_API_VERSION\s+){previous}\b'
        text, count = re.subn(pattern, lambda m: m[1] + str(current), text)
        if count != 1:
            raise ValueError('Unexpected API baseline: ' + str(path))
        text = '#include "qcommon/st_mvp_api.h"\n' + text
        marker = '} gameExport_t;' if sub == 'game' else '} cgameImport_t;'
        if text.count(marker) != 1:
            raise ValueError('Missing API table: ' + str(path))
        extension = '    qboolean (*ST_MvpRead)(int sourceTime, stMvpClip_t *out);\n'
        if sub == 'game':
            extension += '    void (*ST_MvpReset)(void);\n'
        text = text.replace(marker, extension + marker)
        if sub == 'game':
            text = text.replace('} gameImport_t;', '''    int (*ST_MvpPackPose)(void *,unsigned char *,int);
    int (*ST_MvpCompress)(const unsigned char *,int,unsigned char *,int);
} gameImport_t;''')
        else:
            text = text.replace('} cgameImport_t;', '''    void *(*ST_MvpUnpackPose)(const unsigned char *,int);
    int (*ST_MvpDecompress)(const unsigned char *,int,unsigned char *,int);
} cgameImport_t;''')
        path.write_text(text, encoding='utf-8')
    if kind == 'engine':
        replace(root / 'codemp/rd-common/tr_public.h', 'REF_API_VERSION 10', 'REF_API_VERSION 11')
        replace(root / 'codemp/rd-common/tr_public.h', '} refexport_t;', '''    int (*ST_MvpPackPose)(void *,unsigned char *,int);
    void *(*ST_MvpUnpackPose)(const unsigned char *,int);
} refexport_t;''')
        for renderer in ('rd-vanilla', 'rd-rend2', 'rd-dedicated'):
            path = root / 'codemp' / renderer / 'G2_API.cpp'
            # Four actors x 512 retained poses need more than the stock 1024
            # local instance slots. These opaque handles are not network data.
            # Leave headroom for live actors, corpses and temporary replay copies.
            replace(path, '#define MAX_G2_MODELS (1024)', '#define MAX_G2_MODELS (8192)')
            replace(path, '#define G2_MODEL_BITS (10)', '#define G2_MODEL_BITS (13)')
            shutil.copy2(SOURCE / 'renderer_st_mvp_pose.inc', path.parent / 'renderer_st_mvp_pose.inc')
            header = '((model)->data.glm->header)' if renderer == 'rd-rend2' else '((model)->mdxm)'
            with path.open('a',encoding='utf-8') as stream:
                stream.write('\n#define ST_MVP_MODEL_HEADER(model) ' + header + '\n#include "renderer_st_mvp_pose.inc"\n')
            init = path.parent / 'tr_init.cpp'
            replace(init, '#include "tr_local.h"', '''#include "tr_local.h"
extern int ST_MvpPackPose(void *,unsigned char *,int);
extern void *ST_MvpUnpackPose(const unsigned char *,int);
''')
            replace(init, '\tre.G2API_DuplicateGhoul2Instance', '\tre.ST_MvpPackPose=ST_MvpPackPose;\n\tre.ST_MvpUnpackPose=ST_MvpUnpackPose;\n\tre.G2API_DuplicateGhoul2Instance')
            if renderer == 'rd-dedicated':
                continue
            replace(path, '\t/*ignore = */G2API_CopyGhoul2Instance(g2From, ghoul2, -1);', '''
\t/*ignore = */G2API_CopyGhoul2Instance(g2From, ghoul2, -1);
#ifdef _G2_LISTEN_SERVER_OPT
    // The local server may borrow a constructed client skeleton. DeepCopy
    // discards that cache, so its clone needs the overrides that produced it.
    // Change only the owned clone; never alter the live combat skeleton.
    if (ri.Cvar_VariableIntegerValue("st_mvpPrototype") && g2From.size() > 0) {
        const int entity = g2From[0].entityNum;
        if (entity >= 0 && entity < MAX_GENTITIES) {
            CGhoul2Info_v *rendered = g2ClientAttachments[entity];
            if (rendered && rendered != &g2From && rendered->IsValid() && rendered->size() > 0 &&
                g2From[0].mSkelFrameNum == (*rendered)[0].mSkelFrameNum &&
                g2From[0].currentModel == (*rendered)[0].currentModel)
                ghoul2[0].mBlist = (*rendered)[0].mBlist;
        }
    }
#endif''')
        path = root / 'codemp/server/sv_gameapi.cpp'
        replace(path, '#include "server.h"', '#include "server.h"\n#include <zlib.h>')
        replace(path, 'void GVM_RunFrame( int levelTime ) {', '''static int SV_MvpPackPose(void *pose,unsigned char *data,int cap) {return re->ST_MvpPackPose(pose,data,cap);}
static int SV_MvpCompress(const unsigned char *src,int size,unsigned char *dst,int cap) {
    if(size<=0 || cap<=0)return 0;
    uLongf n=cap;return compress2(dst,&n,src,size,Z_BEST_SPEED)==Z_OK ? (int)n : 0;
}
void GVM_RunFrame( int levelTime ) {''')
        replace(path, '\t\tgi.G2API_DuplicateGhoul2Instance', '\t\tgi.ST_MvpPackPose=SV_MvpPackPose;\n\t\tgi.ST_MvpCompress=SV_MvpCompress;\n\t\tgi.G2API_DuplicateGhoul2Instance')
        marker = 'void GVM_RunFrame( int levelTime ) {'
        replace(path, marker, '''qboolean GVM_MvpRead(int sourceTime, stMvpClip_t *out) {
    if (!gvm || gvm->isLegacy || !ge || !ge->ST_MvpRead ||
        !com_sv_running->integer || com_dedicated->integer) return qfalse;
    VMSwap swap(gvm);
    return ge->ST_MvpRead(sourceTime,out);
}
void GVM_MvpReset(void) {
    if (!gvm || gvm->isLegacy || !ge || !ge->ST_MvpReset) return;
    VMSwap swap(gvm);
    ge->ST_MvpReset();
}
''' + marker)
        path = root / 'codemp/client/cl_main.cpp'
        replace(path, 'static void CL_ShutdownRef( qboolean restarting );',
                'extern void GVM_MvpReset(void);\nstatic void CL_ShutdownRef( qboolean restarting );')
        for marker in ('static void CL_ShutdownRef( qboolean restarting ) {',
                       'void CL_ShutdownAll( qboolean shutdownRef ) {'):
            replace(path, marker, marker + '\n    GVM_MvpReset();')
        path = root / 'codemp/server/sv_client.cpp'
        replace(path, 'if ( !com_cl_running->integer &&', '''if ( Q_strncmp(s,"st_mvp_ack ",11) && Q_strncmp(s,"st_mvp_done ",12) &&
        !com_cl_running->integer &&''')
        path = root / 'codemp/client/cl_cgameapi.cpp'
        replace(path, '#include "client.h"', '#include "client.h"\n#include <zlib.h>')
        replace(path, 'static cgameExport_t *cge;', '''static void *CL_MvpUnpackPose(const unsigned char *data,int size) {return re->ST_MvpUnpackPose(data,size);}
static int CL_MvpDecompress(const unsigned char *src,int size,unsigned char *dst,int cap) {
    if(size<=0 || cap<=0)return 0;
    uLongf n=cap;return uncompress(dst,&n,src,size)==Z_OK ? (int)n : 0;
}
static cgameExport_t *cge;''')
        replace(path, '\t\tcgi.G2API_DuplicateGhoul2Instance', '\t\tcgi.ST_MvpUnpackPose=CL_MvpUnpackPose;\n\t\tcgi.ST_MvpDecompress=CL_MvpDecompress;\n\t\tcgi.G2API_DuplicateGhoul2Instance')
        replace(path, 'static cgameExport_t *cge;',
                '''extern qboolean GVM_MvpRead(int, stMvpClip_t *);
static qboolean CL_MvpRead(int time, stMvpClip_t *out) {
    if (clc.serverAddress.type != NA_LOOPBACK) return qfalse;
    return GVM_MvpRead(time,out);
}
static cgameExport_t *cge;''')
        replace(path, 'GetCGameAPI = (GetCGameAPI_t)cgvm->GetModuleAPI;',
                'cgi.ST_MvpRead = CL_MvpRead;\n\t\tGetCGameAPI = (GetCGameAPI_t)cgvm->GetModuleAPI;')
    elif kind == 'game':
        path = root / 'codemp/game/g_main.c'
        shutil.copy2(SOURCE / 'g_st_mvp.inc', path.parent / 'g_st_mvp.inc')
        shutil.copy2(SOURCE / 'g_st_mvp_history.inc', path.parent / 'g_st_mvp_history.inc')
        shutil.copy2(SOURCE / 'g_st_mvp_duel.inc', path.parent / 'g_st_mvp_duel.inc')
        shutil.copy2(SOURCE / 'g_st_mvp_network.inc', path.parent / 'g_st_mvp_network.inc')
        replace(path, 'void G_InitGame( int levelTime, int randomSeed, int restart ) {',
                '#include "g_st_mvp.inc"\nvoid G_InitGame( int levelTime, int randomSeed, int restart ) {\n    ST_MvpReset();')
        replace(path, 'void G_ShutdownGame( int restart ) {',
                'void G_ShutdownGame( int restart ) {\n    ST_MvpReset();')
        replace(path, '\t// see if it is time to do a tournament restart\n\tCheckTournament();',
                '\tST_MvpCapture();\n\tST_MvpNetworkFrame();\n\t// see if it is time to do a tournament restart\n\tCheckTournament();')
        replace(path, '\t// see which players are ready',
                '\tif (ST_MvpHoldIntermission()) return;\n\t// see which players are ready')
        replace(path, '\tlevel.intermissiontime = level.time;',
                '\tST_MvpDuelResult();\n\tif (ST_MvpPendingForfeit()) gDuelExit=qfalse;\n\tlevel.intermissiontime = level.time;')
        replace(path, '\t\t\tlevel.intermissionQueued = 0;\n\t\t\tBeginIntermission();',
                '\t\t\tstMvpDecisionTime=level.intermissionQueued;\n\t\t\tlevel.intermissionQueued = 0;\n\t\t\tBeginIntermission();')
        replace(path, '''\tif ( level.gametype == GT_DUEL || level.gametype == GT_POWERDUEL ) {
\t\ttrap->SetConfigstring ( CS_CLIENT_DUELWINNER, "-1" );''',
                '''\tif ( (level.gametype == GT_DUEL || level.gametype == GT_POWERDUEL) && !ST_MvpPendingForfeit() ) {
\t\ttrap->SetConfigstring ( CS_CLIENT_DUELWINNER, "-1" );''')
        text = path.read_text()
        text = text.replace('else if ( ST_DuelBestOfEnabled() )',
                            'else if ( ST_DuelBestOfEnabled() || ST_MvpPendingForfeit() )')
        path.write_text(text)
        replace(path, '\tge.InitGame', '\tge.ST_MvpRead = ST_MvpRead;\n\tge.ST_MvpReset = ST_MvpRendererReset;\n\tge.InitGame')
        path = root / 'codemp/game/g_sabertrials.c'
        replace(path, '\tlevel.clients[winner].sess.stTournamentMatchWins++;',
                '\tif (ST_MvpTournamentForfeit(winner,loser)) return;\n\tlevel.clients[winner].sess.stTournamentMatchWins++;')
        path = root / 'codemp/game/g_client.c'
        text = path.read_text(encoding='utf-8')
        text = text.replace('d_perPlayerGhoul2.integer || g_saberHandedness.integer',
            'd_perPlayerGhoul2.integer || g_saberHandedness.integer || trap->Cvar_VariableIntegerValue("st_mvpPrototype")')
        path.write_text(text,encoding='utf-8')
        replace(path, '\t\tInfo_SetValueForKey( userinfo, "saber1", saberOne );', '''
        // Private replay test bots use the currently supported capture loadout.
        // Normal bot life-to-life saber rotation remains the default.
        if (trap->Cvar_VariableIntegerValue("st_mvpPrototype") &&
            trap->Cvar_VariableIntegerValue("st_mvpTestSingleSaber") &&
            !trap->Cvar_VariableIntegerValue("dedicated")) {
            Q_strncpyz(saberOne,"single_1",sizeof(saberOne));
            Q_strncpyz(saberTwo,"none",sizeof(saberTwo));
        }
\t\tInfo_SetValueForKey( userinfo, "saber1", saberOne );''')
        replace(path, '\t// if we are playing in tourney mode, give a win to the other player and clear his frags for this round',
                '\tqboolean stMvpLeaving=ST_MvpDuelDisconnect(clientNum);\n\t// if we are playing in tourney mode, give a win to the other player and clear his frags for this round')
        replace(path, 'if ( level.gametype == GT_DUEL && !level.intermissiontime && !level.warmupTime )',
                'if ( !stMvpLeaving && level.gametype == GT_DUEL && !level.intermissiontime && !level.warmupTime )')
        replace(path, 'if ( level.gametype == GT_DUEL && ent->client->sess.sessionTeam == TEAM_FREE && level.intermissiontime )',
                'if ( level.gametype == GT_DUEL && ent->client->sess.sessionTeam == TEAM_FREE && level.intermissiontime && !ST_MvpHoldIntermission() )')
        path = root / 'codemp/game/g_combat.c'
        replace(path, '\t// check for an almost capture',
                '\tif (!stPrivateDuelDeath) ST_MvpDeath(self, attacker, meansOfDeath);\n\t// check for an almost capture')
        replace(path, '\tlimb->classname = "playerlimb";',
                '\tlimb->classname = "playerlimb";\n    if (ent->client) ST_MvpTagPart(limb->s.number,ent->s.number,ent->client->ps.persistant[PERS_SPAWN_COUNT]);')
        path = root / 'codemp/game/g_local.h'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('\nvoid ST_MvpDeath(gentity_t *victim, gentity_t *attacker, int meansOfDeath);\n')
            stream.write('void ST_MvpProofSetup(void);\nqboolean ST_MvpProofFrozen(int client);\n')
            stream.write('void ST_MvpWinnerProof(void);\n')
            stream.write('void ST_MvpTagPart(int entity,int owner,int spawn);\n')
            stream.write('qboolean ST_MvpHoldIntermission(void);\nqboolean ST_MvpNetCommand(int client,const char *command);\n')
            stream.write('qboolean ST_MvpPendingForfeit(void);\nqboolean ST_MvpTournamentForfeit(int winner,int loser);\nqboolean ST_MvpDuelDisconnect(int client);\n')
        path = root / 'codemp/game/g_cmds.c'
        marker = '    if (ST_StaffBlocked(ent) && Q_stricmp(cmd,"say") && Q_stricmp(cmd,"say_team") && Q_stricmp(cmd,"tell") && Q_stricmp(cmd,"score")) {'
        replace(path, marker,
                '    if (ST_MvpNetCommand(clientNum,cmd)) return;\n' + marker)
        path = root / 'codemp/game/g_svcmds.c'
        replace(path, '\tcommand = (svcmd_t *)Q_LinearSearch',
                '\tif (!Q_stricmp(cmd,"st_mvpproof")) { ST_MvpProofSetup(); return qtrue; }\n\tif (!Q_stricmp(cmd,"st_mvpwinnerproof")) { ST_MvpWinnerProof(); return qtrue; }\n\tcommand = (svcmd_t *)Q_LinearSearch')
        path = root / 'codemp/game/ai_main.c'
        replace(path, '\tif (gDeactivated)\n', '\tif (ST_MvpProofFrozen(bs->client)) return;\n\tif (gDeactivated)\n')
        replace(path, '\tST_BotApplyRoleCommand( bs, &bs->lastucmd );', '''
    if (ST_MvpProofFrozen(bs->client)) {
        bs->lastucmd.buttons = 0;
        bs->lastucmd.forwardmove = bs->lastucmd.rightmove = bs->lastucmd.upmove = 0;
        for (j=0; j<3; ++j)
            bs->lastucmd.angles[j] = ANGLE2SHORT(g_entities[bs->client].client->ps.viewangles[j]) - bs->cur_ps.delta_angles[j];
    } else ST_BotApplyRoleCommand( bs, &bs->lastucmd );''')
    elif kind == 'frontend':
        path = root / 'codemp/cgame/cg_view.c'
        shutil.copy2(SOURCE / 'cg_st_mvp.inc', path.parent / 'cg_st_mvp.inc')
        shutil.copy2(SOURCE / 'cg_st_mvp_effects.inc', path.parent / 'cg_st_mvp_effects.inc')
        shutil.copy2(SOURCE / 'cg_st_mvp_hud.inc', path.parent / 'cg_st_mvp_hud.inc')
        shutil.copy2(SOURCE / 'cg_st_mvp_network.inc', path.parent / 'cg_st_mvp_network.inc')
        replace(path.parent / 'cg_servercmds.c', 'if (CG_STEventMessage(cmd)) return;',
            'if (CG_STEventMessage(cmd)) return;\n    if (ST_MvpServerCommand(cmd)) return;')
        replace(path, 'void CG_DrawActiveFrame( int serverTime, stereoFrame_t stereoView, qboolean demoPlayback ) {',
                '#include "cg_st_mvp.inc"\nvoid CG_DrawActiveFrame( int serverTime, stereoFrame_t stereoView, qboolean demoPlayback ) {')
        replace(path, '\tCG_ProcessSnapshots();', '\tCG_ProcessSnapshots();\n    if (ST_MvpDraw()) return;')
        path = root / 'codemp/cgame/cg_main.c'
        replace(path, '    ST_PhotoStop();', '    ST_MvpClear();\n    ST_PhotoStop();')
        replace(path, 'static void ST_PhotoKeyEvent(int key, qboolean down) {',
                'static void ST_PhotoKeyEvent(int key, qboolean down) {\n    if (ST_MvpKey(key,down)) return;')
        replace(path, 'static void ST_PhotoEventHandling(int type) {',
                'static void ST_PhotoEventHandling(int type) {\n    if (type == CGAME_EVENT_NONE) ST_MvpStop();')
        path = root / 'codemp/cgame/cg_local.h'
        with path.open('a', encoding='utf-8') as stream:
            stream.write('\nvoid ST_MvpStop(void);\nvoid ST_MvpClear(void);\nqboolean ST_MvpKey(int key,qboolean down);\nqboolean ST_MvpTestReady(void);\nvoid ST_MvpRecordSound(const vec3_t origin,int entity,int channel,sfxHandle_t sound);\n')
            stream.write('qboolean ST_MvpDrawCard(void);\nqboolean ST_MvpServerCommand(const char *command);\n')
        path = root / 'codemp/cgame/cg_draw.c'
        replace(path, '\tif (ST_PhotoActive()) { ST_PhotoDraw(); return; }',
                '\tif (ST_MvpDrawCard()) return;\n\tif (ST_PhotoActive()) { ST_PhotoDraw(); return; }')
        for name in ('cg_players.c', 'cg_event.c'):
            path = root / 'codemp/cgame' / name
            text = path.read_text(encoding='utf-8')
            path.write_text(re.sub(r'trap->S_StartSound\s*\(', 'ST_MvpRecordSound(', text), encoding='utf-8')
        path = root / 'codemp/cgame/cg_ents.c'
        replace(path, '''\t\t// Saber Trials always renders the complete dismemberment tier, including
\t\t// decapitation and waist cuts, when the server creates a severed limb.
\t\tint dismember_settings = Q_max( cg_dismember.integer, 2 );''',
                '''\t\t// Respect the viewer's existing dismemberment preference.
\t\tint dismember_settings = cg_dismember.integer;''')
        path = root / 'codemp/cgame/cg_consolecmds.c'
        replace(path, '\tcommand = (consoleCommand_t *)Q_LinearSearch',
                '\tif (!Q_stricmp(CG_Argv(0),"st_mvptestready")) return ST_MvpTestReady();\n\tif (!Q_stricmp(CG_Argv(0),"st_mvpskip")) return ST_MvpKey(A_ENTER,qtrue);\n\tcommand = (consoleCommand_t *)Q_LinearSearch')
