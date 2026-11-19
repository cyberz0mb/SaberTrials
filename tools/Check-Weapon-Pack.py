"""Check a release Weapon PK3 for additive definitions, assets and effects."""
from pathlib import Path, PurePosixPath
import argparse
import re
import sys
from zipfile import ZipFile, BadZipFile

FAMILIES={'bryar','bryar_old','blaster','disruptor','bowcaster','repeater','demp2','flechette','rocket','concussion'}
REQUIRED={'version','id','name','baseWeapon','viewModel','worldModel'}
EFFECTS={'muzzleEffect','altMuzzleEffect','shotEffect','altShotEffect','impactEffect','altImpactEffect'}
SOUNDS={'fireSound','altFireSound'}
ASSETS=EFFECTS|SOUNDS|{'viewModel','worldModel','icon','handsModel','projectileModel','altProjectileModel'}
TOKEN=re.compile(r'//[^\n]*|/\*.*?\*/|"[^"\n]*"|[{}]|[^\s{}]+',re.S)


def definition(text):
    if len(text.encode('utf-8'))>=8192: raise ValueError('Definition exceeds 8191 bytes')
    tokens=[m.group() for m in TOKEN.finditer(text) if not m.group().startswith(('//','/*'))]
    if tokens[:2]!=['weapon','{'] or tokens[-1:]!=['}'] or len(tokens[2:-1])%2:
        raise ValueError('Expected one weapon { key value ... } block')
    result={}
    for key,value in zip(tokens[2:-1:2],tokens[3:-1:2]):
        if key not in REQUIRED|ASSETS: raise ValueError('Unknown key '+key)
        if key in result: raise ValueError('Duplicate key '+key)
        result[key]=value[1:-1] if value.startswith('"') and value.endswith('"') else value
    if REQUIRED-result.keys(): raise ValueError('Missing fields: '+', '.join(sorted(REQUIRED-result.keys())))
    if result['version']!='1': raise ValueError('version must be 1')
    if not re.fullmatch(r'[a-z0-9_-]{1,31}',result['id']): raise ValueError('Invalid weapon id')
    if '..' in result['id'] or result['baseWeapon'] not in FAMILIES: raise ValueError('Invalid baseWeapon')
    if not 0<len(result['name'].encode('utf-8'))<=63 or '^' in result['name'] or any(ord(c)<32 for c in result['name']):
        raise ValueError('Invalid display name')
    for key in ASSETS&result.keys():
        value=result[key]
        if not re.fullmatch(r'[a-z0-9_./-]{1,63}',value) or value.startswith('/') or '..' in value:
            raise ValueError('Invalid asset path for '+key)
    if not result['viewModel'].endswith('.md3') or not result['worldModel'].endswith('.glm'):
        raise ValueError('viewModel must be MD3; worldModel must be GLM')
    return result


def check(path):
    errors,warnings=[],[]
    with ZipFile(path) as archive:
        names=[p.filename for p in archive.infolist() if not p.is_dir()]
        files=set(names)
        if len(files)!=len(names): errors.append('Duplicate ZIP members')
        folded={name.lower() for name in names}
        if len(folded)!=len(names): errors.append('Case-colliding ZIP members')
        for name in names:
            pure=PurePosixPath(name)
            if name!=name.lower() and name!='README.txt': errors.append('Use lowercase path: '+name)
            if name.startswith('/') or '\\' in name or '..' in pure.parts: errors.append('Unsafe ZIP path: '+name)
            if pure.suffix.lower() in ('.dll','.exe','.qvm','.cfg'): errors.append('Do not package code/configuration: '+name)
            if name.startswith(('models/weapons2/','effects/weapons/','sound/weapons/','gfx/hud/','ui/')):
                errors.append('Stock replacement path: '+name)
        definitions=[name for name in names if name.startswith('ext_data/st_weapons/') and name.endswith('.weapon')]
        if not definitions: errors.append('No ext_data/st_weapons/*.weapon definitions')
        if len(definitions)>63: errors.append('More than 63 weapon definitions')
        ids=set()
        for name in sorted(definitions):
            try: data=definition(archive.read(name).decode('utf-8'))
            except (ValueError,UnicodeDecodeError) as error: errors.append(f'{name}: {error}');continue
            if data['id'] in ids: errors.append('Duplicate weapon id: '+data['id'])
            ids.add(data['id'])
            for key in EFFECTS|SOUNDS:
                if key not in data: warnings.append(f'{data["id"]}: {key} missing; uses JKA fallback')
            for key in ASSETS&data.keys():
                value=data[key]
                if key in EFFECTS:
                    if not value.startswith('st_dlc/'): errors.append(f'{name}: {key} must use st_dlc/ namespace')
                    target='effects/'+value+'.efx'
                elif key in SOUNDS:
                    if not value.startswith('sound/st_dlc/'): errors.append(f'{name}: {key} must use sound/st_dlc/ namespace')
                    target=value
                elif key=='icon':
                    if not value.startswith('gfx/st_dlc/'): errors.append(f'{name}: icon must use gfx/st_dlc/ namespace')
                    if not any(value+ext in files for ext in ('.png','.tga','.jpg')):
                        warnings.append(f'{name}: icon image absent; verify the named shader exists')
                    continue
                else:
                    if not value.startswith('models/st_dlc/'): errors.append(f'{name}: {key} must use models/st_dlc/ namespace')
                    target=value
                if target not in files: errors.append(f'{name}: missing declared asset {target}')
    return errors,warnings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pk3',type=Path)
    parser.add_argument('--allow-fallbacks',action='store_true',help='Allow incomplete custom-effect coverage for development')
    args=parser.parse_args()
    try: errors,warnings=check(args.pk3)
    except (OSError,BadZipFile) as error: parser.exit(1,str(error)+'\n')
    for line in errors: print('ERROR: '+line)
    for line in warnings: print('WARNING: '+line)
    if errors or (warnings and not args.allow_fallbacks): sys.exit(1)
    print('Package checks passed. Test models, embedded references and effects in-game before release.')
