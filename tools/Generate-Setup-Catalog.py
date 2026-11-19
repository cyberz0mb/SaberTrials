"""Build Setup metadata from the pinned owner sources; no live settings are read."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/controls-candidate-01'
rows=[]
def add(tab,group,name,label,kind=0,low=0,high=1,choices='',help='',dep=0,restart=0):
 rows.append(dict(tab=tab,group=group,name=name,label=label,kind=kind,low=low,high=high,choices=choices,help=help,dep=dep,restart=restart))
def toggle(tab,group,name,label,help='',dep=0):add(tab,group,name,label,1,choices='0=Off|1=On',help=help,dep=dep)
add(0,'Display','cl_renderer','Renderer',2,choices='rd-vanilla=Vanilla|rd-rend2=Rend2',help='Restarts the renderer.',restart=1)
add(0,'Display','r_mode','Resolution',2,choices='-2=Desktop|-1=Custom|4=800 x 600|6=1024 x 768|10=1600 x 1200',help='Available display modes are added automatically.',restart=1)
add(0,'Display','r_customwidth','Custom width',0,320,16384,help='Used for Custom resolution.',dep=5,restart=1)
add(0,'Display','r_customheight','Custom height',0,200,16384,dep=5,restart=1)
toggle(0,'Display','r_fullscreen','Fullscreen')
add(0,'Display','r_gamma','Brightness',3,.5,3)
add(0,'Display','r_swapInterval','V-Sync',2,choices='0=Off|1=On|-1=Adaptive')
for name,label,opts in [('r_colorbits','Color depth','0=Desktop|16=16 bit|32=32 bit'),('r_lodbias','Geometry detail','2=Low|1=Medium|0=High'),('r_picmip','Texture detail','3=Low|2=Medium|1=High|0=Very high'),('r_texturebits','Texture depth','0=Default|16=16 bit|32=32 bit'),('r_texturemode','Texture filter','GL_LINEAR_MIPMAP_NEAREST=Bilinear|GL_LINEAR_MIPMAP_LINEAR=Trilinear'),('r_ext_multisample','Antialiasing','0=Off|2=2x|4=4x|8=8x'),('r_ext_texture_filter_anisotropic','Anisotropic filtering','0=Off|2=2x|4=4x|8=8x|16=16x')]:add(0,'Quality',name,label,2,choices=opts)
toggle(0,'Quality','r_detailtextures','Detailed shaders')
toggle(0,'Quality','r_ext_compress_textures','Texture compression')
add(0,'Quality','r_subdivisions','Curve subdivisions',3,4,80,help='Lower values make curved surfaces smoother.')
for name,label in [('r_dynamiclight','Dynamic lights'),('r_dynamicglow','Dynamic glow'),('r_flares','Light flares'),('cg_marks','Wall marks')]:toggle(0,'Effects',name,label)
add(0,'Lighting','r_intensity','Texture intensity',3,1,4)
toggle(0,'Lighting','r_vertexLight','Vertex lighting')
for name,label in [('r_hdr','HDR'),('r_tonemap','Tonemapping'),('r_autoexposure','Autoexposure'),('r_floatLightmap','HDR lightmaps'),('r_deluxemapping','Deluxe mapping'),('r_cubemapping','Cubemapping'),('r_parallaxmapping','Parallax mapping'),('r_genNormalMaps','Generate normal maps'),('r_ssao','SSAO')]:toggle(0,'Advanced video',name,label,dep=1)
add(0,'Advanced video','r_deluxeSpecular','Deluxe specular',3,0,10,dep=1)
add(0,'Advanced video','r_cubemappingBounces','Cubemap bounces',0,0,4,dep=1)
for name,label in [('s_volume','Effects volume'),('s_musicvolume','Music volume'),('s_volumeVoice','Voice volume')]:add(1,'Volume',name,label,3,0,1)
add(1,'Playback','s_khz','Sound quality',2,choices='22=22 kHz|44=44 kHz',restart=2)
toggle(1,'Playback','s_UseOpenAL','OpenAL')
add(1,'Playback','s_language','Voice language',2,choices='english=English|francais=French|deutsch=German|espanol=Spanish',restart=2)
for name,label in [('cg_chatBeep','Chat sound'),('cg_teamChatBeep','Team chat sound'),('cg_jumpSounds','Jump sounds')]:
 toggle(1,'Game sounds',name,label)
add(2,'Chat','st_chatSize','Chat box size (%)',3,75,125,help='Scales the panel and text together.')
add(2,'Chat','st_chatWidth','Chat box width (%)',3,24,68,help='Adjusts the width across the screen.')
add(2,'Chat','st_chatHeight','Chat box height (%)',3,12,36,help='Adjusts how many chat lines fit.')
add(2,'Chat','st_chatOpacity','Chat box opacity (%)',3,0,100,help='Changes the chat background. Text stays readable.')
languages=json.loads((ROOT/'development-source/translator/languages.json').read_text())
languageChoices='|'.join(str(language['id'])+'='+language['name'] for language in languages)
toggle(2,'Translation','st_translate','Universal translator','Translate received public, team and private chat offline.')
add(2,'Translation','st_translateTarget','Translate into',2,choices=languageChoices,help='Your preferred reading language. Requires the matching offline packs.')
add(2,'Translation','st_translateSource','Message language',2,choices='0=Automatic|'+languageChoices,help='Choose a language if short messages or regional variants are misidentified.')
toggle(2,'Translation','st_translateOriginal','Show original message','Show the original above its marked translation. Originals remain in the console.')
add(2,'HUD','st_hudStyle','HUD style',2,choices='0=Original JKA|1=Saber Trials')
add(2,'HUD','st_hudScale','HUD size (%)',3,75,125)
add(2,'HUD','st_hudOpacity','Panel opacity (%)',3,0,100)
toggle(2,'HUD','cg_drawScores','Show score')
toggle(2,'HUD','st_hudPulse','Low health pulse')
toggle(2,'HUD','cg_drawRadar','Radar')
toggle(2,'HUD','cg_drawStatus','Health and ammo')
toggle(2,'HUD','cg_drawTimer','Match timer')
add(2,'Portraits','st_portraitMode','Portrait',2,choices='0=Off|1=Live|2=Static')
add(2,'Portraits','st_portraitTarget','Subject',2,choices='0=Leader|1=Your character|2=Opponent')
add(2,'Portraits','st_portraitSize','Portrait size',3,48,144)
toggle(2,'Portraits','st_portraitDamage','Damage reactions')
add(2,'Crosshair and interface','cg_drawCrosshair','Crosshair',0,0,9)
toggle(2,'Crosshair and interface','cg_drawCrosshairNames','Target names')
toggle(2,'Crosshair and interface','cg_dynamicCrosshair','Dynamic crosshair')
toggle(2,'Crosshair and interface','cg_dynamicCrosshairPrecision','Precise crosshair trace')
toggle(2,'Crosshair and interface','cg_drawVehLeadIndicator','Vehicle lead indicator')
add(2,'Crosshair and interface','cg_drawTeamOverlay','Team overlay',2,choices='0=Off|1=Top right|2=Bottom right|3=Bottom left')
toggle(2,'Crosshair and interface','st_notifications','Status notifications')
toggle(2,'Console','st_consoleOverlay','Console overlay')
add(2,'Console','con_opacity','Console opacity',3,0,1)
for name,label in [('cg_forceModel','Force player models'),('cg_deferPlayers','Defer player models'),('cg_simpleItems','Simple items')]:toggle(3,'Players and world',name,label)
toggle(3,'Team appearance','cg_teamColorSkins','Team color skins','Use team skins when available. Off shows chosen outfits.')
toggle(3,'Team appearance','cg_teamColorSabers','Team color lightsabers','Use team blade colors. Off shows chosen colors.')
add(3,'Visual effects','cg_shadows','Character shadows',2,choices='0=Off|1=Blob|2=Stencil|3=Projected')
add(3,'Visual effects','cg_saberTrail','Saber trail',2,choices='0=Off|1=Standard|2=Stencil')
add(3,'Visual effects','cg_dismember','Dismemberment',2,choices='0=Off|1=Limbs only|2=On',help='Controls what you see when the server allows dismemberment.')
toggle(3,'Visual effects','cg_speedTrail','Speed trail')
add(3,'Visual effects','cg_noProjectileTrail','Projectile trails',4,choices='1=Off|0=On')
toggle(3,'Communication','cg_teamChatsOnly','Team chat only')
add(3,'Communication','se_language','Text language',2,choices='english=English|french=French|german=German|spanish=Spanish')
add(3,'Movement effects','cg_footsteps','Footsteps',2,choices='0=Off|1=Sounds|2=Sounds + effects|3=Sounds + effects + marks')
for name,label in [('cg_bobup','Vertical sway'),('cg_bobpitch','Pitch sway'),('cg_bobroll','Roll sway'),('cg_runpitch','Run pitch'),('cg_runroll','Run roll')]:add(3,'Movement effects',name,label,0,0,1,help='Zero disables this component of view swaying.')
for name,label,lo,hi,help in [('rate','Rate',1000,1000000,'Requested bytes per second; server limits apply.'),('snaps','Snapshots',1,125,'Requested snapshots per second.'),('cl_maxpackets','Max packets',15,125,'Client command packets per second.'),('cl_packetdup','Packet duplication',0,5,'Repeat commands in outgoing packets.'),('cl_timeNudge','Time Nudge',-30,30,'Snapshot timing offset; normally session-only.'),('com_maxfps','FPS limit',0,1000,'Zero removes the client frame-rate limit.')]:add(4,'Connection' if name in ('rate','snaps','cl_maxpackets','cl_packetdup') else 'Timing and downloads',name,label,0,lo,hi,help=help)
toggle(4,'Timing and downloads','cg_drawFPS','FPS counter')
toggle(4,'Timing and downloads','cg_lagometer','Lagometer')
toggle(4,'Timing and downloads','cl_allowDownload','Allow downloads')
add(5,'Capture','cg_draw2D','Clean Capture',4,choices='1=Off|0=On',help='Hide HUD, radar, chat and spectator overlays.')
toggle(5,'Streamer presentation','st_streamerMode','Streamer mode',dep=2)
for name,label in [('st_streamerCleanHud','Replace ordinary HUD'),('st_streamerOverlay','Names / scores'),('st_streamerKillFeed','Kill feed'),('st_streamerPlayerNames','Player labels'),('st_streamerTeamOverlay','Team overlay'),('st_streamerLetterbox','Letterbox')]:toggle(5,'Streamer presentation',name,label,dep=3)
add(5,'Streamer presentation','st_streamerMatchClock','Match clock',2,choices='0=Off|1=Count up|2=Time remaining',dep=3)
toggle(5,'Spectator camera','st_streamerCameraSmooth','Smooth follow')
add(5,'Spectator camera','st_streamerFov','Camera FOV',0,40,140)
add(5,'Spectator camera','st_streamerCameraSpeed','Freecam speed',0,50,2000)
toggle(6,'Third-person framing','cg_thirdPerson','Third person','Some weapons and modes choose the view automatically.')
for name,label,lo,hi,help in [
 ('cg_thirdPersonRange','Distance',20,1000,'Distance behind the player. Walls can bring the camera closer.'),
 ('cg_thirdPersonAngle','Orbit angle',-180,180,'Turn the camera around the player.'),
 ('cg_thirdPersonPitchOffset','Pitch',-75,75,'Tilt the camera up or down.'),
 ('cg_thirdPersonVertOffset','Height',-64,160,'Raise or lower the camera target.'),
 ('st_cameraShoulder','Shoulder offset',-64,64,'Negative shifts left. Positive shifts right. Zero centers the view.'),
 ('cg_thirdPersonCameraDamp','Camera damping',0,1,'Smooths changes to camera position.'),
 ('cg_thirdPersonTargetDamp','Target damping',0,1,'Smooths changes to the point the camera follows.'),
]:add(6,'Third-person framing' if 'Damp' not in name else 'Camera smoothing',name,label,3,lo,hi,help=help)
add(6,'Perspective','cg_fov','Field of view',3,60,140)
add(6,'Perspective','cg_fovViewmodel','Weapon FOV',3,0,140,help='Zero uses your field of view.')
toggle(6,'Perspective','cg_drawGun','Show weapon','Shows the weapon model in first person.')

def main():
 sources={};owners={}
 paths=[BASE/'frontend/codemp/cgame',BASE/'engine/codemp',BASE/'engine/shared',BASE/'frontend/codemp/ui']
 for folder in paths:
  for p in folder.rglob('*'):
   if p.suffix not in ('.h','.c','.cpp'):continue
   text=p.read_text(errors='replace').replace('DEFAULT_RENDER_LIBRARY','"rd-vanilla"').replace('DEFAULT_LANGUAGE','"english"');rel=str(p.relative_to(BASE))
   patterns=[r'Cvar_Get\s*\(\s*"([^"\n]+)"\s*,\s*"([^"\n]*)"\s*,\s*([^,;)]+)',r'XCVAR_DEF\(\s*(\w+)\s*,\s*"([^"\n]*)"\s*,\s*[^,]+,\s*([^\)]+)',r'Cvar_Register\s*\(\s*[^,]+,\s*"([^"\n]+)"\s*,\s*"([^"\n]*)"\s*,\s*([^,;)]+)']
   for pat in patterns:
    for m in re.finditer(pat,text):
     n,v,flags=m.groups();key=n.lower()
     if key not in owners:owners[key]=(v,flags.strip(),rel,text[:m.start()].count('\n')+1)
 for r in rows:
  owner=owners.get(r['name'].lower())
  if r['name'].startswith('st_translate'):
   path=ROOT/'development-source/translator/cl_st_translation.inc'
   text=path.read_text();match=re.search(r'Cvar_Get\("'+r['name']+r'","([^"]*)",([^\)]+)',text)
   owner=(match[1],match[2].strip(),path.relative_to(ROOT).as_posix(),text[:match.start()].count('\n')+1)
  if r['name'] in ('cg_drawRadar','cg_thirdPersonCameraDamp','st_cameraShoulder','cg_teamColorSkins','cg_teamColorSabers','st_chatSize','st_chatWidth','st_chatHeight','st_chatOpacity'):
   path=ROOT/'development-source/client-game/codemp/cgame/cg_xcvar.h'
   text=path.read_text()
   match=re.search(r'XCVAR_DEF\(\s*'+r['name']+r'\s*,\s*"([^"]*)"\s*,\s*[^,]+,\s*([^\)]+)',text)
   owner=(match[1],match[2].strip(),path.relative_to(ROOT).as_posix(),text[:match.start()].count('\n')+1)
  if not owner:raise RuntimeError('No owner for '+r['name'])
  r['default'],r['flags'],r['source'],r['line']=owner
  r['flags']=r['flags'].replace('SWAPINTERVAL_FLAGS','CVAR_ARCHIVE')
  if r['kind']==0 and r['name'].lower() in ('r_customwidth','r_customheight','r_cubemappingbounces','cg_drawcrosshair','rate','snaps','cl_maxpackets','cl_packetdup','cl_timenudge','com_maxfps'):r['kind']=5
  if r['name'].lower() in ('s_useopenal',):r['restart']=2
  if r['tab']==0:r['restart']=int(r['name'].lower()=='cl_renderer' or 'CVAR_LATCH' in r['flags'])
 names=[r['name'].lower() for r in rows];assert len(names)==len(set(names))
 dest=ROOT/'development-source/setup';dest.mkdir(exist_ok=True)
 (dest/'catalog.json').write_text(json.dumps(rows,indent=2))
 def q(x):return json.dumps(x)
 out=['// Generated by tools/Generate-Setup-Catalog.py from pinned owner sources.','#ifndef ST_SETUP_CATALOG_H','#define ST_SETUP_CATALOG_H','struct ssSetting_t{const char *name,*label,*group,*help,*choices,*fallback;int tab,kind,restart,dependency,flags;double low,high;};','static const ssSetting_t ssSettings[]={']
 for r in rows:out.append(' {'+','.join([q(r[k]) for k in ('name','label','group','help','choices','default')]+[str(r[k]) for k in ('tab','kind','restart','dep')]+[r['flags'],str(r['low']),str(r['high'])])+'},')
 out+=['};','static const int SS_COUNT=sizeof(ssSettings)/sizeof(ssSettings[0]);','#endif']
 (dest/'st_setup_catalog.h').write_text('\n'.join(out)+'\n')
 tabnames=['Video','Sound','Interface','Game Options','Network','Recording','Camera']
 lines=['# Setup settings inventory','', 'Pinned baseline: current Controls candidate; defaults and flags below come from the owning engine/cgame source, not the browser preview.','', '| Tab | Setting | Variable | Default | Owner |','|---|---|---|---|---|']
 for r in rows:lines.append(f"| {tabnames[r['tab']]} | {r['label']} | `{r['name']}` | `{r['default']}` | `{r['source']}:{r['line']}` |")
 lines+=['','## Moved/adapted utilities','','- UI proxy fields (`ui_r_*`, `st_uiHud*`, `st_uiPortraitSize`) bind to actual renderer/HUD/portrait variables above. Status proxies are not settings.','- Old Input controls remain solely in Controls; console appearance moves to Interface.','- View swaying is preserved as its five existing component variables rather than the transient `ui_disableWeaponSway` script field.','- Existing quality preset, driver info, installed Mods discovery and spectator Free Camera/Previous/Next actions remain utilities.','- Defaults becomes a confirmed, staged reset of this tab only.','- Saved Configs has one manager in Setup; Controls links to it.','- EAX is unavailable in this OpenJK menu baseline (legacy UI disables it); retain supported OpenAL backend and quality choices.','- Language selectors preserve the current value; packaged language choices will be enumerated from existing localization metadata.']
 (ROOT/'docs/Setup-Settings-Inventory.md').write_text('\n'.join(lines)+'\n')
 print(f'Generated {len(rows)} settings with source ownership; no duplicate cvars.')
if __name__=='__main__':main()
