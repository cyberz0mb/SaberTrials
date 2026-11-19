"""Native, menu-only visual checks. Never loads a map or starts a server."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'dist/presentation-staging'
WORK=Path(tempfile.gettempdir())/'SaberTrials-presentation-20261023'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--height',type=int,default=1024);p.add_argument('--production',action='store_true');p.add_argument('--installed',action='store_true');p.add_argument('--tag',default='');a=p.parse_args()
    qa=not a.production and not a.installed;kind='qa' if qa else 'installed' if a.installed else 'production'
    run=ROOT/'dist/verification/presentation-20261023'/(kind+'-'+str(a.height)+a.tag)
    assert not run.exists(),run
    mod=run/'home/SaberTrials';mod.mkdir(parents=True)
    targets=json.loads((STAGE/'manifest.json').read_text())
    if not a.installed:
        for name in targets:
            dest=mod/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/name,dest)
        shutil.copy2(WORK/('build-qa' if qa else 'build')/'Release/uix86_64.dll',mod/'uix86_64.dll')
    lines=['wait 100','set name "UI Review"','set model kyle/default','set st_notifications 1']
    def shot(name):lines.extend(['wait 18','screenshot_png ST-'+name,'wait 12'])
    def openmenu(name):lines.extend(['ui_openmenu '+name,'wait 12'])
    def click(menu,item):lines.extend(['st_clientqa move '+menu+' '+item,'st_clientqa click','wait 6'])
    def focus(name):lines.extend(['echo ST_EXPECT_FOCUS '+name,'st_clientqa state'])
    openmenu('main');shot('main')
    openmenu('playerMenu');shot('profile')
    openmenu('controlsMenu');shot('controls')
    openmenu('setup_menu');shot('setup')
    if qa:
        for fixture in ['board','teams','crowded','results']:
            lines+=['st_clientqa presentation '+fixture];shot(fixture)
        lines+=['st_clientqa presentation browser'];openmenu('joinserver');shot('browser')
        click('joinserver','serverlist');lines+=['st_clientqa down'];shot('browser-selection')
        lines+=['st_clientqa presentation none']
    else:openmenu('joinserver');shot('browser-empty')
    openmenu('multiplayermenu')
    if qa:click('multiplayermenu','tournament');focus('st_main_tournament')
    else:openmenu('st_main_tournament')
    shot('tournament-selection')
    if qa:click('st_main_tournament','team5');focus('st_tournament_ready')
    else:lines+=['exec st-tournament-preview-5v5.cfg'];openmenu('st_tournament_ready')
    shot('ready-waiting')
    if qa:
        click('st_tournament_ready','ready');lines+=['ui_stFrontReady'];shot('ready-confirmed')
        click('st_tournament_ready','unready');lines+=['ui_stFrontReady']
        click('st_tournament_ready','bracket');focus('st_tournament_bracket1')
    else:openmenu('st_tournament_bracket1')
    shot('team-bracket')
    openmenu('st_tournament_result');shot('result-preview')
    openmenu('st_tournament_reserves');shot('reserves')
    if qa:
        click('st_tournament_reserves','disconnectpreview');focus('st_tournament_ready');shot('disconnected')
        click('st_tournament_ready','reconnect');lines+=['ui_stFrontReady']
    openmenu('st_tournament_leave');shot('leave')
    lines+=['exec st-tournament-preview-individual.cfg'];openmenu('st_tournament_ready');shot('individual-ready')
    for n in [1,3,4]:openmenu('st_tournament_bracket'+str(n));shot('individual-bracket'+str(n))
    openmenu('setup_menu')
    if qa:
        click('setup_menu','st_interface_settings');focus('st_interface_main');shot('ui-options')
        click('st_interface_main','notifications');lines+=['st_notifications']
        click('st_interface_main','notifications');lines+=['st_notifications']
        click('st_interface_main','hud');focus('st_hud_main')
        lines+=['set st_uiHudScale 100','set st_uiHudOpacity 55'];click('st_hud_main','apply');shot('saved-notice')
        lines+=['set st_uiHudScale 999'];click('st_hud_main','apply');shot('invalid-notice')
        lines+=['st_hudScale','wait 320'];shot('notice-expired')
    lines+=['echo ST_PRESENTATION_COMPLETE','quit']
    chunks=[[]]
    for line in lines:
        chunks[-1].append(line)
        if qa and line=='st_clientqa click':chunks.append([])
    for i,chunk in enumerate(chunks):
        if i+1<len(chunks):chunk.append(f'st_clientqa continue st-presentation-step{i+1}.cfg')
        (mod/f'st-presentation-step{i}.cfg').write_text('\n'.join(chunk)+'\n')
    command=[str(ROOT/'client/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight',str(a.height),'+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','st-presentation-step0.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    env=os.environ.copy();env['PATH']=str(ROOT.parent)+';'+env.get('PATH','')
    proc=subprocess.Popen(command,cwd=ROOT.parent,env=env,startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (run/'process.json').write_text(json.dumps({'pid':proc.pid,'map_loaded':False,'server_started':False}))
    print('Native menu-only review. PID',proc.pid,flush=True)
    try:proc.wait(timeout=150)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert proc.returncode==0 and 'ST_PRESENTATION_COMPLETE' in log
    for bad in ['Server Initialization','SpawnServer','QA item missing','unknown menu keyword',"couldn't load menu"]:assert bad not in log,bad
    if qa:
        checks=re.findall(r'ST_EXPECT_FOCUS (\w+).*?MENU_QA focused=(\w+)',log,re.S)
        assert len(checks)==sum(x.startswith('echo ST_EXPECT_FOCUS') for x in lines) and all(x==y for x,y in checks),checks
        plain=re.sub(r'\^[0-9]','',log)
        for value in ['0','1']:assert f'ui_stFrontReady = "{value}"' in plain and f'st_notifications = "{value}"' in plain
        assert 'st_hudScale = "100"' in plain
    images=list((mod/'screenshots').glob('ST-*.png'));assert len(images)==sum(x.startswith('screenshot_png') for x in lines)
    manifest=WORK/('build-qa' if qa else 'build')/'Release/presentation-build.json'
    (run/'capture.json').write_text(json.dumps({'kind':kind,'map_loaded':False,'server_started':False,'interactive_checks':qa,'exit_code':proc.returncode,'build':json.loads(manifest.read_text()),'menu_files':{n:digest((ROOT if a.installed else STAGE)/n) for n in targets},'images':{str(p.relative_to(ROOT)):digest(p) for p in images}},indent=2)+'\n')
    print('PASS',len(images),'native captures and', 'navigation/state checks' if qa else 'production menu loading',flush=True)
if __name__=='__main__':main()
