"""Repeatable hybrid gameplay/network overlay; modifies only caller's candidate."""
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
FIELDS = ('style','requestedStyle','attackStyle','attackAnim','attackMove','strikeMs',
          'recoveryMs','committed','enabled','originalStyle','lastTime','clockSet','allowedMask',
          'loadout[0]','loadout[1]','loadout[2]','selectedStyle','requestedSelection','availableMask','comboCount','chainPending')

def change(root, name, old, new, count=1):
    path = root / name
    text = path.read_text(encoding='utf-8')
    if text.count(old) != count:
        raise ValueError(f'Hybrid hook changed {name}: {old[:90]!r}; found {text.count(old)}, expected {count}')
    path.write_text(text.replace(old,new),encoding='utf-8',newline='\n')

def wire_respawn_style(root):
    local = 'codemp/game/g_local.h'
    session = 'codemp/game/g_session.c'
    change(root, local, '\tint\t\t\tstTournamentMatchLosses;',
           '\tint\t\t\tstTournamentMatchLosses;\n\tint\t\t\tstSaberStyle;')
    change(root, local, 'void G_ST_HybridSpawn(gentity_t* ent,const char* userinfo);',
           'void G_ST_HybridSpawn(gentity_t* ent,const char* userinfo);\nvoid G_ST_HybridRememberStyle(gentity_t* ent);')
    change(root, 'codemp/game/g_combat.c', '\tself->client->ps.pm_type = PM_DEAD;',
           '\tG_ST_HybridRememberStyle(self);\n\tself->client->ps.pm_type = PM_DEAD;')
    change(root, session, '\tQ_strcat( s, sizeof( s ), va( "%i", client->sess.stTournamentMatchLosses ) );',
           '\tQ_strcat( s, sizeof( s ), va( "%i %i", client->sess.stTournamentMatchLosses, client->sess.stSaberStyle ) );')
    change(root, session, '%s %s %i %i %i %i %i %i",', '%s %s %i %i %i %i %i %i %i",')
    change(root, session, '\t\t&client->sess.stTournamentMatchLosses\n\t\t);',
           '\t\t&client->sess.stTournamentMatchLosses,\n\t\t&client->sess.stSaberStyle\n\t\t);\n'
           '\tif ( fieldsRead < 21 || !STH_SelectionValid( client->sess.stSaberStyle ) )\n\t\tclient->sess.stSaberStyle = 0;')
    change(root, session, '\tsess->stTournamentMatchLosses = 0;',
           '\tsess->stTournamentMatchLosses = 0;\n\tsess->stSaberStyle = 0;')

def apply(root, kind):
    root=Path(root)
    for name in ('st_hybrid.h','st_hybrid.c'):
        shutil.copy2(HERE/name,root/'codemp/game'/name)
    change(root,'codemp/qcommon/q_shared.h','#include "../game/st_combat_core.h"',
           '#include "../game/st_combat_core.h"\n#include "../game/st_hybrid.h"')
    change(root,'codemp/qcommon/q_shared.h','\tint stCombatFlags;','\tint stCombatFlags;\n\tSTH_State stHybrid;')
    for filename, key, version in [('codemp/game/g_public.h','GAME_API_VERSION',218),
            ('codemp/cgame/cg_public.h','CGAME_API_VERSION',219),('codemp/ui/ui_public.h','UI_API_VERSION',220)]:
        p=root/filename;s=p.read_text()
        s,n=re.subn(r'(#define\s+'+key+r'\s+)\d+',lambda m:m[1]+str(version),s)
        if n!=1:raise ValueError('Hybrid API hook '+filename)
        p.write_text(s,encoding='utf-8',newline='\n')
    if kind=='engine':
        p=root/'codemp/qcommon/msg.cpp';s=p.read_text()
        insert='\n// Hybrid selection and recovery, including both stopped clocks.\n'+''.join(
            '{ PSF(stHybrid.'+field+'), 32 },\n' for field in FIELDS)
        matches=list(re.finditer(r'netField_t\s+(?:playerStateFields|pilotPlayerStateFields|vehPlayerStateFields)\[\]\s*=\s*\{',s))
        if len(matches)!=4:raise ValueError('Hybrid playerstate table count')
        for m in reversed(matches):
            end=s.index('\n};',m.end());s=s[:end]+insert+s[end:]
        p.write_text(s,encoding='utf-8',newline='\n')
        change(root,'codemp/client/cl_main.cpp',' Cvar_Get("st_feintProtocol","1",CVAR_ROM|CVAR_USERINFO);',
               ' Cvar_Get("st_hybridProtocol","3",CVAR_ROM|CVAR_USERINFO);\n Cvar_Set("st_hybridProtocol","3");\n Cvar_Get("st_feintProtocol","1",CVAR_ROM|CVAR_USERINFO);')
        # The feint engine predates the installed portrait correction. Carry
        # forward that exact accepted fix when replacing the complete engine.
        change(root,'codemp/rd-rend2/tr_main.cpp',
               '\t// Shoud be just refef->y but this flips the menu orientation for models, so its actually needed like this\n\tif (!tr.world)',
               '\t// HUD portraits and menu models use top-origin screen coordinates even\n'
               '\t// when a map is loaded. Keep the world-view path unchanged; its render\n'
               '\t// target follows the world/postprocessing convention.\n'
               '\tif (!tr.world || (refdef->rdflags & RDF_NOWORLDMODEL))')
        return
    for target in ('game','cgame','ui'):
        change(root,'codemp/'+target+'/CMakeLists.txt','"${MPDir}/game/st_combat_core.c"',
               '"${MPDir}/game/st_combat_core.c"\n\t"${MPDir}/game/st_hybrid.c"')
    shutil.copy2(HERE/'bg_st_hybrid.inc',root/'codemp/game/bg_st_hybrid.inc')
    change(root,'codemp/game/bg_public.h','qboolean PM_ST_FeintFrame(void);',
       'qboolean PM_ST_HybridFrame(void);\nvoid BG_ST_HybridStopped(playerState_t* ps,const usercmd_t* cmd,unsigned guards);\nqboolean PM_ST_FeintFrame(void);')
    change(root,'codemp/game/bg_saber.c','static void PM_ST_FeintMove(int move);',
       'static int PM_ST_HybridCanMove(int move);\nstatic void PM_ST_HybridMove(int move);\nstatic void PM_ST_FeintMove(int move);')
    change(root,'codemp/game/bg_saber.c','qboolean PM_SaberKataDone(int curmove, int newmove);',
       'static int PM_ST_HybridUsable(void);\nqboolean PM_SaberKataDone(int curmove, int newmove);')
    change(root,'codemp/game/bg_saber.c','\tint parts = SETANIM_TORSO;\n\n\tif ( newMove == LS_READY',
       '''\tint parts = SETANIM_TORSO;
    if(!PM_ST_HybridCanMove(newMove))return;

\tif ( newMove == LS_READY''')
    change(root,'codemp/game/bg_saber.c','\t// If the move does the same animation as the last one, we need to force a restart...',
       '''    if(PM_ST_HybridUsable() && pm->ps->stHybrid.style)
        anim=STH_AnimForStyle(pm->ps->stHybrid.style,anim);
    if(STH_AnimStyle(anim) && pm->ps->torsoAnim==anim && newMove>LS_PUTAWAY)
        setflags|=SETANIM_FLAG_RESTART;
\t// If the move does the same animation as the last one, we need to force a restart...''')
    # Commit only after the engine accepted this actual animation.
    change(root,'codemp/game/bg_saber.c','\t\tPM_ST_FeintMove(newMove);',
       '\t\tPM_ST_FeintMove(newMove);\n\t\tPM_ST_HybridMove(newMove);')
    change(root,'codemp/game/bg_saber.c','\t\tpm->ps->saberBlocking = saberMoveData[newMove].blocking;',
       '\t\tpm->ps->saberBlocking = pm->ps->stHybrid.recoveryMs?BLK_NO:saberMoveData[newMove].blocking;')
    change(root,'codemp/game/bg_saber.c','#include "bg_st_feint.inc"',
       '#include "bg_st_hybrid.inc"\n#include "bg_st_feint.inc"')
    change(root,'codemp/game/bg_saber.c','qboolean PM_SaberKataDone(int curmove, int newmove)\n{',
       '''qboolean PM_SaberKataDone(int curmove, int newmove)
{
    if(PM_ST_HybridUsable() && pm->ps->stHybrid.style)
        return pm->ps->saberAttackChainCount>=STH_ChainLimit(pm->ps->stHybrid.style)?qtrue:qfalse;''')
    change(root,'codemp/game/bg_pmove.c','\tif(PM_ST_FeintFrame())return;',
       '\tif(PM_ST_HybridFrame())return;\n\tif(PM_ST_FeintFrame())return;')
    change(root,'codemp/game/bg_pmove.c','        BG_ST_FeintStopped(pmove->ps,&pmove->cmd,guards);',
       '        BG_ST_HybridStopped(pmove->ps,&pmove->cmd,guards);\n        BG_ST_FeintStopped(pmove->ps,&pmove->cmd,guards);')
    change(root,'codemp/game/bg_pmove.c','    /* Only conventional matching geometry is approved. Mixed modes retain Stock. */',
       '''    if(slot>=0 && slot<3 && pm->ps->stHybrid.style)
        slot=pm->ps->stHybrid.style-1;
    /* Only conventional matching geometry is approved. Mixed modes retain Stock. */''')
    # Classify aliases canonically but keep actual alias animation timing.
    for signature in ('qboolean BG_SpinningSaberAnim( int anim )', 'qboolean PM_InSaberAnim( int anim )'):
        change(root,'codemp/game/bg_panimate.c',signature+'\n{',signature+'\n{\n\tanim=STH_OriginalAnim(anim);')
    change(root,'codemp/game/bg_panimate.c','void BG_SaberStartTransAnim( int clientNum, int saberAnimLevel, int weapon, int anim, float *animSpeed, int broken )\n{',
       '''void BG_SaberStartTransAnim( int clientNum, int saberAnimLevel, int weapon, int anim, float *animSpeed, int broken )
{
    if(STH_AnimStyle(anim))saberAnimLevel=STH_ParentStyle(STH_AnimStyle(anim));
    anim=STH_OriginalAnim(anim);''')
    # Feint phase tracks real hybrid identity; its timing still comes from actual torsoTimer.
    change(root,'codemp/game/bg_st_feint.inc','(STC_Style)pm->ps->fd.saberAnimLevel',
       '(STC_Style)(pm->ps->stHybrid.style?pm->ps->stHybrid.style:pm->ps->fd.saberAnimLevel)',2)
    if kind!='game':
        change(root,'codemp/cgame/cg_main.c','    if(atoi(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"g_stanceLibrary")) && !ST_StanceLibraryValid(bgAllAnims[0].anims))',
          '''    if(atoi(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"g_hybridStyles")) &&
       (!ST_StanceAssetsAvailable() || !STH_AnimationsValid(bgAllAnims[0].anims)))
        trap->Error(ERR_DROP,"Hybrid styles require matching Saber Trials animation assets.");
    if(atoi(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"g_stanceLibrary")) && !ST_StanceLibraryValid(bgAllAnims[0].anims))''')
        return
    shutil.copy2(HERE/'g_st_hybrid.inc',root/'codemp/game/g_st_hybrid.inc')
    change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( g_directionalFeints,',
       'XCVAR_DEF( g_hybridStyles, "0", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( g_directionalFeints,')
    change(root,'codemp/game/g_local.h','qboolean ClientUserinfoChanged(',
       'qboolean G_ST_HybridCycle(gentity_t* ent);\nvoid G_ST_HybridUserinfo(gentity_t* ent,const char* userinfo);\nvoid G_ST_HybridSpawn(gentity_t* ent,const char* userinfo);\nvoid G_ST_HybridThink(gentity_t* ent);\nint G_ST_HybridDamageStyle(gentity_t* ent,int saberNum);\nqboolean ClientUserinfoChanged(')
    wire_respawn_style(root)
    change(root,'codemp/game/g_client.c','qboolean ClientUserinfoChanged( int clientNum ) {',
       '#include "g_st_hybrid.inc"\n\nqboolean ClientUserinfoChanged( int clientNum ) {')
    change(root,'codemp/game/g_client.c','    if(g_directionalFeints.integer && !(ent->r.svFlags&SVF_BOT)',
       '''    if(g_hybridStyles.integer && !(ent->r.svFlags&SVF_BOT) &&
       (strcmp(Info_ValueForKey(userinfo,"st_hybridProtocol"),"3") ||
        strcmp(Info_ValueForKey(userinfo,"st_hybridAssets"),ST_HYBRID_ASSET_VERSION))) {
        trap->DropClient(clientNum,"This server requires matching Saber Trials hybrid client and assets.");
        return qfalse;
    }
    G_ST_HybridUserinfo(ent,userinfo);
    if(g_directionalFeints.integer && !(ent->r.svFlags&SVF_BOT)''')
    change(root,'codemp/game/g_client.c','    if(!isBot && g_directionalFeints.integer',
       '''    if(!isBot && g_hybridStyles.integer &&
       (strcmp(Info_ValueForKey(userinfo,"st_hybridProtocol"),"3") ||
        strcmp(Info_ValueForKey(userinfo,"st_hybridAssets"),ST_HYBRID_ASSET_VERSION)))
        return "This server requires the matching Saber Trials hybrid client and animation assets.";
    if(!isBot && g_directionalFeints.integer''')
    change(root,'codemp/game/g_client.c','\tent->client->pers.cmd.serverTime = level.time;\n\tClientThink( ent-g_entities, NULL );',
       '\tG_ST_HybridSpawn(ent,userinfo);\n\tent->client->pers.cmd.serverTime = level.time;\n\tClientThink( ent-g_entities, NULL );')
    change(root,'codemp/game/g_active.c','    G_STFeintStoppedState(ent);',
       '    G_ST_HybridThink(ent);\n    G_STFeintStoppedState(ent);',2)
    change(root,'codemp/game/g_cmds.c','\tif (ent->client->saber[0].model[0] && ent->client->saber[1].model[0])\n\t{ //no cycling for akimbo',
       '''    if(G_ST_HybridCycle(ent))return;
\tif (ent->client->saber[0].model[0] && ent->client->saber[1].model[0])
\t{ //no cycling for akimbo'''.replace('\\\\"','\\"'))
    change(root,'codemp/game/w_saber.c','\t\tsaberInfo_t *saber = &ent->client->saber[saberNum];',
       '\t\tsaberInfo_t *saber = &ent->client->saber[saberNum];\n\t\tanim=STH_OriginalAnim(anim);')
    # Existing paired lock negotiation classifies the selected retimed attacks.
    # Leave playerstate and lock poses untouched; canonicalize comparisons only.
    p=root/'codemp/game/w_saber.c';s=p.read_text()
    begin=s.index('qboolean WP_SabersCheckLock(')
    end=s.index('\n}',begin)+2
    section=s[begin:end]
    for which in ('ent1','ent2'):
        section=section.replace(which+'->client->ps.torsoAnim',
                                'STH_OriginalAnim('+which+'->client->ps.torsoAnim)')
    p.write_text(s[:begin]+section+s[end:],encoding='utf-8',newline='\n')
    change(root,'codemp/game/w_saber.c','\t\tqboolean inBackAttack = G_SaberInBackAttack(self->client->ps.saberMove);\n\n\t\tif ( d_saberSPStyleDamage.integer )',
       '\t\tqboolean inBackAttack = G_SaberInBackAttack(self->client->ps.saberMove);\n\t\tint hybridDamageStyle=G_ST_HybridDamageStyle(self,rSaberNum);\n\n\t\tif ( d_saberSPStyleDamage.integer )')
    change(root,'codemp/game/w_saber.c','\t\t\tif ( g_saberRealisticCombat.integer > 1 )',
       '\t\t\tif(hybridDamageStyle && !g_saberRealisticCombat.integer)fDmg=STH_PowerFactor(hybridDamageStyle);\n\t\t\tif ( g_saberRealisticCombat.integer > 1 )')
    change(root,'codemp/game/w_saber.c','\t\t\tattackStr = self->client->ps.fd.saberAnimLevel;',
       '''            if(hybridDamageStyle==STH_GREEN)dmg=47;
            else if(hybridDamageStyle==STH_PURPLE)dmg=G_GetAttackDamage(self,2,120,0.5f);
            else if(hybridDamageStyle==STH_ORANGE)dmg=G_GetAttackDamage(self,2,90,0.5f);
\t\t\tattackStr = self->client->ps.fd.saberAnimLevel;''')
    change(root,'codemp/game/w_saber.c','\tif (SaberAttacking(self))\n\t{ //attacking, can\'t block now',
       '\tif(self->client->ps.stHybrid.recoveryMs)return 0;\n\tif (SaberAttacking(self))\n\t{ //attacking, can\'t block now')
