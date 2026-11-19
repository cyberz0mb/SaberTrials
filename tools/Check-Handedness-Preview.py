"""Native visual proof only: does not load maps or create a local server."""
from pathlib import Path
import argparse,shutil,subprocess,os,json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True)
    p.add_argument('--build-dir',type=Path,default=ROOT/'dist/handedness-preview-build/Release')
    a=p.parse_args()
    run=ROOT/'dist/verification/handedness-20261024'/a.tag
    if run.exists():raise RuntimeError('Evidence directory already exists')
    mod=run/'home/SaberTrials';app=run/'bin';mod.mkdir(parents=True);app.mkdir()
    for name in ('SDL2.dll','OpenAL32.dll'):
        shutil.copy2(ROOT/'client'/name,app/name)
    build=a.build_dir.resolve()
    shutil.copy2(build/'openjk.x86_64.exe',app/'SaberTrials.x86_64.exe')
    shutil.copy2(build/'rd-vanilla_x86_64.dll',app/'rd-vanilla_x86_64.dll')
    shutil.copy2(build/'uix86_64.dll',mod/'uix86_64.dll')
    menu=mod/'ui/jamp/saber.menu';menu.parent.mkdir(parents=True)
    original=(ROOT/'ui/jamp/saber.menu').read_text();end=original.rfind('}')
    menu.write_text(original[:end]+'\n'+(ROOT/'development-source/handedness/ui/handedness.menu').read_text()+'\n'+original[end:])
    # Overhaul regression fixtures only; copyrighted game data stays in ignored
    # local test storage and is never distributed or changed in GameData/base.
    with zipfile.ZipFile(ROOT.parent/'base/assets1.pk3') as z:
        model=z.read('models/players/kyle/model.glm')
        skin=z.read('models/players/kyle/model_default.skin')
        gla=z.read('models/players/_humanoid/_humanoid.gla')
    for fixture in ('st_hand_noanim','st_hand_notag'):
        folder=mod/'models/players'/fixture;folder.mkdir(parents=True)
        data=bytearray(model)
        if fixture=='st_hand_noanim':
            name=b'models/players/st_hand_noanim/pose'
            data[72:136]=name.ljust(64,b'\0');(folder/'pose.gla').write_bytes(gla)
        else:
            assert b'*l_hand\0' in data
            data=data.replace(b'*l_hand\0',b'*x_hand\0')
        (folder/'model.glm').write_bytes(data);(folder/'model_default.skin').write_bytes(skin)
    lines=['wait 100','set model kyle/default']
    for style in ('single','dual','staff'):
        for attack in (0,1):
            for hand in (0,1):
                name=f'{style}-{attack}-{hand}'
                lines+=[f'st_handqa {style} {hand} {attack}','wait 50','st_handqa probe',f'screenshot_png hand-{name}','wait 10']
    lines+=['st_handqa single 0 0','wait 10','st_handqa toggle','wait 30','st_handqa probe','screenshot_png hand-control-left','st_handqa toggle','wait 30','st_handqa probe','screenshot_png hand-control-right']
    for fixture in ('st_hand_noanim','st_hand_notag'):
        lines+=['set model '+fixture+'/default','st_handqa single 1 0','wait 30','st_handqa probe','screenshot_png hand-'+fixture]
    lines+=['set model kyle/default']
    for style in ('single','dual','staff'):
        for pose in (1,2,3):
            for hand in (0,1):
                lines+=[f'st_handqa {style} {hand} 1','wait 10',f'st_handqa pose {pose}',
                        'wait 4',f'st_handqa geometry {pose}','wait 4']
    lines+=['echo ST_HANDEDNESS_PREVIEW_COMPLETE','quit']
    (mod/'hand-preview.cfg').write_text('\n'.join(lines)+'\n')
    args=[str(app/'SaberTrials.x86_64.exe'),'+set','fs_basepath',str(ROOT.parent),'+set','fs_homepath',str(run/'home'),'+set','fs_game','SaberTrials','+set','r_fullscreen','0','+set','r_mode','-1','+set','r_customwidth','1280','+set','r_customheight','800','+set','cl_renderer','rd-vanilla','+set','s_initsound','0','+set','com_maxfps','60','+set','logfile','2','+set','com_introplayed','1','+exec','hand-preview.cfg']
    si=subprocess.STARTUPINFO();si.dwFlags=subprocess.STARTF_USESHOWWINDOW;si.wShowWindow=0
    proc=subprocess.Popen(args,cwd=app,env=os.environ.copy(),startupinfo=si,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Menu-only handedness preview PID',proc.pid,flush=True)
    try:proc.wait(timeout=100)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);raise
    log=(mod/'qconsole.log').read_text(errors='replace')
    shots=list((mod/'screenshots').glob('hand-*.png'))
    assert proc.returncode==0 and 'ST_HANDEDNESS_PREVIEW_COMPLETE' in log and len(shots)==16
    assert 'Server Initialization' not in log
    probes=[line for line in log.splitlines() if 'HAND_QA ready' in line]
    assert len(probes)==16 and 'HAND_QA missing' not in log
    assert 'hand=1 mirror=1' in probes[-4] and 'hand=0 mirror=0' in probes[-3]
    assert 'support=0' in probes[-2], 'Missing animation.cfg incorrectly advertised a mirrored preview'
    assert 'support=0 hilt=0' in probes[-1], 'Missing hand tag left an unattached saber'
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    (run/'evidence.json').write_text(json.dumps({'map_or_server_started':False,
        'checker_sha256':digest(Path(__file__).resolve()),'returncodes':[proc.returncode],
        'logs':{'home/SaberTrials/qconsole.log':digest(mod/'qconsole.log')},
        'files':{str(p.relative_to(run)):digest(p) for p in [*shots,app/'SaberTrials.x86_64.exe',app/'rd-vanilla_x86_64.dll',mod/'uix86_64.dll']}},indent=2)+'\n')
    print('Captured 16 native views; toggle and unsupported-asset checks passed:',run)
if __name__=='__main__':main()
