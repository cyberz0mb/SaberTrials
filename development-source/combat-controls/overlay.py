"""Block, parry and feint controls."""
from pathlib import Path
import hashlib
import importlib.util
import re
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def module(name):
    spec = importlib.util.spec_from_file_location('approved_'+name, HERE/(name+'.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def change(root, name, old, new):
    p = Path(root)/name
    s = p.read_text()
    if s.count(old) != 1:
        raise ValueError('Main integration hook changed: '+name+' / '+old[:80])
    p.write_text(s.replace(old,new), encoding='utf-8', newline='\n')

def assets(out):
    package = ROOT/'zz_sabertrials_styles_v1.pk3'
    with zipfile.ZipFile(package) as z:
        cfg = z.read('models/players/_humanoid/animation.cfg')
    guards = []
    for family, donor in [('SINGLE','BOTH_P1_S1_TR'),('DUAL','BOTH_P6_S6_T_'),('STAFF','BOTH_P7_S7_T_')]:
        match = re.search(rb'(?m)^'+donor.encode()+rb'\s+(\d+)\s+(\d+)\s+(-?\d+)\s+([\d.]+)',cfg)
        if not match: raise ValueError('Missing guard donor '+donor)
        first, count = int(match[1]), int(match[2])
        guards.append(dict(name='BOTH_ST_GUARD_'+family, first=first+count-1))
    expanded = cfg + ('\n// Approved manual guard: stock final samples; torso only.\n'+''.join(
        f"{g['name']} {g['first']} 1 1 20\n" for g in guards)).encode('ascii')
    assert len(expanded)<131071
    # FS_PathCmp compares uppercase package names. Z_ sorts above ZZ_, giving
    # the table with guard poses priority over the earlier hybrid tables.
    destination = out/'z_sabertrials_combat_controls.pk3'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('models/players/_humanoid/animation.cfg', expanded)
    return dict(guards=guards, token=hashlib.sha256(expanded).hexdigest()[:16],
                original_cfg_sha256=hashlib.sha256(cfg).hexdigest(), cfg_sha256=hashlib.sha256(expanded).hexdigest())

def apply(root, kind, contract):
    root = Path(root)
    module('manual_block').apply(root,kind)
    if kind == 'engine':
        assert (root/'codemp/client/cl_input.cpp').read_text().count('{ "+feint",')==1
    else:
        module('feint_controls').apply(root,kind)
        guard=(HERE/'bg_st_manualguard.inc').read_text()
        (root/'codemp/game/bg_st_manualguard.inc').write_text(guard,encoding='utf-8')
        change(root,'codemp/game/bg_public.h','qboolean BG_SaberInSpecialAttack( int anim );',
            'qboolean BG_SaberInSpecialAttack( int anim );\nvoid BG_ST_SetManualGuard(int mode,qboolean activeDefense);')
        change(root,'codemp/game/bg_saber.c','void PM_WeaponLightsaber(void)\n{',
            '#include "bg_st_manualguard.inc"\n\nvoid PM_WeaponLightsaber(void)\n{')
        change(root,'codemp/game/bg_saber.c','\tqboolean checkOnlyWeap = qfalse;\n',
            '\tqboolean checkOnlyWeap = qfalse;\n\n\tif (PM_ST_ManualGuardFrame())return;\n')
        # Existing animation IDs, authored motions and skeletal data remain unchanged.
        change(root,'codemp/game/anims.h','\tMAX_ANIMATIONS,',
            ''.join('\t'+g['name']+',\n' for g in contract['guards'])+'\tMAX_ANIMATIONS,')
        change(root,'codemp/cgame/animtable.h','\t//must be terminated',
            ''.join('\tENUM2STRING('+g['name']+'),\n' for g in contract['guards'])+'\t//must be terminated')
        change(root,'codemp/game/st_hybrid_anims.h','#define ST_HYBRID_ASSET_VERSION "16cba8e6a67f3799"',
            '#define ST_HYBRID_ASSET_VERSION "'+contract['token']+'"')
        checks=''.join(f"    if(anims[{g['name']}].firstFrame!={g['first']} || anims[{g['name']}].numFrames!=1 || anims[{g['name']}].loopFrames!=1 || anims[{g['name']}].frameLerp!=50)return 0;\n" for g in contract['guards'])
        change(root,'codemp/game/st_hybrid_anims.h','    if(!anims)return 0;','    if(!anims)return 0;\n'+checks)
    if kind=='game':
        change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( g_manualBlocking, "0",','XCVAR_DEF( g_manualBlocking, "1",')
        change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( g_directionalFeints, "0",','XCVAR_DEF( g_directionalFeints, "1",')
        change(root,'codemp/game/g_xcvar.h','XCVAR_DEF( st_activeDefense, "1", NULL, CVAR_ARCHIVE|CVAR_LATCH, qfalse )',
            'XCVAR_DEF( st_activeDefense, "1", NULL, CVAR_ARCHIVE|CVAR_LATCH|CVAR_SERVERINFO, qfalse )')
        change(root,'codemp/game/g_stcombat.c','    BG_ST_SetParryRecovery(ST_CombatOption(ST_COMBAT_RECOVERY));',
            '    BG_ST_SetParryRecovery(ST_CombatOption(ST_COMBAT_RECOVERY));\n    BG_ST_SetManualGuard(ST_BlockingMode(),ST_CombatOption(ST_COMBAT_DEFENSE));')
        change(root,'codemp/game/g_client.c','if(g_hybridStyles.integer && !(ent->r.svFlags&SVF_BOT) &&',
            'if((g_hybridStyles.integer || ST_BlockingMode()!=0) && !(ent->r.svFlags&SVF_BOT) &&')
        change(root,'codemp/game/g_client.c','if(!isBot && g_hybridStyles.integer &&',
            'if(!isBot && (g_hybridStyles.integer || ST_BlockingMode()!=0) &&')
    if kind=='frontend':
        change(root,'codemp/cgame/cg_servercmds.c','        BG_ST_SetParryRecovery(trials);',
            '        BG_ST_SetParryRecovery(trials);\n        BG_ST_SetManualGuard(atoi(Info_ValueForKey(info,"g_manualBlocking")),\n            atoi(Info_ValueForKey(info,"st_combatMode"))==1 &&\n            atoi(Info_ValueForKey(info,"st_activeDefense"))==1);')
    if kind in ('engine','frontend'):
        shutil.copyfile(HERE.parent/'controls/st_controls_catalog.h',root/'codemp/ui/st_controls_catalog.h')
    compact_sync(root,kind)
    protocol(root,kind)
    if kind in ('frontend','game'):
        profile_uniforms(root,kind)

def profile_uniforms(root,kind):
    root = Path(root)
    patch = HERE/('profile-uniforms-'+kind+'.patch')
    command = ['git','apply','--ignore-space-change','--whitespace=nowarn',
               '--directory='+root.relative_to(ROOT).as_posix()]
    already = subprocess.run([*command,'--reverse','--check',patch],cwd=ROOT,
                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if already.returncode:
        subprocess.run([*command,patch],cwd=ROOT,check=True)
    shutil.copyfile(HERE.parent/'multiteam/st_stock_uniform.h',root/'codemp/game/st_stock_uniform.h')

def protocol(root,kind):
    # Same wire layout, changed prediction rules. Reject old feint clients even
    # if an operator turns off both the guard and hybrid-asset join gates.
    if kind=='engine':
        p=Path(root)/'codemp/client/cl_main.cpp'
        s=p.read_text();assert s.count('"st_feintProtocol","1"')==2
        p.write_text(s.replace('"st_feintProtocol","1"','"st_feintProtocol","2"'),encoding='utf-8')
    if kind=='game':
        p=Path(root)/'codemp/game/g_client.c'
        s=p.read_text();assert s.count('"st_feintProtocol"),"1"')==2
        p.write_text(s.replace('"st_feintProtocol"),"1"','"st_feintProtocol"),"2"'),encoding='utf-8')

def compact_sync(root,kind):
    """Do not spend the remaining legacy 1024-byte serverinfo budget."""
    if kind=='engine':
        p=Path(root)/'codemp/client/cl_input.cpp'
        s=p.read_text()
        duplicate='\t{ "+feint", "Withdraw a saber wind-up", IN_Button12Down, NULL },\n\t{ "-feint", NULL, IN_Button12Up, NULL },\n'
        if duplicate in s:p.write_text(s.replace(duplicate,''),encoding='utf-8')
        assert p.read_text().count('{ "+feint",')==1
        return
    change(root,'codemp/game/bg_public.h','#define CS_TFFA_TEAMS (CS_MAX + 1 + MAX_CLIENTS)',
        '#define CS_TFFA_TEAMS (CS_MAX + 1 + MAX_CLIENTS)\n'
        '#define CS_ST_COMBAT_CONTROLS (CS_TFFA_TEAMS + 1)\n'
        '#if CS_ST_COMBAT_CONTROLS >= MAX_CONFIGSTRINGS\n#error Combat controls configstring overflow\n#endif')
    if kind=='game':
        for old,new in [
            ('XCVAR_DEF( st_attackParry, "1", NULL, CVAR_SERVERINFO|CVAR_LATCH,','XCVAR_DEF( st_attackParry, "1", NULL, CVAR_LATCH,'),
            ('XCVAR_DEF( g_manualBlocking, "1", NULL, CVAR_SERVERINFO|CVAR_LATCH,','XCVAR_DEF( g_manualBlocking, "1", NULL, CVAR_LATCH,'),
            ('XCVAR_DEF( st_activeDefense, "1", NULL, CVAR_ARCHIVE|CVAR_LATCH|CVAR_SERVERINFO,','XCVAR_DEF( st_activeDefense, "1", NULL, CVAR_ARCHIVE|CVAR_LATCH,')]:
            change(root,'codemp/game/g_xcvar.h',old,new)
        change(root,'codemp/game/g_stcombat.c','    BG_ST_SetManualGuard(ST_BlockingMode(),ST_CombatOption(ST_COMBAT_DEFENSE));',
            '    BG_ST_SetManualGuard(ST_BlockingMode(),ST_CombatOption(ST_COMBAT_DEFENSE));\n'
            '    trap->SetConfigstring(CS_ST_COMBAT_CONTROLS,va("1 %d %d",ST_BlockingMode(),ST_CombatOption(ST_COMBAT_DEFENSE)?1:0));')
    else:
        change(root,'codemp/cgame/cg_servercmds.c','void CG_ParseServerinfo( void ) {',
            '''static void CG_ParseCombatControls(void) {
    int version=0,mode=0,active=0;
    if(sscanf(CG_ConfigString(CS_ST_COMBAT_CONTROLS),"%d %d %d",&version,&mode,&active)!=3 ||
       version!=1 || mode<0 || mode>2 || active<0 || active>1) {mode=0;active=0;}
    BG_ST_SetManualGuard(mode,active?qtrue:qfalse);
}

void CG_ParseServerinfo( void ) {''')
        change(root,'codemp/cgame/cg_servercmds.c',
            '        BG_ST_SetManualGuard(atoi(Info_ValueForKey(info,"g_manualBlocking")),\n            atoi(Info_ValueForKey(info,"st_combatMode"))==1 &&\n            atoi(Info_ValueForKey(info,"st_activeDefense"))==1);',
            '        CG_ParseCombatControls();')
        change(root,'codemp/cgame/cg_servercmds.c','\t} else if ( num == CS_TFFA_TEAMS ) {',
            '\t} else if ( num == CS_ST_COMBAT_CONTROLS ) {\n        CG_ParseCombatControls();\n\t} else if ( num == CS_TFFA_TEAMS ) {')
