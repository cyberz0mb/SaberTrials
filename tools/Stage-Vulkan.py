"""Stage and verify a private Vulkan test client; never install over the regular game."""
import argparse
from importlib import import_module
from pathlib import Path
import os
import re
import shutil
import subprocess

b=import_module('Build-Vulkan')
PLAY=b.OUT/'playable'

def evidence():
    source=b.sha(b.OUT/'source-receipt.json')
    assert b.tree(b.SOURCE)==b.read(b.OUT/'source-receipt.json')['authored'],'Authored source changed'
    chosen={}
    for p in sorted((b.OUT/'checks').glob('*/result.json')):
        r=b.read(p)
        if not r.get('passed') or r.get('source')!=source:continue
        if r.get('scenario')=='dedicated-loopback':key='dedicated-loopback'
        else:key=r['renderer']+'/'+r['scenario']
        valid=True
        for role,(_,_,name,ext) in b.ROLES.items():
            receipt=b.read(b.OUT/f'build-{role}.json')
            assert receipt['source']==source and receipt['sha256']==b.sha(b.OUT/f'build-{role}/Release'/(name+ext))
            logical={'engine':'bin/SaberTrials.x86_64.exe','vulkan':'bin/rd-vulkan_x86_64.dll','ui':'home/SaberTrials/uix86_64.dll'}[role]
            valid &= r['inputs'].get(logical)==receipt['sha256']
        if valid:chosen[key]={'path':str(p),'sha256':b.sha(p)}
    required={r+'/'+s for r,s in import_module('Check-Vulkan-Suite').CASES}|{'dedicated-loopback','rd-vulkan/materials'}
    assert required<=chosen.keys(),'Missing matching checks: '+str(sorted(required-chosen.keys()))
    return chosen

def files():
    result={'client/SaberTrials.x86_64.exe':b.OUT/'build-engine/Release/openjk.x86_64.exe',
        'client/rd-vulkan_x86_64.dll':b.OUT/'build-vulkan/Release/rd-vulkan_x86_64.dll',
        'home/SaberTrials/uix86_64.dll':b.OUT/'build-ui/Release/uix86_64.dll'}
    for name in ('SDL2.dll','OpenAL32.dll','rd-vanilla_x86_64.dll','rd-rend2_x86_64.dll'):
        result['client/'+name]=b.ROOT/'client'/name
    for name in ('cgamex86_64.dll','jampgamex86_64.dll'):result['home/SaberTrials/'+name]=b.ROOT/name
    return result

def verify():
    record=b.read(PLAY/'stage-receipt.json')
    assert record['source']==b.sha(b.OUT/'source-receipt.json'),'Candidate source changed'
    for name,digest in record['files'].items():assert b.sha(PLAY/name)==digest,'Candidate changed: '+name
    for item in record['checks'].values():assert b.sha(item['path'])==item['sha256'],'Check receipt changed'
    return record

def stage():
    checks=evidence()
    settings=b.read(b.OUT/'settings-check.json')
    assert settings['passed'] and settings['source']==b.sha(b.OUT/'source-receipt.json')
    checks['settings']={'path':str(b.OUT/'settings-check.json'),'sha256':b.sha(b.OUT/'settings-check.json')}
    PLAY.mkdir(parents=True,exist_ok=True)
    helper=import_module('Install-Profile-Browser')
    home,original=helper.settings()
    for name,path in files().items():
        target=PLAY/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    copied={}
    for source in home.glob('*.cfg'):
        target=PLAY/'home/SaberTrials'/source.name
        if not target.exists():shutil.copyfile(source,target);copied[source.name]=b.sha(source)
    # Copy the offline translator runtime as well as fonts, preserving current client features.
    # Model weights/fonts are immutable shared data; hard links avoid another multi-GB copy.
    def copy(source,target):
        if Path(target).exists():
            if b.sha(source)==b.sha(target):return target
            # Replace only a staged file, never write through an existing hard link.
            Path(target).unlink()
        if any(part in ('models','fonts') for part in Path(source).parts):
            try:os.link(source,target);return target
            except OSError:pass
        return shutil.copy2(source,target)
    shutil.copytree(b.ROOT/'client/translator',PLAY/'client/translator',dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('__pycache__'),copy_function=copy)
    licenses=PLAY/'licenses';licenses.mkdir(exist_ok=True)
    shutil.copyfile(b.UPSTREAM/'LICENSE.txt',licenses/'OpenJK-GPL-2.0.txt')
    shutil.copyfile(b.UPSTREAM/'codemp/rd-vulkan/README.md',licenses/'Vulkan-upstream-credits.md')
    shutil.copyfile(b.UPSTREAM/'codemp/rd-vulkan/utils/stb_dxt.h',licenses/'stb_dxt-source-and-BSD-license.h')
    shutil.copyfile(b.ROOT/'docs/licenses/Khronos-Vulkan-MIT.txt',licenses/'Khronos-Vulkan-MIT.txt')
    shutil.copyfile(b.ROOT/'docs/Vulkan-Renderer.md',PLAY/'README.md')
    shutil.copyfile(b.ROOT/'docs/Vulkan-Validation.md',PLAY/'VALIDATION.md')
    shutil.copyfile(b.ROOT/'docs/Vulkan-Material-Compatibility.md',PLAY/'Vulkan-Material-Compatibility.md')
    assert original==helper.settings()[1],'Original settings changed during staging'
    b.write(PLAY/'stage-receipt.json',dict(source=b.sha(b.OUT/'source-receipt.json'),checks=checks,
        files={name:b.sha(PLAY/name) for name in files()},copied_profile=copied,original_settings=original,
        installed=False,dlss=False))
    verify()
    print('Staged isolated Vulkan candidate: '+str(PLAY),flush=True)

def launch(extra=None,startupinfo=None):
    verify()
    configuration=PLAY/'home/SaberTrials/openjk.cfg'
    saved=configuration.read_text(errors='replace') if configuration.exists() else ''
    match=(re.search(r'seta? cl_renderer "(rd-vanilla|rd-rend2)"',saved)
           or re.search(r'seta? st_lastGoodRenderer "(rd-vanilla|rd-rend2)"',saved))
    fallback=match[1] if match else 'rd-vanilla'
    command=[str(PLAY/'client/SaberTrials.x86_64.exe')]
    for name,value in dict(fs_basepath=b.ROOT.parent,fs_homepath=PLAY/'home',fs_game='SaberTrials',
        com_unpackLibraries=0,cl_renderer='rd-vulkan',st_lastGoodRenderer=fallback,
        r_renderScale=0,r_ext_supersample=0).items():command+=['+set',name,str(value)]
    process=subprocess.Popen(command+(extra or []),cwd=b.ROOT.parent,startupinfo=startupinfo,
        env={**os.environ,'LOCALAPPDATA':str(PLAY/'local-app-data')})
    print('Opened the private Vulkan test client.',flush=True)
    return process

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true');parser.add_argument('--launch',action='store_true')
    args=parser.parse_args()
    if args.launch:launch()
    elif args.verify:verify();print('Vulkan candidate verified.')
    else:stage()
