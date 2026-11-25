"""Reuse accepted regression fixtures against literal main-integration code."""
from pathlib import Path
import re, subprocess, sys
candidate,out,baseline_tree=map(Path,sys.argv[1:])
root=Path(__file__).resolve().parents[2]
fixtures=Path(__file__).resolve().parent/'fixtures'
game=candidate/'game/codemp/game'
out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,Path(__file__).with_name('prepare_feint_clock.py'),candidate,out],check=True)
def block(path,marker):
    s=path.read_text();start=s.index(marker);at=s.index('{',start)+1;depth=1
    while depth:
        depth+=(s[at]=='{')-(s[at]=='}');at+=1
    return s[start:at]
pieces=[block(game/'g_sabertrials.c','void ST_UpdateParryInput('),
    block(game/'w_saber.c','static qboolean ST_ConsumePerfectParry('),
    block(game/'w_saber.c','static void ST_ResolvePerfectParry('),
    block(game/'w_saber.c','int WP_SaberCanBlock(')]
(out/'manual_block_production.inc').write_text('#include "g_st_parrycontact.inc"\n'+'\n'.join(pieces))
for fixture in fixtures.iterdir():
    (out/fixture.name).write_bytes(fixture.read_bytes())
source=(game/'w_saber.c').read_text()
assert source.count('ST_TryAttackParryContact(self,')==2
missile=block(game/'w_saber.c','void WP_SaberStartMissileBlockCheck(')
assert missile.index('ST_BlockInputAllowed')<missile.index('if (!doFullRoutine)')
baseline=baseline_tree/'codemp/game'
for name in ('st_hybrid.c','st_hybrid.h','g_missile.c','g_combat.c'):
    assert (game/name).read_bytes()==(baseline/name).read_bytes(),name+' changed unexpectedly'
print('Main damage, network state and physical projectile paths preserved; production adapters extracted.')
front=candidate/'frontend/codemp/cgame/cg_servercmds.c'
(out/'combat_sync.inc').write_text(block(front,'static void CG_ParseCombatControls(void)'))
# New rules use their own tiny configstring; the public browser/status info
# must not grow beyond its existing legacy 1024-byte budget.
def info_names(path):
    return set(re.findall(r'XCVAR_DEF\(\s*(\w+),[^\n]*CVAR_SERVERINFO',path.read_text()))
assert info_names(game/'g_xcvar.h')==info_names(baseline/'g_xcvar.h')
assert 'trap->SetConfigstring(CS_ST_COMBAT_CONTROLS,va("1 %d %d"' in (game/'g_stcombat.c').read_text()
assert 'num == CS_ST_COMBAT_CONTROLS' in front.read_text()
