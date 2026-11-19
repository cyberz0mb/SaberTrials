"""Native navigation and screenshots of honest offline Ranked screens."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, shutil, time
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('photo',ROOT/'tools/Test-Photo.py')
photo=importlib.util.module_from_spec(spec);spec.loader.exec_module(photo)
EVIDENCE=ROOT/'dist/verification/ranked-menu-20261012'
photo.EVIDENCE=EVIDENCE
def main():
    p=argparse.ArgumentParser();p.add_argument('--height',type=int,default=720)
    p.add_argument('--installed',action='store_true');args=p.parse_args()
    mode='installed' if args.installed else 'qa'
    extra=None if args.installed else ROOT/'dist/ranked-menu-staging'
    photo.start(mode,1280,args.height,extra_stage=extra)
    try:
        pages=[('overview','st_main_ranked'),('duel','st_ranked_duel'),('teams','st_ranked_teams'),('servers','st_ranked_servers')]
        lines=['disconnect','wait 30','ui_openmenu main','wait 10']
        captures=[]
        def click(menu,item):return [f'st_clientqa move {menu} {item}','st_clientqa click','wait 5','st_clientqa state']
        def capture(key):
            name=f'ranked-{mode}-{key}-1280x{args.height}'
            captures.append(name)
            return ['screenshot_png '+name,'wait 8']
        if args.installed:
            for key,page in pages:
                lines+=['ui_openmenu '+page,'wait 5']+capture(key)
        else:
            lines+=click('main','play')+click('multiplayermenu','ranked')
            current='st_main_ranked'
            for key,page in pages:
                lines+=click(current,key)+capture(key)
                current=page
            lines+=['st_clientqa escape','wait 5','st_clientqa state']
            lines+=click('multiplayermenu','ranked')+click('st_main_ranked','duel')+click('st_ranked_duel','back')
            lines+=click('multiplayermenu','ranked')+click('st_main_ranked','servers')+click('st_ranked_servers','browse')
            lines+=['st_clientqa tab','st_clientqa state']
        lines+=['echo RANKED_MENU_COMPLETE','wait 4','quit']
        (photo.native.MOD/'st-ranked-menu-test.cfg').write_text('\n'.join(lines)+'\n')
        log=photo.native.HOME/'SaberTrials/qconsole.log';offset=log.stat().st_size
        photo.command('exec st-ranked-menu-test.cfg')
        for _ in range(150):
            time.sleep(.2);result=log.read_bytes()[offset:].decode(errors='replace')
            if 'RANKED_MENU_COMPLETE' in result:break
        assert 'RANKED_MENU_COMPLETE' in result,result[-3000:]
        assert not any(e in result for e in ['QA item missing','Unknown command','ERROR: ui/']),result[-4000:]
        if not args.installed:
            for page in [p[1] for p in pages]+['multiplayermenu','joinserver']:
                assert 'focused='+page+'\n' in result,page
        (EVIDENCE/f'{mode}-1280x{args.height}.log').write_text(result)
        for name in captures:
            image=photo.native.HOME/'SaberTrials/screenshots'/f'{name}.png'
            assert image.exists(),image
            shutil.copy2(image,EVIDENCE/image.name)
        main=ROOT/'ui/jamp/main.menu' if args.installed else ROOT/'dist/ranked-menu-staging/ui/jamp/main.menu'
        (EVIDENCE/f'{mode}-1280x{args.height}.json').write_text(json.dumps({'passed':True,'mode':mode,
            'menu':hashlib.sha256(main.read_bytes()).hexdigest()},indent=2)+'\n')
        print('PASS Ranked tabs, empty states, Back/Escape and unranked browser route' if not args.installed else 'PASS installed Ranked screens render')
    finally:photo.stop()
if __name__=='__main__':main()
