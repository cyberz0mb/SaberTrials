"""Keep legacy Profile action scripts verbatim in the new native surfaces."""
from pathlib import Path
import importlib.util,re,subprocess
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'development-source/profile'
spec=importlib.util.spec_from_file_location('menu_blocks',ROOT/'tools/Stage-Tournament-Frontend.py');blocks=importlib.util.module_from_spec(spec);spec.loader.exec_module(blocks)
BASE='71d8fdd'
def main():
 for file,menu in (('player.menu','playerMenu'),('ingame_player.menu','ingame_player')):
  text=subprocess.check_output(['git','show',BASE+':ui/jamp/'+file],cwd=ROOT,text=True)
  mapping={'sp_action_custom':'custom','sp_action_saber':'next'} if menu=='playerMenu' else {'sp_action_custom':'custom','sp_action_saber':'saber','sp_action_force':'configforcebutton','sp_action_join':'applyjoin','sp_action_red':'applyred','sp_action_blue':'applyblue','sp_action_spectate':'applyspectate'}
  lines=['// Native Profile browser; legacy action scripts preserved from '+BASE+'.','{ menuDef { name "'+menu+'" fullscreen 1 rect 0 0 640 480 visible 0 style 1 backcolor .027 .063 .098 1 focusColor 1 1 1 1',
   'onOpen { uiScript update "ui_GetName"; '+('uiScript updateForceStatus;' if menu=='ingame_player' else '')+' }',
   'itemDef { name st_profile_preview type ITEM_TYPE_MODEL rect 466 150 152 194 model_g2anim "BOTH_WALK1" model_angle 180 model_rotation 100 model_g2mins -32 -32 -26 model_g2maxs 32 32 42 model_fovy 36 isCharacter 1 visible 1 decoration cvarTest "ui_stProfilePreviewAvailable" showCvar { "1" } }']
  for target,name in mapping.items():
   start,end=blocks.block_span(text,'itemDef',name)
   action=re.search(r'\baction\s*\{([^}]+)\}',text[start:end],re.S)
   assert action,(file,name)
   lines.append('itemDef { name '+target+' type ITEM_TYPE_BUTTON rect 0 0 0 0 visible 0 decoration action {'+action[1]+'} }')
  lines.append('} }');(SRC/file).write_text('\n'.join(line.rstrip() for part in lines for line in part.splitlines())+'\n')
 print('Profile surfaces generated with original native customization/team actions.')
if __name__=='__main__':main()
