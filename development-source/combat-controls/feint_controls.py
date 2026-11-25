"""Expose responsive ordinary single-saber feints for local review."""
from pathlib import Path

def change(p,old,new):
    s=p.read_text()
    if s.count(old)!=1:raise ValueError('Feint hook changed: '+str(p))
    p.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

def apply(root,kind):
    if kind!='engine':
        core=Path(root)/'codemp/game/st_combat_core.c'
        # The entire ordinary START move is decision time. STC_Advance and the
        # shared move hook still reject expired/committed/contacted attacks.
        # Each new wind-up can be withdrawn, including a redirected wind-up.
        # Recovery and input-edge checks remain; no extra lockout is imposed.
        change(core,'STC_Rules r={STC_RULESET_VERSION,0,20,600,200,600};',
                    'STC_Rules r={STC_RULESET_VERSION,0,0,1000,200,600};')
        change(core,'r->windowPermille>0 && r->windowPermille<1000 &&',
                    'r->windowPermille>0 && r->windowPermille<=1000 &&')
        change(core,' if(redirect==s->direction)return STC_SAME_DIRECTION;',
                    ' /* Keeping direction is also a valid withdrawal. Held Attack\n'
                    '  * may restart that direction after the same paid recovery. */')
        change(core,'STC_Result STC_Input(STC_State* s,uint32_t now,int pressed,',
                    '/* Only supported styles get repeatable feints. */\n'
                    'static int repeatableFeintStyle(STC_Style style) {\n'
                    ' return style==STC_SINGLE_BLUE || style==STC_SINGLE_YELLOW ||\n'
                    '        style==STC_SINGLE_RED || style==STC_SINGLE_GREEN || style==STC_SINGLE_ORANGE;\n'
                    '}\n'
                    'STC_Result STC_Input(STC_State* s,uint32_t now,int pressed,')
        change(core,' if(s->feintsUsed)return STC_ALREADY_FEINTED;\n if(s->cooldownMs)return STC_COOLDOWN;',
                    ' /* Fresh presses may withdraw successive supported wind-ups. */\n'
                    ' if(!repeatableFeintStyle(s->style)) {\n'
                    '  if(s->feintsUsed)return STC_ALREADY_FEINTED;\n'
                    '  if(s->cooldownMs)return STC_COOLDOWN;\n'
                    ' }')
        change(core,' s->recoveryMs=rules->recoveryMs;s->cooldownMs=rules->cooldownMs;',
                    ' s->recoveryMs=rules->recoveryMs;\n'
                    ' s->cooldownMs=repeatableFeintStyle(s->style)?rules->recoveryMs:rules->cooldownMs;')
        p=Path(root)/'codemp/game/bg_st_feint.inc'
        change(p,' if(pm->ps->groundEntityNum==ENTITYNUM_NONE || (pm->ps->pm_flags&PMF_DUCKED) || pm->cmd.upmove)\n  guards|=STC_GUARD_SPECIAL;',
                 ' /* Ordinary supported wind-ups remain eligible in the air/crouch.\n'
                 '  * Preserve the restricted startup path for the remaining style. */\n'
                 ' if(pm->ps->stHybrid.style==STC_SINGLE_PURPLE &&\n'
                 '    (pm->ps->groundEntityNum==ENTITYNUM_NONE || (pm->ps->pm_flags&PMF_DUCKED) || pm->cmd.upmove))\n'
                 '  guards|=STC_GUARD_SPECIAL;')
        change(p,'   if(!pm->cmd.forwardmove && !pm->cmd.rightmove) {parts=SETANIM_BOTH;pm->ps->legsTimer=0;}',
                 '   if(pm->ps->groundEntityNum!=ENTITYNUM_NONE && !(pm->ps->pm_flags&PMF_DUCKED) &&\n'
                 '      !pm->cmd.upmove && !pm->cmd.forwardmove && !pm->cmd.rightmove) {\n'
                 '    parts=SETANIM_BOTH;pm->ps->legsTimer=0;\n'
                 '   }')
        s=p.read_text()
        # PmoveSingle copies the real simulation time to ps->commandTime
        # before running weapons. Stock PM_irand_timesync subsequently reuses
        # cmd.serverTime as an RNG seed. Keep that stock RNG behavior intact.
        if s.count('pm->cmd.serverTime')!=4:
            raise ValueError('Feint simulation-clock hook changed')
        s=s.replace('pm->cmd.serverTime','pm->ps->commandTime')
        s=s.replace('#include "st_combat_wire.h"',
            '#include "st_combat_wire.h"\n/* Use the stable Pmove clock; cmd.serverTime can become a stock RNG seed. */')
        p.write_text(s,encoding='utf-8',newline='\n')
    if kind=='frontend':
        change(Path(root)/'codemp/ui/ui_shared.c','\t"+button2",','\t"+button2",\n\t"+feint",')
