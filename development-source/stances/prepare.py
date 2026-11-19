"""Narrow overlay for the accepted source snapshots; never touches live sources."""
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def change(source, name, old, new, count=1):
    p=source/name; text=p.read_text()
    if text.count(old)!=count: raise ValueError(f'Hook changed: {name}: {old[:90]} ({text.count(old)})')
    p.write_text(text.replace(old,new), encoding='utf-8', newline='\n')

def runtime_header(manifest):
    rows='\n'.join(f'    {{{p["frame"]},{p["count"]},{math.ceil(1000/p["fps"])},{p["loop"]}}},' for p in manifest['stances'])
    return '''/* Generated from the hash-locked ready-pose library; no combat replacements. */
#ifndef ST_STANCE_RUNTIME_H
#define ST_STANCE_RUNTIME_H
#include "st_stance_policy.h"
static int ST_IsReadyPose(int anim) {return anim>=BOTH_ST_READY_01 && anim<=BOTH_ST_READY_15;}
static int ST_StanceLibraryValid(const animation_t* anims) {
    static const int expected[15][4]={
'''+rows+'''
    };
    int i;
    if(!anims)return 0;
    for(i=0;i<15;i++) {
        const animation_t* a=&anims[BOTH_ST_READY_01+i];
        if(a->firstFrame!=expected[i][0] || a->numFrames!=expected[i][1] ||
           a->frameLerp!=expected[i][2] || a->loopFrames!=expected[i][3])return 0;
    }
    return 1;
}
#endif
'''

def asset_header(manifest):
    return '''/* Resolved-file compatibility check; not a cryptographic trust claim. */
#ifndef ST_STANCE_ASSETS_H
#define ST_STANCE_ASSETS_H
static int ST_StanceAssetsCheck(void) {
    fileHandle_t file=0;
    unsigned char buffer[8192];
    unsigned int hash=2166136261U;
    int remaining=trap->FS_Open("models/players/_humanoid/_humanoid.gla",&file,FS_READ),count,i;
    if(!file)return 0;
    if(remaining!='''+str(manifest['gla_size'])+''') {trap->FS_Close(file);return 0;}
    while(remaining>0) {
        count=remaining>(int)sizeof(buffer)?(int)sizeof(buffer):remaining;
        trap->FS_Read(buffer,count,file);
        for(i=0;i<count;i++)hash=(hash^buffer[i])*16777619U;
        remaining-=count;
    }
    trap->FS_Close(file);
    return hash=='''+str(manifest['gla_fnv32'])+'''U;
}
static int ST_StanceAssetsAvailable(void) {
    static int available=-1;
    if(available<0)available=ST_StanceAssetsCheck();
    return available;
}
#endif
'''

def apply(source,kind,manifest):
    poses=manifest['stances']
    (source/'codemp/game/st_stance_policy.h').write_bytes((HERE/'st_stance_policy.h').read_bytes())
    (source/'codemp/game/st_stance_runtime.h').write_text(runtime_header(manifest),newline='\n')
    (source/'codemp/game/st_stance_assets.h').write_text(asset_header(manifest),newline='\n')
    change(source,'codemp/game/anims.h','\tMAX_ANIMATIONS,',''.join(f'\t{p["animation"]},\n' for p in poses)+'\tMAX_ANIMATIONS,')
    change(source,'codemp/cgame/animtable.h','\t//must be terminated',''.join(f'\tENUM2STRING({p["animation"]}),\n' for p in poses)+'\t//must be terminated')
    # Preserve every original stat index and the engine's existing 16-bit stat layout.
    change(source,'codemp/game/bg_public.h','\tSTAT_MAX_HEALTH\t','\tSTAT_MAX_HEALTH,\n\tSTAT_ST_STANCES_A = 9, STAT_ST_STANCES_B, STAT_ST_STANCES_C, STAT_ST_STANCES_ACTIVE\t')
    for filename in ('bg_panimate.c','bg_pmove.c','bg_saber.c'):
        change(source,'codemp/game/'+filename,'#include "bg_local.h"','#include "bg_local.h"\n#include "st_stance_runtime.h"')
    for signature in ('qboolean BG_SaberStanceAnim( int anim )','qboolean BG_InSaberStandAnim( int anim )'):
        change(source,'codemp/game/bg_panimate.c',signature+'\n{',signature+'\n{\n\tif(ST_IsReadyPose(anim))return qtrue;')
    change(source,'codemp/game/bg_pmove.c','int PM_GetSaberStance(void)','static int PM_GetStockSaberStance(void)')
    file=source/'codemp/game/bg_pmove.c';text=file.read_text(); start=text.index('static int PM_GetStockSaberStance(void)'); end=text.index('\n}',start)+2
    wrapper='''

int PM_GetSaberStance(void) {
    int original=PM_GetStockSaberStance(),slot=-1,id;
    saberInfo_t *first=BG_MySaber(pm->ps->clientNum,0), *second=BG_MySaber(pm->ps->clientNum,1);
    if(pm->ps->stats[STAT_ST_STANCES_ACTIVE]!=ST_STANCE_ACTIVE_MARKER)return original;
    /* Explicit weapon constraints win, even if their readyAnim equals a stock ID. */
    if(!pm->ps->saberEntityNum || BG_SabersOff(pm->ps) ||
       (first && first->readyAnim!=-1) || (second && second->readyAnim!=-1))return original;
    switch(original) {
    case BOTH_SABERFAST_STANCE: slot=0;break;
    case BOTH_STAND2: slot=1;break;
    case BOTH_SABERSLOW_STANCE: slot=2;break;
    case BOTH_SABERDUAL_STANCE: slot=6;break;
    case BOTH_SABERSTAFF_STANCE: slot=9;break;
    }
    /* Only conventional matching geometry is approved. Mixed modes retain Stock. */
    if(!first)return original;
    if(slot>=0 && slot<6) {
        if(first->type!=SABER_SINGLE || first->numBlades!=1 || second)return original;
    } else if(slot==6) {
        if(first->type!=SABER_SINGLE || first->numBlades!=1 || !second ||
           second->type!=SABER_SINGLE || second->numBlades!=1 || pm->ps->saberHolstered)return original;
    } else if(slot==9) {
        if(first->type!=SABER_STAFF || first->numBlades!=2 || second || pm->ps->saberHolstered)return original;
    }
    id=ST_StanceChoice(&pm->ps->stats[STAT_ST_STANCES_A],slot,ST_StanceLibraryValid(pm->animations));
    return id?BOTH_ST_READY_01+id-1:original;
}
'''
    file.write_text(text[:end]+wrapper+text[end:],newline='\n')
    # Both slope switches already treat stock single ready poses as neutral leg poses.
    text=file.read_text()
    for tabs in ('\t','\t\t'):
        old=tabs+'case BOTH_STAND2:\n'+tabs+'case BOTH_SABERFAST_STANCE:'
        new=''.join(tabs+'case '+p['animation']+':\n' for p in poses)+old
        change(source,'codemp/game/bg_pmove.c',old,new)
    change(source,'codemp/game/bg_pmove.c','\t\t|| (pm->ps->legsAnim) == BOTH_STAND1\n',
           '\t\t|| ST_IsReadyPose(pm->ps->legsAnim)\n\t\t|| (pm->ps->legsAnim) == BOTH_STAND1\n')
    change(source,'codemp/game/bg_saber.c','pm->ps->torsoAnim == BOTH_SABERDUAL_STANCE//not already attacking',
           '(pm->ps->torsoAnim == BOTH_SABERDUAL_STANCE || ST_IsReadyPose(pm->ps->torsoAnim))//not already attacking')
    if kind=='game':
        change(source,'codemp/game/g_xcvar.h','XCVAR_DEF( g_saberHandedness,',
               'XCVAR_DEF( g_stanceLibrary, "1", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( g_saberHandedness,')
        change(source,'codemp/game/g_client.c','#include "bg_saga.h"','#include "bg_saga.h"\n#include "st_stance_runtime.h"\n#include "st_stance_assets.h"')
        change(source,'codemp/game/g_client.c','\tclient->pers = saved;','''\tclient->pers = saved;
    {
        int choices[ST_STANCE_SLOTS]={0};
        int enabled=g_stanceLibrary.integer && !strcmp(Info_ValueForKey(userinfo,"st_stanceProtocol"),ST_STANCE_VERSION) &&
           ent->localAnimIndex>=0 && ent->localAnimIndex<=1 &&
           ST_StanceLibraryValid(bgAllAnims[ent->localAnimIndex].anims) && ST_StanceAssetsAvailable();
        if(enabled)
            ST_StanceParse(Info_ValueForKey(userinfo,"saberStances"),choices);
        ST_StancePack(choices,&client->ps.stats[STAT_ST_STANCES_A]);
        client->ps.stats[STAT_ST_STANCES_ACTIVE]=enabled?ST_STANCE_ACTIVE_MARKER:0;
    }''')
        change(source,'codemp/game/g_client.c','\tvalue = Info_ValueForKey( userinfo, "ja_guid" );','''    if(!isBot && g_stanceLibrary.integer &&
       strcmp(Info_ValueForKey(userinfo,"st_stanceProtocol"),ST_STANCE_VERSION))
        return "This server requires the Saber Trials stance library client and matching assets.";
\tvalue = Info_ValueForKey( userinfo, "ja_guid" );''')
    if kind=='frontend':
        change(source,'codemp/cgame/cg_main.c','#include "cg_local.h"',
               '#include "cg_local.h"\n#include "game/st_stance_runtime.h"\n#include "game/st_stance_assets.h"')
        change(source,'codemp/cgame/cg_main.c','\tCG_ParseServerinfo();','''\tCG_ParseServerinfo();
    /* Pure-server mount changes happen after the UI handshake. Check again here. */
    if(atoi(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"g_stanceLibrary")) && !ST_StanceAssetsAvailable())
        trap->Error(ERR_DROP,"Saber Trials stance assets are missing or overridden. Use the matching stance package.");''')
        change(source,'codemp/cgame/cg_main.c','\tCG_RegisterClients();\t\t// if low on memory, some clients will be deferred','''\tCG_RegisterClients();\t\t// if low on memory, some clients will be deferred
    if(atoi(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"g_stanceLibrary")) && !ST_StanceLibraryValid(bgAllAnims[0].anims))
        trap->Error(ERR_DROP,"Saber Trials stance animation definitions are missing or overridden.");''')
        change(source,'codemp/ui/ui_xcvar.h','XCVAR_DEF( saberHand,',
               'XCVAR_DEF( saberStances, "000000000000", NULL, CVAR_ARCHIVE|CVAR_USERINFO )\nXCVAR_DEF( st_stanceProtocol, "0", NULL, CVAR_USERINFO|CVAR_ROM )\nXCVAR_DEF( saberHand,')
        (source/'codemp/ui/ui_st_stances.inc').write_bytes((HERE/'ui_st_stances.inc').read_bytes())
        change(source,'codemp/ui/ui_sabertrials_menu.inc','#include "ui_st_handedness.inc"',
               '#include "ui_st_handedness.inc"\n#include "ui_st_stances.inc"')
        change(source,'codemp/ui/ui_sabertrials_menu.inc',' ST_UIHandPreview(menu);',' ST_UIHandPreview(menu);\n ST_UIStanceRefresh(menu);')
        change(source,'codemp/ui/ui_sabertrials_menu.inc','\tif (ST_UIHudScript(name)) return qtrue;',
               '\tif (ST_UIStanceScript(name)) return qtrue;\n\tif (ST_UIHudScript(name)) return qtrue;')
        # Separate preview-only hilt cvars; selecting families must not rewrite equipment.
        change(source,'codemp/ui/ui_saber.c','&& ((!Q_stricmp(item->window.name,"st_hand_preview")) ?',
               '&& ((!Q_stricmp(item->window.name,"st_stance_preview")) ? trap->Cvar_VariableValue("ui_stanceFamily")==1 : (!Q_stricmp(item->window.name,"st_hand_preview")) ?')
        change(source,'codemp/ui/ui_saber.c','if(!Q_stricmp(item->window.name,"st_hand_preview"))\n                trap->Cvar_VariableStringBuffer',
               'if(!Q_stricmp(item->window.name,"st_stance_preview"))\n                trap->Cvar_VariableStringBuffer(saberNum?"ui_stanceHilt2":"ui_stanceHilt",saber,sizeof(saber));\n            else if(!Q_stricmp(item->window.name,"st_hand_preview"))\n                trap->Cvar_VariableStringBuffer')
        # UI shared is built into cgame as well: keep the existing trap capability guard.
        change(source,'codemp/ui/ui_shared.c','if(item->window.name && !Q_stricmp(item->window.name,"st_hand_preview")) {',
               'if(item->window.name && (!Q_stricmp(item->window.name,"st_hand_preview") || !Q_stricmp(item->window.name,"st_stance_preview"))) {')
        change(source,'codemp/ui/ui_shared.c','if(trap->Cvar_VariableValue("ui_saberHand")==1)flags|=BONE_ANIM_MIRROR;',
               'if(trap->Cvar_VariableValue(!Q_stricmp(item->window.name,"st_stance_preview")?"ui_stanceHand":"ui_saberHand")==1)flags|=BONE_ANIM_MIRROR;')
        change(source,'codemp/ui/ui_shared.c','if(item->window.name && !Q_stricmp(item->window.name,"st_hand_preview"))\n                                    trap->Cvar_Set("ui_handSupported",applied?"1":"0");',
               'if(item->window.name && !Q_stricmp(item->window.name,"st_hand_preview"))\n                                    trap->Cvar_Set("ui_handSupported",applied?"1":"0");\n                                if(item->window.name && !Q_stricmp(item->window.name,"st_stance_preview"))\n                                    trap->Cvar_Set("ui_stanceSupported",applied?"1":"0");')
        change(source,'codemp/ui/ui_shared.c','if (uiInfo.moveAnimTime && (uiInfo.moveAnimTime < uiInfo.uiDC.realTime))',
               'if (Q_stricmp(item->window.name,"st_stance_preview") && uiInfo.moveAnimTime && (uiInfo.moveAnimTime < uiInfo.uiDC.realTime))')
