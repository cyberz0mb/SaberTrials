"""Native gameplay checks. Fixture controls set preconditions, not staff authority."""
import re,time

def gameplay(n):
    for i in range(3):n.client(i)
    initial=n.states()
    def place(i,x=2432,y=-744,z=-39.88):n.command(f'st_staffqa place {i} {x} {y} {z}')
    place(2);place(1,2432,-544);place(0,2432,-644);time.sleep(.5)
    for field in ('duel','objective','tournament'):
        n.command(f'st_staffqa {field} 2 1')
        for command in ('freeze #2','summon #2','travel #2'):n.action(0,command,'denied')
        assert n.states()[2]['mode']==0
        n.command(f'st_staffqa {field} 2 0')
        n.command(f'st_staffqa {field} 0 1');n.action(0,'ghost on','Leave combat')
        n.command(f'st_staffqa {field} 0 0')
    n.check('active private-duel/tournament and objective flags deny staff interventions')
    target=n.states()[2]
    n.action(0,f"travel coords {target['x']} {target['y']} {target['z']}",'denied')
    n.command('st_staffqa obstacle 0 2432 -940 100')
    n.action(0,'travel coords 2432 -940 100','denied')
    n.command('st_staffqa clearobstacles 0')
    n.check('occupied and solid destination volumes reject travel without telefragging')
    def contacts(i):
        reply=n.command(f'st_staffqa trigger {i}')
        return int(re.search(r'STAFF_CONTACT touches=(\d+)',reply).group(1))
    assert contacts(2)>0
    n.action(0,'freeze #2','completed');assert contacts(2)==0
    n.action(0,'unfreeze #2','completed');assert contacts(2)>0
    assert contacts(0)>0
    n.action(0,'ghost on','completed');assert contacts(0)==0
    n.action(0,'ghost off','Ghost off');assert contacts(0)>0
    n.check('real trigger-contact path blocks frozen/ghost players and restores after exit')
    n.command('st_staffqa health 2 50')
    assert 'STAFF_PICKUP health=25' in n.command('st_staffqa pickup 2')
    assert 'dy=8.00' in n.command('st_staffqa push 2')
    assert 'STAFF_FORCE allowed=1' in n.command('st_staffqa forcecheck 1 2')
    n.action(0,'freeze #2','completed');n.command('st_staffqa health 2 50')
    assert 'STAFF_PICKUP health=0' in n.command('st_staffqa pickup 2')
    assert 'dy=0.00' in n.command('st_staffqa push 2')
    assert 'STAFF_FORCE allowed=0' in n.command('st_staffqa forcecheck 1 2')
    assert 'STAFF_FORCE allowed=0' in n.command('st_staffqa forcecheck 2 1')
    n.action(0,'unfreeze #2','completed')
    assert 'STAFF_PICKUP health=25' in n.command('st_staffqa pickup 2')
    assert 'dy=8.00' in n.command('st_staffqa push 2')
    assert 'STAFF_FORCE allowed=1' in n.command('st_staffqa forcecheck 1 2')
    n.check('pickup, mover-push and Force eligibility boundaries block freeze and restore after release')
    place(2)
    # A slow real missile gives time to restrict its issuer after launch.
    distant=max(initial.values(),key=lambda p:(p['x']-2432)**2+(p['y']+744)**2)
    place(0,2432,-544);place(1,distant['x'],distant['y'],distant['z'])
    n.command('st_staffqa disarm 2');n.command('st_staffqa health 2 100')
    missile=n.command('st_staffqa missile 0 2');assert 'trace=2 ' in missile,missile
    time.sleep(2.5)
    health=n.states()[2]['health'];assert health<100,('positive projectile control did not hit',n.states())
    n.command('st_staffqa missile 0 2');n.action(0,'ghost on','completed');time.sleep(2.5)
    assert n.states()[2]['health']==health
    n.action(0,'ghost off','Ghost off')
    n.command('st_staffqa missile 1 2');n.action(0,'freeze #1','completed');time.sleep(2.5)
    assert n.states()[2]['health']==health
    n.action(0,'unfreeze #1','completed')
    n.action(0,'freeze #2','completed');n.command('st_staffqa missile 1 2');time.sleep(2.5)
    assert n.states()[2]['health']==health
    n.action(0,'unfreeze #2','completed');missile=n.command('st_staffqa missile 1 2');assert 'trace=2 ' in missile,missile
    time.sleep(2.5)
    assert n.states()[2]['health']<health
    n.check('real missiles cannot damage frozen targets or deal delayed damage for restricted issuers; damage restores')
    place(0,2432,-644);time.sleep(.5)
    view,visible=n.view(2);assert visible[0]['valid']==1,visible
    n.action(0,'ghost on','completed');time.sleep(.3)
    view,visible=n.view(2);assert visible[0]['valid']==0,visible
    n.input(0,'+moveup');n.input(0,'+attack');time.sleep(.5)
    view,_=n.view(0);n.input(0,'-moveup');n.input(0,'-attack')
    assert view['mode']==2 and abs(view['z']-view['sz'])<40,view
    n.action(0,'ghost off','Ghost off');time.sleep(.3)
    view,visible=n.view(2);assert visible[0]['valid']==1,visible
    n.check('observer snapshots hide ghost and restore visibility; attack input keeps prediction aligned')
    saved=n.states()[0];n.action(0,'ghost on','completed')
    n.command(f"st_staffqa obstacle 0 {saved['x']} {saved['y']} {saved['z']+100}")
    n.input(0,'+moveup');time.sleep(.8);n.input(0,'-moveup')
    assert n.states()[0]['z']>saved['z']+160
    n.command('st_staffqa clearobstacles 0')
    n.check('ghost flight passes through a verified solid obstacle')
    n.command(f"st_staffqa obstacle 0 {saved['x']} {saved['y']} {saved['z']}")
    n.action(0,'ghost off','Ghost off');state=n.states()[0]
    assert state['mode']==0 and state['solid']==0 and any(abs(state[a]-saved[a])>40 for a in ('x','y','z')),state
    n.command('st_staffqa clearobstacles 0')
    n.check('blocked ghost return selects a safe alternative without residual restriction')
    n.action(0,'ghost on','completed')
    n.input(0,'screenshot silent');time.sleep(.3)
    n.action(0,'ghost off','Ghost off')
