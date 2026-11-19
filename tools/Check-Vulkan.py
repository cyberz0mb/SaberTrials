"""Run isolated renderer checks without touching the installed client or saved profile."""
import argparse
from datetime import datetime
from importlib import import_module
import os
import shutil
import subprocess
import time
import re
import ctypes
from ctypes import wintypes

b = import_module('Build-Vulkan')

class MemoryCounters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
        ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
         'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]

def memory_sample(process):
    counters=MemoryCounters();counters.cb=ctypes.sizeof(counters)
    function=ctypes.windll.psapi.GetProcessMemoryInfo
    function.argtypes=(wintypes.HANDLE,ctypes.POINTER(MemoryCounters),wintypes.DWORD)
    if function(wintypes.HANDLE(int(process._handle)),ctypes.byref(counters),counters.cb):
        return {'working_set_mib':round(counters.WorkingSetSize/1048576,2),
                'private_commit_mib':round(counters.PrivateUsage/1048576,2)}
    return {}

def stage(name):
    for role,(_,_,base,ext) in b.ROLES.items():
        receipt=b.read(b.OUT/f'build-{role}.json')
        assert receipt['source']==b.sha(b.OUT/'source-receipt.json'),'Rebuild '+role
        assert receipt['sha256']==b.sha(b.OUT/f'build-{role}/Release'/(base+ext)),'Binary drift: '+role
    run = b.OUT/'checks'/(name+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    binary, mod = run/'bin',run/'home/SaberTrials'
    binary.mkdir(parents=True)
    mod.mkdir(parents=True)
    files = {'bin/SaberTrials.x86_64.exe':b.OUT/'build-engine/Release/openjk.x86_64.exe',
             'bin/rd-vulkan_x86_64.dll':b.OUT/'build-vulkan/Release/rd-vulkan_x86_64.dll',
             'home/SaberTrials/uix86_64.dll':b.OUT/'build-ui/Release/uix86_64.dll',
             'home/SaberTrials/cgamex86_64.dll':b.ROOT/'cgamex86_64.dll',
             'home/SaberTrials/jampgamex86_64.dll':b.ROOT/'jampgamex86_64.dll'}
    for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
        files['bin/'+name]=b.ROOT/'client'/name
    for name,source in files.items():
        shutil.copyfile(source,run/name)
    shutil.copytree(b.ROOT/'client/translator/fonts',binary/'translator/fonts')
    b.write(run/'inputs.json',{name:b.sha(source) for name,source in files.items()})
    return run,mod

def launch(run,mod,renderer,lines,extra=None,environment=None):
    (mod/'vulkan-test.cfg').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    cvars=dict(fs_basepath=b.ROOT.parent,fs_homepath=run/'home',fs_game='SaberTrials',
        com_unpackLibraries=0,logfile=2,net_ip='127.0.0.1',net_port=29731,sv_pure=0,
        s_initsound=0,com_introplayed=1,developer=1,r_fullscreen=0,r_mode=-1,
        r_customwidth=1280,r_customheight=720,cl_renderer=renderer,com_maxfps=125,
        con_notifytime=0,st_translate=0,r_renderScale=0,r_ext_supersample=0)
    cvars.update(extra or {})
    command=[str(run/'bin/SaberTrials.x86_64.exe'),'+safe']
    for key,value in cvars.items():command+=['+set',key,str(value)]
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=0
    return subprocess.Popen(command+['+exec','vulkan-test.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(run/'local-app-data'),**(environment or {})},
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def local(renderer,scenario):
    run,mod=stage(renderer+'-'+scenario)
    extra={}
    environment={}
    if scenario in ('missing','incompatible'):
        # Only the copy made in this newly created check directory is moved.
        (run/'bin/rd-vulkan_x86_64.dll').rename(run/'bin/rd-vulkan_x86_64.absent')
        extra['st_lastGoodRenderer']='rd-rend2'
        if scenario=='incompatible':
            shutil.copyfile(run/'bin/rd-vanilla_x86_64.dll',run/'bin/rd-vulkan_x86_64.dll')
    if scenario=='no-driver':
        environment['VK_DRIVER_FILES']=str(run/'missing-vulkan-driver.json')
        environment['VK_ICD_FILENAMES']=environment['VK_DRIVER_FILES']
        extra['st_lastGoodRenderer']='rd-rend2'
    if scenario in ('missing','no-driver','incompatible'):
        extra.update(r_picmip=1,r_textureMode='GL_LINEAR_MIPMAP_LINEAR',r_gamma=1.1)
    if scenario=='intel':extra['r_device']=-2
    lines=['wait 100','cl_renderer','st_activeRenderer','st_rendererError','gfxinfo',
           'screenshot_png menu','wait 15']
    if scenario in ('scene','custom','profile','intel'):
        lines += ['set g_gametype 0','set g_warmup 0','set fraglimit 0','set model kyle/default',
            'devmap '+('ffa_bespin' if scenario=='custom' else 'mp/ffa3'),'wait 400','team free','wait 130','set cg_thirdPerson 1',
            'st_emoteuiqa resume','wait 10']
        if scenario=='profile':
            lines += ['wait 500','set st_profileFrames 600','set r_vkProfileFrames 600','wait 2400',
                      'st_profileFrames','r_vkProfileFrames','screenshot_png profile']
        else:
            lines += ['addbot desann 3','addbot reborn 3','wait 130','screenshot_png combat',
            '+attack','+forward','wait 125','-forward','-attack','wait 50',
            'screenshot_png effects','st_emote bow','wait 60','screenshot_png pose','wait 60',
            'set cg_chatBox 30000','say "Vulkan: 日本語 한국어 العربية"','wait 60','screenshot_png unicode']
    elif scenario=='restart':
        for selected in ('rd-rend2','rd-vulkan','rd-vanilla','rd-vulkan'):
            lines += ['set cl_renderer '+selected,'vid_restart','wait 100','st_activeRenderer',
                      'screenshot_png restart-'+selected,'wait 15']
    lines+=['wait 20','st_activeRenderer','st_rendererError','gfxinfo','r_picmip','r_textureMode','r_gamma','echo ST_VULKAN_CHECK_DONE','quit']
    started=time.monotonic();process=launch(run,mod,renderer,lines,extra,environment)
    memory=[]
    try:
        while process.poll() is None:
            if time.monotonic()-started>150:raise TimeoutError('Renderer check timed out')
            if scenario=='profile':memory.append(memory_sample(process))
            try:process.wait(timeout=1)
            except subprocess.TimeoutExpired:pass
        code=process.returncode
    finally:
        if process.poll() is None:process.kill();process.wait()
    logfile=mod/'qconsole.log'
    output=logfile.read_text(errors='replace') if logfile.exists() else ''
    result=dict(source=b.sha(b.OUT/'source-receipt.json'),renderer=renderer,checker=b.sha(__file__),passed=False,
        scenario=scenario,exit_code=code,elapsed_seconds=time.monotonic()-started,
        completed='ST_VULKAN_CHECK_DONE' in output,log=b.sha(logfile) if logfile.exists() else None,
        screenshots={p.name:b.sha(p) for p in (mod/'screenshots').glob('*')},inputs=b.read(run/'inputs.json'))
    b.write(run/'result.json',result)
    print(run,flush=True)
    if code or 'ST_VULKAN_CHECK_DONE' not in output or ('ERROR:' in output and scenario!='no-driver'):
        raise RuntimeError('Renderer check failed; inspect '+str(logfile))
    expected='rd-rend2' if scenario in ('missing','no-driver','incompatible') else renderer
    clean=re.sub(r'\^[0-9]','',output)
    if f'Cvar st_activeRenderer = "{expected}"' not in clean:
        raise RuntimeError('The requested renderer was not active: '+str(logfile))
    assert re.findall(r'Cvar st_activeRenderer = "([^"]*)"',clean)[-1]==expected,'Renderer changed during the check'
    if scenario not in ('missing','no-driver','incompatible'):
        assert 'Saved graphics settings retained.' not in output,'Unexpected fallback during gameplay'
    if scenario in ('missing','no-driver','incompatible'):
        if 'Saved graphics settings retained.' not in output or 'Cvar cl_renderer = "rd-vulkan"' not in clean:
            raise RuntimeError('Renderer fallback or saved selection check failed')
        for name,value in (('r_picmip','1'),('r_gamma','1.1'),('r_textureMode','GL_LINEAR_MIPMAP_LINEAR')):
            assert f'Cvar {name} = "{value}"' in clean,'Graphics setting changed: '+name
    if scenario=='restart':
        for name in ('rd-rend2','rd-vanilla','rd-vulkan'):
            assert f'Cvar st_activeRenderer = "{name}"' in clean,'Switch failed: '+name
    if scenario in ('scene','custom','intel'):
        assert 'Unknown bot' not in output and 'desann' in clean.lower() and 'reborn' in clean.lower()
        assert len(result['screenshots'])>=5
    if scenario=='intel':assert 'VK_RENDERER: Integrated Intel' in output
    if scenario=='profile':
        result['client_profile']=re.findall(r'ST_FRAME_PROFILE frames=.*',output)
        result['gpu_profile']=re.findall(r'ST_VULKAN_GPU frames=.*',output)
        result['memory_samples']=memory
        assert result['client_profile'] and (renderer!='rd-vulkan' or result['gpu_profile'])
    result['passed']=True
    b.write(run/'result.json',result)
    print('Completed '+renderer+' '+scenario,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renderer',choices=('rd-vulkan','rd-vanilla','rd-rend2'),default='rd-vulkan')
    parser.add_argument('--scenario',choices=('menu','scene','custom','profile','intel','missing','no-driver','incompatible','restart'),default='menu')
    args=parser.parse_args()
    local(args.renderer,args.scenario)
