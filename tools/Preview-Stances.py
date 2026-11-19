"""Open the staged production menu in a separate, persistent visual-preview home."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'dist/stance-candidate-02'
PREVIEW=CANDIDATE/'interactive-preview'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    record=json.loads((CANDIDATE/'sources.json').read_text())
    mapping={}
    for name in ('SaberTrials.x86_64.exe','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll','SDL2.dll','OpenAL32.dll'):
        source=ROOT/'client'/name
        installed=ROOT/'dist/hybrid-install.json'
        if installed.exists():
            state=json.loads(installed.read_text())
            key='client/'+name
            if state.get('installed') and state['before'].get(key):
                source=Path(state['backup'])/key
                if sha(source)!=state['before'][key]:raise RuntimeError('Legacy preview backup changed: '+name)
        mapping['bin/'+name]=source
    for kind,files in record['builds'].items():
        for name,expected in files.items():
            source=CANDIDATE/('build-'+kind)/'Release'/name
            if sha(source)!=expected:raise RuntimeError('Candidate build changed: '+name)
            mapping['home/SaberTrials/'+name]=source
    if len(record['builds'])!=2:raise RuntimeError('Candidate has not completed both builds')
    package=CANDIDATE/'assets/zz_sabertrials_stances_v1.pk3'
    if sha(package)!=record['library_sha256']:raise RuntimeError('Candidate asset mismatch')
    mapping['home/SaberTrials/'+package.name]=package
    for name,expected in record['menus'].items():
        source=CANDIDATE/'menus'/name
        if sha(source)!=expected:raise RuntimeError('Candidate menu changed: '+name)
        mapping['home/SaberTrials/'+name]=source
    for name,source in mapping.items():
        target=PREVIEW/name;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if sha(target)!=sha(source):raise RuntimeError('Existing preview differs; preserve it before updating: '+name)
        else:shutil.copy2(source,target)
    home=PREVIEW/'home';mod=home/'SaberTrials';account=PREVIEW/'local-app-data';account.mkdir(exist_ok=True)
    config=mod/'stance-visual-preview.cfg'
    if not config.exists():
        config.write_text('wait 35\nui_openmenu saberMenu\nwait 35\nscreenshot_png stance-menu-entry\n')
    environment=os.environ.copy();environment['LOCALAPPDATA']=str(account)
    args=[str(PREVIEW/'bin/SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),
          '+set','fs_homepath',str(home),'+set','fs_game','SaberTrials',
          '+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','800',
          '+set','cl_renderer','rd-vanilla','+set','com_maxfps','60','+set','s_initsound','0',
          '+set','com_introplayed','1','+set','logfile','1','+exec','stance-visual-preview.cfg']
    # This is the interactive window the user requested, not a hidden test run.
    process=subprocess.Popen(args,cwd=PREVIEW/'bin',env=environment,
        creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (PREVIEW/'launch.json').write_text(json.dumps({'pid':process.pid,'preview_only':True,
        'normal_install_changed':False,'files':{name:sha(PREVIEW/name) for name in mapping}},indent=2)+'\n')
    print('Opened interactive Saber preview. Select Stances... on the Saber page. PID:',process.pid)

if __name__=='__main__':main()
