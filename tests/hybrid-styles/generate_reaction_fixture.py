"""Extract unchanged stock reaction/return paths, with explicit narrow dispatch."""
from pathlib import Path
import sys

root,out=map(Path,sys.argv[1:])
s=(root/'game/codemp/game/bg_saber.c').read_text()
start=s.index('\t// Now we react to a block action')
end=s.index('\nweapChecks:',start)
blocks=s[start:end]
start=s.index('\t\telse if ( !(pm->cmd.buttons & (BUTTON_ATTACK|BUTTON_ALT_ATTACK)) )')
brace=s.index('{',start);depth=1;at=brace+1
while depth:
    depth+=(s[at]=='{')-(s[at]=='}');at+=1
returns=s[brace:at]
# The stock block/return bodies are compiled verbatim. The wrapper dispatch
# substitutes only unrelated weapon modes and rendering dependencies.
assert s.index('\t\tpm->ps->weaponTime -= pml.msec;',s.index('weapChecks:')-15000)<s.index('// Now we react')
blocking=[line.strip() for line in s.splitlines() if 'pm->ps->saberBlocking =' in line]
assert len(blocking)==1 and 'stHybrid.recoveryMs?BLK_NO:' in blocking[0]
out.with_name('reaction_blocking.inc').write_text(blocking[0].replace('[newMove]','[move]')+'\n',encoding='utf-8')
prefix="""/* Generated from actual stock reaction/return branches. */
static void ProductionWeaponReactions(void) {
 int curmove,newmove=LS_NONE;
 if(pm->ps->weaponTime>0)pm->ps->weaponTime-=pml.msec;
"""
middle="""
 if(pm->ps->weaponTime>0)return;
 curmove=pm->ps->saberMove;
 if(!(pm->cmd.buttons&(BUTTON_ATTACK|BUTTON_ALT_ATTACK)))
"""
suffix="""
 if(newmove!=LS_NONE) {
  PM_SetSaberMove((short)newmove);pm->ps->weaponTime=pm->ps->torsoTimer;
 }
}
"""
out.write_text(prefix+blocks+middle+returns+suffix,encoding='utf-8')
