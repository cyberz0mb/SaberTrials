"""Exercise stock and additive guns in an isolated, real Windows client/server."""
from datetime import datetime
from importlib import import_module
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
b=import_module('Build-Weapon-DLC')
FAMILIES=[('bryar',4,'blaster_pistol/blaster_pistol'),('blaster',5,'blaster_r/blaster'),
          ('disruptor',6,'disruptor/disruptor'),('bowcaster',7,'bowcaster/bowcaster'),
          ('repeater',8,'heavy_repeater/heavy_repeater'),('demp2',9,'demp2/demp2'),
          ('flechette',10,'golan_arms/golan_arms'),('concussion',15,'concussion/c_rifle'),
          ('rocket',11,'merr_sonn/merr_sonn'),('bryar_old',16,'briar_pistol/briar_pistol')]


def fixtures(mod):
    folder=mod/'ext_data/st_weapons'
    folder.mkdir(parents=True,exist_ok=True)
    for family,base,model in FAMILIES:
        text=f'''weapon {{
version 1
id qa_{family}
name "QA {family.title()} Add-on"
baseWeapon {family}
viewModel models/weapons2/{model}.md3
worldModel models/weapons2/{model}_w.glm
}}
'''
        (folder/f'qa_{family}.weapon').write_text(text)
    custom='''muzzleEffect blaster/muzzle_flash
altMuzzleEffect bowcaster/muzzle_flash
shotEffect bowcaster/shot
altShotEffect blaster/shot
impactEffect bowcaster/explosion
altImpactEffect blaster/wall_impact
fireSound sound/weapons/bowcaster/fire.wav
altFireSound sound/weapons/blaster/fire.wav
'''
    text=(folder/'qa_blaster.weapon').read_text().replace('qa_blaster','qa_blaster_zfx').replace('QA Blaster','QA Custom FX')
    text=text.replace('\n}', '\n'+custom+'}')
    (folder/'qa_blaster_zfx.weapon').write_text(text)


def launch(folder,lines,installed=False):
    mod=folder/'home/SaberTrials'
    mod.mkdir(parents=True,exist_ok=True)
    if not installed:
        for name,path in b.files().items(): shutil.copyfile(path,mod/name)
    (mod/'test.cfg').write_text('\n'.join(lines)+'\n')
    options=dict(fs_basepath=b.ROOT.parent,fs_homepath=folder/'home',fs_game='SaberTrials',com_unpackLibraries=0,
        logfile=2,net_ip='127.0.0.1',net_port=29234,r_fullscreen=0,r_mode=-1,r_customwidth=1280,
        r_customheight=720,cl_renderer='rd-rend2',com_maxfps=60,s_initsound=0,com_introplayed=1)
    command=[str(b.ROOT/'client/SaberTrials.x86_64.exe'),'+safe']
    for name,value in options.items(): command.extend(['+set',name,str(value)])
    startup=subprocess.STARTUPINFO()
    startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow=0
    process=subprocess.Popen(command+['+exec','test.cfg'],cwd=b.ROOT.parent,startupinfo=startup,
        env={**os.environ,'LOCALAPPDATA':str(folder/'local-app-data')},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        assert process.wait(timeout=200)==0
    finally:
        if process.poll() is None: process.kill();process.wait()
    return (mod/'qconsole.log').read_text(errors='replace')


def run(mode):
    folder=b.OUT/f'{mode}-{datetime.now():%H%M%S}'
    mod=folder/'home/SaberTrials'
    mod.mkdir(parents=True)
    if mode not in ('stock','installed'): fixtures(mod)
    print(folder,flush=True)
    lines=['wait 60','set sv_pure 0','set g_weaponDLC 1','set g_gametype 0','set st_weaponsActive 1',
           'set g_weaponDisable 0','set g_warmup 0','set fraglimit 0','set st_mvpPrototype 0',
           'set g_infiniteAmmo 0','set cg_thirdPerson 0',
           ('map' if mode=='cheats_off' else 'devmap')+' mp/ffa3','wait 450',
           'team free','wait 90','ui_openmenu ingame_setup','wait 10','togglemenu','wait 20','god']
    def state(label): lines.extend(['echo ST_CASE_'+label,'st_weaponinfo'])
    if mode in ('stock','installed'):
        lines.extend(['give weapons','give ammo 100','wait 90','weaponclean 5','wait 120','weapnext','wait 120'])
        state('stock_only')
        lines+=['screenshot_png stock-only']
    elif mode=='families':
        # No gun pickup: start with the ordinary spawn inventory and cycle into a rifle add-on.
        lines+=['weaponclean 3','wait 80','weapnext','wait 75','weapnext','wait 75','weapnext','wait 100']
        state('no_pickup')
        lines+=['give weapons']
        for family,base,model in FAMILIES:
            lines+=['give ammo 100',f'weaponclean {base}','wait 220']
            state(family+'_stock')
            lines+=['weapnext','wait 220']
            state(family+'_addon')
            if family in ('bryar','blaster','concussion'):
                lines+=['screenshot_png '+family+'-addon']
            lines+=['+attack','wait 12','-attack','wait 200']
            state(family+'_fired')
            lines+=['weapprev','wait 220']
            state(family+'_back')
            lines+=['weapnext','wait 220','+altattack','wait 45','-altattack','wait 350']
            state(family+'_alt')
        lines+=['give ammo 100','weaponclean 5','wait 55','weapnext','wait 40','weapnext','wait 50']
        state('custom_fx')
        lines+=['+attack','wait 15','screenshot_png custom-fx','-attack','wait 60',
                'set cg_thirdPerson 1','weapprev','wait 40','weapnext','wait 40','screenshot_png third-person']
    elif mode=='cheats_off':
        lines+=['set g_infiniteAmmo 1','weaponclean 3','wait 80',
                'weapnext','wait 75','weapnext','wait 75','weapnext','wait 100']
        state('cheats_off_before')
        lines+=['+attack','wait 30','-attack','wait 150']
        state('cheats_off_after')
    elif mode=='rules':
        lines+=['give weapons','give ammo 20','wait 90','weaponclean 5','wait 120','weapnext','wait 120',
                'set g_infiniteAmmo 1','wait 90']
        state('infinite_before')
        lines+=['+attack','wait 80','-attack','wait 150']
        state('infinite_after')
        lines+=['set g_infiniteAmmo 0','wait 90','+attack','wait 30','-attack','wait 150']
        state('finite_after')
        lines+=['set g_weaponDisable 131063','wait 120']
        state('disabled')
        lines+=['weapnext','wait 40']
        state('disabled_cycle')
    lines+=['echo ST_DLC_CHECK_COMPLETE','wait 10','quit']
    log=launch(folder,lines,mode=='installed')
    log=re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ', '',log,flags=re.M)
    assert 'ST_DLC_CHECK_COMPLETE' in log,log[-1500:]
    states={}
    pattern=r'ST_CASE_(\w+)\s+ST_DLC_STATE ([^\n]+)'
    for label,row in re.findall(pattern,log):
        states[label]=dict(re.findall(r'(\w+)=([^ ]+)',row))
    assert states,log[-2500:]
    if mode=='families':
        for family,base,_ in FAMILIES:
            stock,addon,fired,back=(states[family+'_'+s] for s in ('stock','addon','fired','back'))
            assert stock['name']=='stock' and int(stock['base'])==base,(family,stock)
            assert addon['name']=='qa_'+family and int(addon['base'])==base,(family,addon)
            assert addon['id']==addon['predicted'] and addon['models']=='1/1',(family,addon)
            # JKA's modern pistol has zero ammo cost; it still shares the blaster pool.
            if family=='bryar': assert fired['ammo']==addon['ammo'],(family,addon,fired)
            else: assert int(fired['ammo'])<int(addon['ammo']),(family,addon,fired)
            assert back['name']=='stock' and back['ammo']==fired['ammo'],(family,back,fired)
        assert states['custom_fx']['name']=='qa_blaster_zfx',states['custom_fx']
        assert states['custom_fx']['fx']=='1/1/1/1',states['custom_fx']
        no=states['no_pickup']
        assert no['name'].startswith('qa_') and not int(no['inventory'])&(1<<int(no['base'])),no
    elif mode=='rules':
        assert states['infinite_before']['ammo']==states['infinite_after']['ammo'],states
        assert int(states['finite_after']['ammo'])<int(states['infinite_after']['ammo']),states
        assert states['disabled']['id']=='0' and states['disabled_cycle']['id']=='0',states
        assert int(states['disabled']['allowed'])==0,states
    elif mode=='cheats_off':
        before,after=states['cheats_off_before'],states['cheats_off_after']
        assert before['name']=='qa_blaster' and after['name']=='qa_blaster',states
        assert not (int(before['allowed'])&1) and not (int(after['allowed'])&1),states
        assert int(after['ammo'])<int(before['ammo']),states
    else: assert states['stock_only']['name']=='stock' and states['stock_only']['base']=='6',states
    b.write(folder/'result.json',dict(mode=mode,source=b.sha(b.RECEIPT),
        files={name:b.sha(b.ROOT/name if mode=='installed' else path) for name,path in b.files().items()},states=states))
    print('Passed '+mode+': '+str(len(states))+' live state checks',flush=True)


if __name__=='__main__': run(sys.argv[1])
