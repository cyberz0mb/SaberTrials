"""Native rendering and interaction checks for the remaining menu skin."""
from pathlib import Path
import importlib.util
import re
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

skin=module('remainder_skin','Theme-Menu-Remainder.py')
details=module('detail_checks','Test-Menu-Details.py')
native=details.native
EVIDENCE=ROOT/'dist/verification/menu-remainder-20261006'
details.theme.SOURCE=skin.SOURCE;details.theme.OUT=skin.OUT;details.theme.NAMES=skin.NAMES
details.EVIDENCE=EVIDENCE
structure=details.structure


def snap(label):
    native.command('screenshot_png remainder-'+label)


def collect():
    for p in (native.HOME/'SaberTrials/screenshots').glob('remainder-*.png'):
        shutil.copy2(p,EVIDENCE/p.name)


def pause(label):
    native.command('ui_openmenu ingame');native.focused('ingame')
    native.click('ingame','join');native.focused('ingame_join');snap(label+'-join')
    # Existing duplicate team names use shared decorative hover targets to
    # locate their rows; the click still goes through the real mouse handler.
    native.click('ingame_join','button3');native.focused('none')
    assert 'MenuTest' in native.command('status')
    native.command('ui_openmenu ingame');native.click('ingame','join')
    native.click('ingame_join','button2');native.focused('none')
    native.command('ui_openmenu ingame');native.click('ingame','about')
    native.click('st_pause_about','details');native.focused('ingame_about');snap(label+'-about')
    native.escape();native.focused('st_pause_about')
    native.click('st_pause_about','match');native.click('st_pause_tools','bots')
    native.focused('ingame_addbot');native.click('ingame_addbot','gametypefield');snap(label+'-addbot')
    native.click('ingame_addbot','ok');native.focused('none')
    for _ in range(15):
        status=native.command('status')
        if re.search(r'\b[1-9]\d* bots\b',status):break
        time.sleep(.2)
    assert re.search(r'\b[1-9]\d* bots\b',status),status
    native.command('ui_openmenu ingame');native.click('ingame','vote')
    native.click('st_pause_vote','cast');native.focused('ingame_vote');snap(label+'-vote')
    native.escape();native.focused('st_pause_vote')
    native.click('st_pause_vote','call');native.focused('ingame_callvote')
    for button in ['miscbutton','typebutton','mapsbutton','kickbutton','botsbutton']:
        native.click('ingame_callvote',button);native.focused('ingame_callvote');snap(label+'-'+button)
    native.click('ingame_callvote','typebutton')
    native.command('set st_uiVoteTime ""');native.click('ingame_callvote','type')
    native.command('st_clientqa type 12');native.command('st_clientqa enter')
    assert '= "12"' in native.command('st_uiVoteTime')
    native.escape();native.escape();native.focused('ingame')
    native.click('ingame','about');native.click('st_pause_about','match')
    native.click('st_pause_tools','voice');native.focused('ingame_voicechat');snap(label+'-voice')
    native.escape();native.focused('none')  # Native Siege voice panel closes all.
    native.command('ui_openmenu ingame');native.click('ingame','about');native.click('st_pause_about','match')
    native.click('st_pause_tools','objectives');native.focused('ingame_objectives');snap(label+'-objectives')
    # FFA has no Siege objectives. This checks navigation and the presentation;
    # the structural comparison separately protects all Siege map logic.
    native.escape()
    collect()
    (EVIDENCE/('pause-'+label+'.log')).write_text(status)
    print('PASS native Join/Spectate, server info, Add Bot, vote categories, voice/objectives and Back',flush=True)


def title(label):
    lines=['disconnect','wait 45','ui_openmenu main','wait 10']
    expectations={}
    def step(name,commands,expected):
        lines.extend(['echo REMAINDER_STEP_'+name]+commands+['wait 15','st_clientqa state',
            'screenshot_png remainder-'+label+'-'+name,'echo REMAINDER_END_'+name])
        expectations[name]=expected
    def click(menu,item):return [f'st_clientqa move {menu} {item}','st_clientqa click','wait 4']
    step('rules',click('main','play')+click('multiplayermenu','rules_button'),'rulesMenu')
    for item,dest,choice in [('gamesmenubutton','rulesMenu_games','duelmenubutton'),
         ('forcemenubutton','rulesMenu_force','pushmenubutton'),
         ('weaponmenubutton','rulesMenu_weapons','sabermenubutton'),
         ('itemmenubutton','rulesMenu_items','bactamenubutton')]:
        step(dest,click('rulesMenu',item),dest)
        # State and screenshot after native focus also exercise description swaps.
        step(dest+'-choice',click(dest,choice),dest)
        step(dest+'-back',['st_clientqa escape'],'rulesMenu')
    # The stock rules root intentionally gives Items and Moves the same item
    # name; keyboard advances from Items to reach Moves without renaming it.
    step('moves',['st_clientqa move rulesMenu itemmenubutton','st_clientqa tab','st_clientqa enter'],'rulesMenu_moves')
    step('movesback',['st_clientqa escape'],'rulesMenu')
    step('quitdialog',click('rulesMenu','exitgamebutton'),'quitMenu')
    step('quitcancel',click('quitMenu','quitgame_cancel'),'mainMenu')
    step('rulesback',['ui_openmenu rulesMenu']+click('rulesMenu','backbutton'),'mainMenu')
    lines+=['echo REMAINDER_TITLE_COMPLETE','wait 4','quit']
    (native.MOD/'st-remainder-title.cfg').write_text('\n'.join(lines)+'\n')
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    native.command('exec st-remainder-title.cfg')
    for _ in range(160):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=re.sub(r'\^[0-9]','',f.read().decode(errors='replace'))
        if 'REMAINDER_TITLE_COMPLETE' in result:break
    (EVIDENCE/('title-'+label+'.log')).write_text(result)
    collect()
    assert 'REMAINDER_TITLE_COMPLETE' in result,result[-1500:]
    assert 'QA item missing' not in result,result[-5000:]
    for name,dest in expectations.items():
        segment=result.split('REMAINDER_STEP_'+name+'\n',1)[1].split('REMAINDER_END_'+name,1)[0]
        assert 'focused='+dest+'\n' in segment,(name,segment)
    assert not re.search(r'ERROR:.*ui/|Refusing to load non-power-2',result)
    print('PASS all Rules pages, native descriptions, Moves preview, and Back/Escape',flush=True)


def release():
    # Production UI only: render all changed menu files without any QA hook.
    for _ in range(10):
        reply=native.command('st_clientqa state')
        if 'Unknown command' in reply:break
        time.sleep(.2)
    assert 'Unknown command' in reply and 'MENU_QA' not in reply,reply
    log=native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
    for name in ['ingame_join','ingame_about','ingame_addbot','ingame_vote','ingame_callvote',
                 'ingame_voicechat','ingame_objectives']:
        native.command('ui_openmenu '+name);snap('release-'+name)
    lines=['disconnect','wait 45','ui_openmenu main','wait 10']
    for name in ['rulesMenu','rulesMenu_games','rulesMenu_force','rulesMenu_weapons','rulesMenu_items','rulesMenu_moves','quitMenu']:
        lines+=['ui_openmenu '+name,'wait 20','screenshot_png remainder-release-'+name,'wait 4']
    lines+=['echo REMAINDER_RELEASE_COMPLETE','wait 3','quit']
    (native.MOD/'st-remainder-release.cfg').write_text('\n'.join(lines)+'\n')
    native.command('exec st-remainder-release.cfg')
    for _ in range(100):
        time.sleep(.25)
        with log.open('rb') as f:f.seek(offset);result=f.read().decode(errors='replace')
        if 'REMAINDER_RELEASE_COMPLETE' in result:break
    assert 'REMAINDER_RELEASE_COMPLETE' in result,result[-1500:]
    assert not re.search(r'ERROR:.*ui/|Refusing to load non-power-2',result),result[-1500:]
    (EVIDENCE/'installed-release.log').write_text(result)
    collect()
    print('PASS installed production UI: all 14 menus rendered; no test hook or menu parser errors',flush=True)


if __name__=='__main__':
    action=sys.argv[1]
    if action=='structure':structure()
    elif action=='start':details.start(*map(int,sys.argv[2:4]))
    elif action=='pause':pause(sys.argv[2])
    elif action=='title':title(sys.argv[2])
    elif action=='stop':details.stop_test()
    elif action=='start-release':details.start(1280,1024,True)
    elif action=='release':release()
