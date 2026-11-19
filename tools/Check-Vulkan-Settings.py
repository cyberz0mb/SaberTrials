"""Exercise the existing Renderer row's click/apply/keep path using the UI's established QA hooks."""
from importlib import import_module
import shutil
import subprocess

c=import_module('Check-Vulkan');b=c.b

def run():
    flags=('BuildMPEngine','BuildMPDed','BuildMPGame','BuildMPCGame','BuildMPUI',
        'BuildMPRdVanilla','BuildMPRend2','BuildSPEngine','BuildSPGame','BuildSPRdVanilla')
    build=b.OUT/'build-ui-settings-qa'
    with (b.OUT/'build-ui-settings-qa.log').open('w') as log:
        subprocess.run(['cmake','-S',str(b.OUT/'frontend'),'-B',str(build),'-G','Visual Studio 18 2026','-A','x64',
            '-DST_DEPS='+str(b.ROOT/'dist/handedness-baseline-06/deps'),'-DCMAKE_CXX_FLAGS=/DST_CONTROLS_QA',
            *[f'-D{f}={"ON" if f=="BuildMPUI" else "OFF"}' for f in flags]],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(build),'--config','Release','--target','uix86_64','--parallel','5'],
            stdout=log,stderr=subprocess.STDOUT,check=True)
    folder,mod=c.stage('settings-qa')
    shutil.copyfile(build/'Release/uix86_64.dll',mod/'uix86_64.dll')
    lines=['wait 100','ui_openmenu setup_menu','wait 30','st_setupqa click 2200','wait 5',
        'st_setupqa click 2200','wait 15','screenshot_png renderer-vulkan-selected','wait 20',
        'st_setupqa assertvar cl_renderer rd-vanilla','st_setupqa click 2902','st_setupqa continue settings-step1.cfg']
    (mod/'settings-step1.cfg').write_text('\n'.join(['wait 100','st_setupqa assertvar cl_renderer rd-vulkan',
        'st_setupqa assertvar st_activeRenderer rd-vulkan','screenshot_png renderer-confirm','wait 20',
        'st_setupqa click 3201','wait 20','screenshot_png renderer-kept','wait 20','echo ST_VULKAN_SETTINGS_DONE','quit'])+'\n')
    process=c.launch(folder,mod,'rd-vanilla',lines)
    try:assert process.wait(timeout=90)==0
    finally:
        if process.poll() is None:process.kill();process.wait()
    log=(mod/'qconsole.log').read_text(errors='replace')
    assert 'ST_VULKAN_SETTINGS_DONE' in log and 'ST_SETUP_FAIL' not in log
    assert 'Unknown command "st_setupqa' not in log and 'Saved graphics settings retained.' not in log
    assert not (mod/'_st_setup_display_recovery.cfg').exists()
    b.write(b.OUT/'settings-check.json',dict(passed=True,source=b.sha(b.OUT/'source-receipt.json'),
        folder=str(folder),ui_qa=b.sha(mod/'uix86_64.dll'),log=b.sha(mod/'qconsole.log'),
        screenshots={p.name:b.sha(p) for p in (mod/'screenshots').glob('*.png')}))
    print('Passed Vulkan settings click/apply/keep: '+str(folder),flush=True)

if __name__=='__main__':run()
