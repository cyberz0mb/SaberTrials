"""Verify native themed menu routes in a private game profile."""
import argparse,hashlib,json,os,re,shutil,socket,subprocess,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/menu-rollout-01';PACKAGE='zzzzzzzzzz_sabertrials_rollout.pk3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
# These cover the primary routes plus representative dialogs/variant screens.
# The runtime inventory records every loaded definition, including base PK3 menus.
OFFLINE={
 'createserver':'host','advancedcreateserver':'host-advanced','quickgame':'solo','quickgame2':'solo-options','quickbots':'bots',
 'demo':'recordings','rulesMenu':'rules','rulesMenu_games':'rules-games','rulesMenu_force':'rules-force','rulesMenu_weapons':'rules-weapons','rulesMenu_items':'rules-items','rulesMenu_moves':'rules-moves',
 'playerMenu2':'customize','saberMenu':'sabers','st_handedness':'hand','st_stances_main':'stances','st_hybrid_main':'combat-styles',
 'st_main_ranked':'ranked','st_ranked_duel':'ranked-duel','st_ranked_teams':'ranked-teams','st_ranked_servers':'ranked-servers',
 'st_main_tournament':'tournament','st_tournament_ready':'tournament-ready','st_tournament_bracket1':'tournament-bracket','st_tournament_bracket2':'tournament-bracket-2','st_tournament_bracket3':'tournament-bracket-3','st_tournament_bracket4':'tournament-bracket-4','st_tournament_reserves':'tournament-reserves','st_tournament_leave':'tournament-leave','st_tournament_result':'tournament-result',
 'findplayer_popmenu':'find-player','createfavorite_popmenu':'new-favorite','password_popmenu':'password','password_request':'server-password','quitMenu':'quit','error_popmenu':'error','videodriverMenu':'driver','videowarningMenu':'display-warning'}
INGAME={
 'ingame_player2':'live-customize','ingame_saber':'live-sabers','st_stances_game':'live-stances','st_hybrid_game':'live-combat-styles',
 'ingame_about':'server-info','ingame_addbot':'add-bot','ingame_callvote':'call-vote','ingame_vote':'vote','ingame_objectives':'objectives',
 'ingame_orders':'orders','ingame_voicechat':'voice-menu','ingame_leave':'leave','ingame_siegeobjectives':'siege-objectives','ingame_siegeclass':'siege-class','siege_popmenu':'siege-message'}
def local_reply(sock):
 header=b'\xff'*4
 fields={'protocol':'26','hostname':'^3Saber Trials ^7Local Review','mapname':'mp/ffa3','clients':'4','sv_maxclients':'16','gametype':'0','game':'SaberTrials','needpass':'0','wdisable':'0','fdisable':'0','challenge':'xxx'}
 info=('\\'+'\\'.join(x for pair in fields.items() for x in pair)).encode('ascii')
 while True:
  try:packet,addr=sock.recvfrom(2048)
  except OSError:return
  if addr[0]!='127.0.0.1':continue
  if packet.startswith(header+b'getinfo'):reply=header+b'infoResponse\n'+info+b'\n'
  elif packet.startswith(header+b'getstatus'):reply=header+b'statusResponse\n'+info+b'\n0 12 "Local review"\n'
  else:continue
  try:sock.sendto(reply,addr)
  except OSError:return
def main():
 p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--renderer',choices=['rd-vanilla','rd-rend2'],default='rd-vanilla');p.add_argument('--height',type=int,default=720);p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--matrix',action='store_true');p.add_argument('--cleanup',action='store_true');a=p.parse_args()
 assert re.fullmatch(r'[A-Za-z0-9-]+',a.tag)
 global OUT
 if a.cleanup:OUT=ROOT/'dist/menu-cleanup-03'
 qa=not(a.production or a.installed);r=read(OUT/'source-receipt.json');receipt=sha(OUT/'source-receipt.json')
 record=read(OUT/('build-record-qa.json' if qa else 'build-record.json'));variant='build-qa' if qa else 'build'
 dll=(ROOT if a.installed else OUT/variant/'Release')/'uix86_64.dll';pkg=(ROOT if a.installed else OUT)/PACKAGE
 assert record['source_receipt_sha256']==receipt and record['ui_sha256']==sha(dll) and r['package_sha256']==sha(pkg),'Rebuild matching candidate before verification'
 run=OUT/'verification'/a.tag;assert not run.exists();mod=run/'home/SaberTrials';mod.mkdir(parents=True)
 if not a.installed:shutil.copy2(dll,mod/dll.name);shutil.copy2(pkg,mod/pkg.name)
 lines=['wait 70','set st_menuMotion 1','set name "Menu Review"','set model kyle/default','set ui_netSource 6','wait 8'];shots=[]
 def cmd(s):lines.extend(['st_legacyqa '+s,'wait 3'])
 def shot(n):shots.append(n);lines.extend(['wait 7','screenshot_png rollout-'+n,'wait 3'])
 def page(m,n):
  lines.extend(['ui_openmenu '+m,'wait 8'])
  if qa:cmd('assertpaint '+m)
  shot(n)
 if qa:
  fixture=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);fixture.bind(('127.0.0.1',0));port=fixture.getsockname()[1]
  cmd('inventory offline');cmd('connected 0')
  lines+=['ui_openmenu main','wait 6','st_mainqa click play','wait 8'];cmd('assertpaint multiplayermenu');shot('play')
  if a.cleanup:
   cmd('hover tournament');shot('play-tournament-hover');cmd('click tournament');cmd('assertpaint st_main_tournament')
   lines.extend(['ui_openmenu multiplayermenu','wait 8'])
  cmd('click joinserver_button');cmd('assertpaint joinserver');shot('browser-empty');cmd(f'fixtures {port}');lines+=[f'ping 127.0.0.1:{port}','wait 45'];cmd('assertinfo');shot('browser');cmd('thumb');cmd('drag');cmd('release');cmd('assertscrolled');shot('browser-scrolled');cmd('click serverinfoText');cmd('assertpaint serverinfo_popmenu');shot('browser-info');cmd('escape');cmd('assertmenu joinserver');cmd('escape');cmd('assertmenu multiplayermenu')
  cmd('click startserver_button');cmd('assertpaint createserver');shot('host-route');cmd('escape');cmd('assertmenu multiplayermenu')
  if a.cleanup:
   cmd('click rules_button');cmd('assertpaint rulesMenu');shot('rules-overview');cmd('click gamesmenubutton');cmd('assertpaint rulesMenu_games')
   cmd('click tournamentmenubutton');cmd('asserttournament');shot('rules-tournament')
   cmd('asserttournament scroll');shot('rules-tournament-scrolled')
   cmd('click ffamenubutton');shot('rules-ffa-restored')
  if a.matrix:
   for m,n in OFFLINE.items():page(m,n)
   if a.cleanup:
    for menu,item,capture in (('saberMenu','typebut_dual','sabers-hover'),
                               ('quitMenu','quitgame_cancel','quit-hover'),
                               ('demo','back','recordings-hover')):
     lines.extend(['ui_openmenu '+menu,'wait 8']);cmd('hover '+item);shot(capture)
    lines.extend(['ui_openmenu saberMenu','wait 8']);cmd('click st_stances_options')
    cmd('assertpaint st_stances_main');cmd('hover reset');shot('stances-hover')
   page('Connect','connection')
   lines+=['ui_openmenu main','wait 6','st_mainqa click account_link','wait 8'];cmd('assertpaint st_main_account');shot('account');cmd('click back')
   lines+=['ui_openmenu main','wait 6','st_mainqa click exit','wait 8'];cmd('assertpaint st_main_exit');shot('exit');cmd('click back')
  else:
   for m,n in (('demo','recordings'),('saberMenu','sabers'),('st_main_tournament','tournament'),('password_popmenu','password')):page(m,n)
 else:
  for m,n in (('multiplayermenu','play'),('joinserver','browser'),('createserver','host'),('demo','recordings'),('saberMenu','sabers')):page(m,n)
 lines+=['set g_gametype 0','set sv_maxclients 1','set g_warmup 0','devmap mp/ffa3','wait 160','team spectator','wait 45'];
 if qa:
  cmd('inventory ingame');cmd('connected 1');cmd('pause');cmd('assertpaint ingame');shot('pause');cmd('click join');cmd('assertpaint ingame_join');shot('join');cmd('escape');cmd('pause');cmd('assertmenu ingame')
  cmd('click player');cmd('assertmenu ingame_player');lines+=['st_profileqa click 511','wait 9'];cmd('assertpaint ingame_playerforce');shot('force');cmd('force-rank');shot('force-staged');cmd('escape')
  cmd('pause');cmd('click exit');cmd('assertpaint st_pause_exit');shot('pause-exit');cmd('click back');cmd('assertmenu ingame')
  for m,n in (('st_pause_about','pause-about'),('st_pause_tools','pause-tools'),('st_pause_vote','pause-vote'),('st_pause_respawn','respawn'),('st_pause_disconnect','disconnect'),('st_pause_quit','pause-quit'),('st_pause_account','pause-account'),('st_photo','photo')):page(m,n)
  if a.matrix:
   for m,n in INGAME.items():page(m,n)
 else:
  for m,n in (('ingame','pause'),('ingame_playerforce','force'),('ingame_join','join'),('ingame_saber','live-sabers'),('st_photo','photo')):page(m,n)
 for m,n in (('ingame_controls','rich-controls'),('ingame_setup','rich-setup'),('ingame_player','rich-profile')):
  lines.extend(['ui_openmenu '+m,'wait 8']);shot(n)
 lines+=['wait 18','echo ST_ROLLOUT_COMPLETE','quit'];(mod/'rollout.cfg').write_text('\n'.join(lines)+'\n')
 command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+safe','+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','com_unpackLibraries','0','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer',a.renderer,'+set','com_maxfps','60','+set','s_initsound','0','+set','logfile','2','+set','com_introplayed','1','+exec','rollout.cfg']
 si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0;env=os.environ.copy();env['LOCALAPPDATA']=str(run/'local-app-data')
 if qa:threading.Thread(target=local_reply,args=(fixture,),daemon=True).start()
 proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print('Checking native menus:',a.tag,proc.pid,flush=True)
 try:proc.wait(timeout=160)
 except subprocess.TimeoutExpired:proc.terminate();proc.wait();raise
 finally:
  if qa:fixture.close()
 logpath=mod/'qconsole.log';log=logpath.read_text(errors='replace');errors=[s for s in log.splitlines() if any(x in s for x in ('ST_LEGACY_FAIL','ST_PROFILE_FAIL','Unknown command "st_','ERROR: Could not'))]
 assert proc.returncode==0 and 'ST_ROLLOUT_COMPLETE' in log and not errors,errors or log[-3000:]
 assert 'Server Initialization' in log and 'mp/ffa3' in log,'Private map did not load'
 assert all((mod/('screenshots/rollout-'+n+'.png')).is_file() for n in shots),'Missing completed screenshot'
 inventories={}
 if qa:
  plain=re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ', '',log,flags=re.M)
  for phase,block in re.findall(r'ST_LEGACY_INVENTORY (offline|ingame)\n((?:ST_LEGACY_MENU [^\n]+\n)+)',plain):inventories[phase]=re.findall(r'ST_LEGACY_MENU (\S+) \d+',block)
  assert len(inventories.get('offline',[]))>=35 and len(inventories.get('ingame',[]))>=20,inventories
 assert sha(OUT/'source-receipt.json')==receipt
 result={'passed':True,'qa':qa,'installed':a.installed,'renderer':a.renderer,'height':a.height,'matrix':a.matrix,'source_receipt_sha256':receipt,'checker_sha256':sha(Path(__file__)),'ui_sha256':sha(dll),'package_sha256':sha(pkg),'log_sha256':sha(logpath),'screenshots':shots,'inventory':inventories}
 (run/'result.json').write_text(json.dumps(result,indent=2));print('Passed',a.tag,len(shots),'screenshots',flush=True)
if __name__=='__main__':main()
