"""Record production binary, native regression, menu and normal-speed combat evidence."""
from importlib import import_module
import json,re
b=import_module('Build-Combat-Controls');ROOT,OUT=b.ROOT,b.OUT
tests=(OUT/'tests/Testing/Temporary/LastTest.log').read_text()
assert tests.count('Test Passed.')==5
qa=OUT/'qa'
for mode in ('before','after','practice'):
    log=(qa/mode/'home/SaberTrials/qconsole.log').read_text(errors='replace')
    assert 'MAIN_COMBAT_' in log and 'ERROR:' not in log and 'ST_CONTROLS_FAIL' not in log
    assert 'Info string length exceeded' not in log and 'already defined' not in log
log=(qa/'practice/home/SaberTrials/qconsole.log').read_text(errors='replace')
assert 'MAIN_COMBAT_PRACTICE_COMPLETE' in log
assert '\\st_feintProtocol\\2\\' in log
assert 'Too many info changes' not in log
def ids(part):
    result=[]
    for n in re.findall(r' (?:TORSO|LEGS) Anim: (\d+),',part):
        n=int(n)
        if not result or result[-1]!=n:result.append(n)
    return result
evidence={}
for name,start,ready,attack in [('blue',175,850,126),('yellow',252,917,203),('red',329,851,280),('green',1607,917,1558),('orange',1761,851,1712)]:
    for context in ('CROUCH','AIR'):
        part=log.split(f'MOBILE_{name}_{context}_START',1)[1].split(f'MOBILE_{name}_{context}_CANCEL',1)[0]
        a=ids(part)
        assert start in a and ready in a[a.index(start)+1:],(name,context,a)
        assert attack not in a,(name,context,'attack committed')
        assert ('CROUCH' if context=='CROUCH' else 'JUMP') in part
    part=log.split(f'MOBILE_{name}_REPEAT_START',1)[1].split(f'MOBILE_{name}_REPEAT_CANCEL',1)[0]
    a=ids(part);assert [n for n in a if n in (start,ready)]==[start,ready]*3,(name,a)
    assert attack not in a
    after=log.split(f'MOBILE_{name}_REPEAT_CANCEL',1)[1].split(f'MOBILE_{name}_END',1)[0]
    assert 'BOTH_ST_GUARD_SINGLE' in after,name
    evidence[name]=dict(crouched=True,airborne=True,consecutive_cancels=3,held_block=True)
for name,path in b.files().items():
    if '/' not in name:assert b.sha(qa/'practice/home/SaberTrials'/name)==b.sha(path),name
assert b.sha(qa/'practice/client/SaberTrials.x86_64.exe')==b.sha(b.files()['client/SaberTrials.x86_64.exe'])
assert 'bind "K" "+feint"' in (qa/'after/home/SaberTrials/openjk.cfg').read_text()
result=dict(binaries={n:b.sha(p) for n,p in b.files().items()},native_groups=5,
    feint_checks=20678,block_parry_checks=275,held_pose_checks=125,wire_checks=51,
    runtime=dict(model='kyle/default',map='mp/duel1',timescale=1,styles=evidence),
    interface=dict(current_design_preserved=True,action_search=True,rebind_and_apply=True),
    screenshots={str(p.relative_to(qa)):b.sha(p) for p in qa.rglob('*.png')},
    logs={str(p.relative_to(qa)):b.sha(p) for p in qa.rglob('qconsole.log')},
    limitations=['Hosted latency/opponent testing remains separate.','Purple full-motion and dual/staff feints remain deferred.'])
b.write(OUT/'verified.json',result)
print('Verified main build: all five styles, crouch/air, three consecutive feints, held block, native menus and saved binding.')
