"""Install the accepted main integration with checked backups and no new launcher."""
from pathlib import Path
from importlib import import_module
from datetime import datetime
import argparse, json, os, re, shutil, subprocess

b=import_module('Build-Combat-Controls');ROOT,OUT=b.ROOT,b.OUT
def install(profile):
    record=json.loads((OUT/'prepared.json').read_text())
    verification=json.loads((OUT/'verified.json').read_text())
    sources=b.files();after={n:b.sha(p) for n,p in sources.items()}
    assert verification['binaries']==after,'Verification is for different files'
    processes=subprocess.check_output(['powershell','-NoProfile','-Command',
        "Get-Process | Where-Object { $_.ProcessName -match '^(SaberTrials|openjk|openjkded|taystjk)\\.x86_64$' } | Select-Object -ExpandProperty Id"],text=True).strip()
    assert not processes,'Close the game before installing'
    for role in b.BASE:
        assert all(b.sha(OUT/role/n)==h for n,h in record['sources'][role].items()),'Source drift'
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=ROOT/'dist/backups'/('combat-controls-'+stamp)
    payload=dict(before=record['before'],after=after,protected=record['protected'],backup=str(backup),
        built_from={n:p.relative_to(ROOT).as_posix() for n,p in sources.items()},
        installed=stamp,verification=str(OUT/'verified.json'),new_launchers=0)
    original=profile.read_bytes()
    updated=original
    for button,command in ((b'MOUSE4',b'+feint'),(b'MOUSE5',b'+block')):
        pattern=rb'(?mi)^bind[ \t]+"?'+button+rb'"?[ \t]+[^\r\n]*'
        matches=list(re.finditer(pattern,updated));assert len(matches)<=1
        line=b'bind "'+button+b'" "'+command+b'"'
        if matches:updated=re.sub(pattern,lambda m:line,updated)
        else:updated+=(b'\n' if updated.endswith(b'\n') else b'\n\n')+line+b'\n'
    staged=OUT/'profile-bindings.cfg';staged.write_bytes(updated)
    payload['profile']={'path':str(profile),'before':b.sha(profile),'after':b.sha(staged),
        'changed':['MOUSE4 = +feint','MOUSE5 = +block'],'backup':str(backup/'profile/openjk.cfg')}
    assert profile.read_bytes()==original,'Profile changed while staging'
    import_module('Install-Handedness').install_transaction(ROOT,sources,record['before'],after,
        record['protected'],backup,ROOT/'dist/combat-controls-install.json',payload)
    saved=backup/'profile/openjk.cfg';saved.parent.mkdir();saved.write_bytes(original)
    assert profile.read_bytes()==original,'Profile changed; main installed but bindings not changed'
    pending=profile.with_name('openjk.cfg.combat-controls.pending')
    assert not pending.exists()
    try:
        pending.write_bytes(updated)
        assert b.sha(pending)==payload['profile']['after']
        os.replace(pending,profile)
        assert b.sha(profile)==payload['profile']['after']
    finally:
        if pending.exists():pending.unlink()
    # Do not retain an additional settings copy in the build folder.
    staged.unlink()
    print('Installed approved combat controls in the main mod. Verified backup:',backup,flush=True)
    print('Mouse 4 = Feint; Mouse 5 = Block. Existing launcher preserved.',flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True, help='Path to the openjk.cfg whose combat bindings will be updated')
    args = parser.parse_args()
    install(args.profile.resolve(strict=True))
