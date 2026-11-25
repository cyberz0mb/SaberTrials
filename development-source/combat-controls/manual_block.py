"""Dedicated manual guard using existing saber defense; isolated candidate only."""
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent

def change(root,name,old,new,count=1):
    p=Path(root)/name;s=p.read_text()
    if s.count(old)!=count:raise ValueError('Manual block hook changed: '+name+' / '+old[:70])
    p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

def apply(root,kind):
    change(root,'codemp/qcommon/q_shared.h','#define BUTTON_FEINT 4096',
           '#define BUTTON_BLOCK 8192 // Dedicated guard, existing usercmd bit 13\n#define BUTTON_FEINT 4096')
    if kind=='engine':
        change(root,'codemp/client/cl_input.cpp','\t{ "+button13",',
               '\t{ "+block", "Manual saber block", IN_Button13Down, NULL },\n\t{ "-block", NULL, IN_Button13Up, NULL },\n\t{ "+button13",')
    if kind=='frontend':
        change(root,'codemp/ui/ui_shared.c','\t"+button2",','\t"+block",\n\t"+button2",')
    if kind!='game':return
    shutil.copy2(HERE/'g_st_manualblock.inc',Path(root)/'codemp/game/g_st_manualblock.inc')
    shutil.copy2(HERE/'g_st_parrycontact.inc',Path(root)/'codemp/game/g_st_parrycontact.inc')
    change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( g_directionalFeints,',
           'XCVAR_DEF( st_attackParry, "1", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( st_attackParryWindow, "150", NULL, CVAR_ARCHIVE, qtrue )\nXCVAR_DEF( g_manualBlocking, "0", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( g_directionalFeints,')
    change(root,'codemp/game/g_local.h','\tint\t\t\tstParryWindowEnd;',
           '\tint stManualBlockHeld; /* server-owned edge latch, reset with client */\n\tint stParryAttackHeld, stAttackParryEnd;\n\tint\t\t\tstParryWindowEnd;')
    change(root,'codemp/game/g_local.h','void ST_UpdateParryInput(',
           'int ST_BlockingMode(void);\nqboolean ST_AttackParryEnabled(const gentity_t *ent);\nqboolean ST_AttackParryReady(gentity_t *ent);\nqboolean ST_ConsumeAttackParry(gentity_t *ent,vec3_t point);\nqboolean ST_BlockInputAllowed(gentity_t *ent,const usercmd_t *cmd);\nqboolean ST_ManualBlockEligible(gentity_t *ent,const usercmd_t *cmd);\nqboolean ST_ActiveGuard(gentity_t *ent);\nvoid ST_ManualBlockStopped(gentity_t *ent);\nvoid ST_UpdateParryInput(')
    change(root,'codemp/game/g_sabertrials.c','void ST_UpdateParryInput( gentity_t *ent, const usercmd_t *ucmd ) {',
           '#include "g_st_manualblock.inc"\n\nvoid ST_UpdateParryInput( gentity_t *ent, const usercmd_t *ucmd ) {')
    change(root,'codemp/game/g_sabertrials.c','\tclient = ent->client;\n\tif ( !ST_CombatOption(ST_COMBAT_DEFENSE) ) {',
           '\tclient = ent->client;\n\tif (ST_AttackParryEnabled(ent)) { ST_UpdateAttackParryInput(ent,ucmd);return; }\n\tclient->stAttackParryEnd=0;client->stParryAttackHeld=(ucmd->buttons&BUTTON_ATTACK)!=0;\n\tif (ST_ManualBlockEnabled()) { ST_UpdateManualBlockInput(ent,ucmd);return; }\n\tclient->stManualBlockHeld=0;\n\tif ( !ST_CombatOption(ST_COMBAT_DEFENSE) ) {')
    change(root,'codemp/game/g_active.c','    if (ST_StaffThink(ent)) return;',
           '    ST_ManualBlockStopped(ent);\n    if (ST_StaffThink(ent)) return;',2)
    change(root,'codemp/game/w_saber.c','activeGuard = meleeAttack && (self->client->pers.cmd.buttons & BUTTON_WALKING);',
           'activeGuard = meleeAttack && ST_ActiveGuard(self);')
    change(root,'codemp/game/w_saber.c','static qboolean ST_ConsumePerfectParry( gentity_t *defender, vec3_t hitPos )\n{',
           '#include "g_st_parrycontact.inc"\n\nstatic qboolean ST_ConsumePerfectParry( gentity_t *defender, vec3_t hitPos )\n{\n\tif (ST_AttackParryEnabled(defender))return qfalse; /* Attack timing uses the actual-contact gate. */\n\tif (ST_BlockingMode()!=0 && (!defender || !defender->client ||\n\t    !ST_ManualBlockEligible(defender,&defender->client->pers.cmd)))return qfalse;')
    change(root,'codemp/game/w_saber.c','\tperfectParry = meleeAttack && self->client->stParryWindowEnd >= level.time;',
           '\tif (!ST_BlockInputAllowed(self,&self->client->pers.cmd))return 0;\n\tperfectParry = meleeAttack && !ST_AttackParryEnabled(self) && self->client->stParryWindowEnd >= level.time;')
    change(root,'codemp/game/w_saber.c','&& WP_SaberCanBlock(&g_entities[tr.entityNum], tr.endpos, 0, MOD_SABER, qfalse, attackStr))',
           '&& (ST_TryAttackParryContact(self,&g_entities[tr.entityNum],tr.endpos,dmg,unblockable) ||\n\t\t\t    WP_SaberCanBlock(&g_entities[tr.entityNum], tr.endpos, 0, MOD_SABER, qfalse, attackStr)))')
    change(root,'codemp/game/w_saber.c','\t\tif ( otherOwner && otherOwner->client && dmg > SABER_NONATTACK_DAMAGE &&\n\t\t\t!unblockable && SaberAttacking( self ) && !SaberAttacking( otherOwner ) &&\n\t\t\tST_ConsumePerfectParry( otherOwner, tr.endpos ) )',
           '\t\tif (ST_TryAttackParryContact(self,otherOwner,tr.endpos,dmg,unblockable) ||\n\t\t    (otherOwner && otherOwner->client && dmg > SABER_NONATTACK_DAMAGE &&\n\t\t\t!unblockable && SaberAttacking( self ) && !SaberAttacking( otherOwner ) &&\n\t\t\tST_ConsumePerfectParry( otherOwner, tr.endpos )))')
    change(root,'codemp/game/w_saber.c','\t\tdefender->client->ps.saberMove = parryMove;',
           '\t\tdefender->client->ps.saberMove = parryMove;\n\t\tif (ST_AttackParryEnabled(defender)) {\n\t\t\t/* Replace the interrupted startup visibly; legs and movement remain free. */\n\t\t\tG_SetAnim(defender,NULL,SETANIM_TORSO,saberMoveData[parryMove].animToUse,\n\t\t\t    SETANIM_FLAG_OVERRIDE|SETANIM_FLAG_HOLD,0);\n\t\t}')
    change(root,'codemp/game/w_saber.c','\t//keep this updated even if we don\'t get below',
           '\t/* Manual-only suppresses automatic interception, not look-target updates. */\n\tif (!ST_BlockInputAllowed(self,ucmd))doFullRoutine=qfalse;\n\t//keep this updated even if we don\'t get below')
