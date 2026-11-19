"""Narrow, repeatable overlay for the isolated feint candidate."""
from pathlib import Path
import re,shutil
HERE=Path(__file__).resolve().parent
CORE=HERE.parent/'combat-foundation'

def change(root,name,old,new,count=1):
 p=root/name;s=p.read_text()
 if s.count(old)!=count:raise ValueError(f'Changed hook {name}: {old[:70]!r} ({s.count(old)})')
 p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

def apply(root,kind):
 for name in ('st_combat_core.h','st_combat_core.c','st_combat_wire.h','st_combat_wire.c'):
  shutil.copy2(CORE/name,root/'codemp/game'/name)
 change(root,'codemp/qcommon/q_shared.h','typedef struct playerState_s {',
        '#include "../game/st_combat_core.h"\n\ntypedef struct playerState_s {')
 change(root,'codemp/qcommon/q_shared.h','} playerState_t;',
        '\tSTC_State stCombat;\n\tint stCombatFlags;\n} playerState_t;')
 change(root,'codemp/qcommon/q_shared.h','#define\tBUTTON_ATTACK',
        '#define BUTTON_FEINT 4096 // Saber Trials input bit 12\n#define\tBUTTON_ATTACK')
 # Different APIs intentionally reject old native modules with the wrong PS ABI.
 for file,pattern,version in [('codemp/game/g_public.h','GAME_API_VERSION',202),
                             ('codemp/cgame/cg_public.h','CGAME_API_VERSION',203),
                             ('codemp/ui/ui_public.h','UI_API_VERSION',204)]:
  p=root/file;s=p.read_text();s,n=re.subn(r'(#define\s+'+pattern+r'\s+)\d+',lambda m:m[1]+str(version),s)
  if n!=1:raise ValueError('API version hook '+file)
  p.write_text(s,encoding='utf-8',newline='\n')
 if kind=='engine':
  fields=['epoch','attack','lastTime','lastInputTime','style','direction','redirect','phase',
          'windupMs','elapsedMs','recoveryMs','cooldownMs','feintsUsed','contacted','held','inputSeen']
  p=root/'codemp/qcommon/msg.cpp';s=p.read_text()
  insert='\n// Saber Trials feint state: append only, preserve legacy field indices.\n'+''.join(
   '{ PSF(stCombat.'+f+'), 32 },\n' for f in fields)+'{ PSF(stCombatFlags), 32 },\n'
  matches=list(re.finditer(r'netField_t\s+(?:playerStateFields|pilotPlayerStateFields|vehPlayerStateFields)\[\]\s*=\s*\{',s))
  if len(matches)!=4:raise ValueError('Playerstate table count changed')
  for m in reversed(matches):
   end=s.index('\n};',m.end());s=s[:end]+','+insert+s[end:]
  p.write_text(s,encoding='utf-8',newline='\n')
  change(root,'codemp/client/cl_input.cpp','{ "+button12",',
    '{ "+feint", "Directional feint", IN_Button12Down, NULL },\n\t{ "-feint", NULL, IN_Button12Up, NULL },\n\t{ "+button12",')
  change(root,'codemp/client/cl_main.cpp',' Cvar_Get("st_handProtocol","0",CVAR_ROM|CVAR_USERINFO);',
    ' Cvar_Get("st_feintProtocol","1",CVAR_ROM|CVAR_USERINFO);\n Cvar_Set("st_feintProtocol","1");\n Cvar_Get("st_handProtocol","0",CVAR_ROM|CVAR_USERINFO);')
  for file,vm in [('codemp/server/sv_gameapi.cpp','gvm'),
                  ('codemp/client/cl_cgameapi.cpp','cgvm'),('codemp/client/cl_uiapi.cpp','uivm')]:
   change(root,file,'\t'+vm+' = VM_CreateLegacy(',
    '\tCom_Error(ERR_FATAL,"Saber Trials feint candidate requires matching native modules; legacy modules are not compatible.");\n\treturn;\n\t'+vm+' = VM_CreateLegacy(')
  return
 shutil.copy2(HERE/'bg_st_feint.inc',root/'codemp/game/bg_st_feint.inc')
 for target in ('game','cgame','ui'):
  file='codemp/'+target+'/CMakeLists.txt'
  change(root,file,'"${MPDir}/game/bg_saberLoad.c"',
    '"${MPDir}/game/bg_saberLoad.c"\n\t"${MPDir}/game/st_combat_core.c"\n\t"${MPDir}/game/st_combat_wire.c"')
 change(root,'codemp/game/bg_saber.c','void PM_WeaponLightsaber(void)',
        '#include "../staff/st_staff_movement.h"\n#include "bg_st_feint.inc"\n\nvoid PM_WeaponLightsaber(void)')
 change(root,'codemp/game/bg_saber.c','void PM_SetSaberMove(',
    'static void PM_ST_FeintMove(int move);\nvoid PM_SetSaberMove(')
 change(root,'codemp/game/bg_saber.c','\t\tpm->ps->saberMove = newMove;',
        '\t\tpm->ps->saberMove = newMove;\n\t\tPM_ST_FeintMove(newMove);')
 change(root,'codemp/game/bg_public.h','// playerState_t->stats[] indexes',
    'qboolean PM_ST_FeintFrame(void);\nvoid BG_ST_FeintStopped(playerState_t* ps,const usercmd_t* cmd,unsigned guards);\n\n// playerState_t->stats[] indexes')
 change(root,'codemp/game/bg_pmove.c','\tqboolean vehicleRocketLock = qfalse;',
    '\tqboolean vehicleRocketLock = qfalse;\n\n\tif(PM_ST_FeintFrame())return;')
 change(root,'codemp/game/bg_pmove.c','\t// Apply the same restrictions in server movement and local prediction.',
    '''\tif(pmove->ps->pm_type==PM_FREEZE || pmove->ps->pm_type==PM_NOCLIP || pmove->ps->stCombatFlags) {
        unsigned guards=(unsigned)pmove->ps->stCombatFlags;
        if(pmove->ps->pm_type==PM_FREEZE)guards|=STC_GUARD_FROZEN;
        if(pmove->ps->pm_type==PM_NOCLIP)guards|=STC_GUARD_GHOST;
        BG_ST_FeintStopped(pmove->ps,&pmove->cmd,guards);
    }
\t// Apply the same restrictions in server movement and local prediction.''')
 if kind!='game':return
 change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( g_stanceLibrary,',
    'XCVAR_DEF( g_directionalFeints, "0", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( g_stanceLibrary,')
 change(root,'codemp/game/g_client.c','void ClientSpawn(gentity_t *ent) {',
    'static uint32_t stFeintEpoch; /* Gamestate replacement clears old prediction. */\nvoid ClientSpawn(gentity_t *ent) {')
 change(root,'codemp/game/g_client.c','\tclient->ps.commandTime = level.time - 100;',
    '''\tclient->ps.commandTime = level.time - 100;
    if(g_directionalFeints.integer && ent->s.number<MAX_CLIENTS &&
       ent->localAnimIndex>=0 && ent->localAnimIndex<=1) {
        if(!++stFeintEpoch)++stFeintEpoch;
        STC_Init(&client->ps.stCombat,stFeintEpoch,(uint32_t)client->ps.commandTime);
    }''')
 # Connection and mid-connection capability checks: default off remains legacy.
 hook='    if(!isBot && g_saberHandedness.integer &&'
 change(root,'codemp/game/g_client.c',hook,
    '''    if(!isBot && g_directionalFeints.integer && strcmp(Info_ValueForKey(userinfo,"st_feintProtocol"),"1"))
        return "This server requires the matching Saber Trials feint engine and modules.";
'''+hook)
 hook='    if(g_saberHandedness.integer && !(ent->r.svFlags&SVF_BOT) &&'
 change(root,'codemp/game/g_client.c',hook,
    '''    if(g_directionalFeints.integer && !(ent->r.svFlags&SVF_BOT) && strcmp(Info_ValueForKey(userinfo,"st_feintProtocol"),"1")) {
        trap->DropClient(clientNum,"This server requires the matching Saber Trials feint client.");
        return qfalse;
    }
'''+hook)
 change(root,'codemp/game/w_saber.c','\tif ( self->client->ps.saberAttackWound < level.time\n',
    '''    /* Contact precedes damage/defense filtering; a blocked/absorbed hit
     * cannot be cancelled retroactively. World contact also commits a feint. */
    if(self->client->ps.stCombat.epoch && tr.entityNum!=ENTITYNUM_NONE &&
       (tr.fraction<1.0f || tr.startsolid || tr.allsolid))STC_Contact(&self->client->ps.stCombat);
\tif ( self->client->ps.saberAttackWound < level.time
''')
 shutil.copy2(HERE/'g_st_feint.inc',root/'codemp/game/g_st_feint.inc')
 change(root,'codemp/game/g_active.c','void ClientThink_real( gentity_t *ent ) {',
    '#include "g_st_feint.inc"\n\nvoid ClientThink_real( gentity_t *ent ) {')
 change(root,'codemp/game/g_active.c','    if (ST_StaffThink(ent)) return;',
    '    G_STFeintStoppedState(ent);\n    if (ST_StaffThink(ent)) return;',2)
