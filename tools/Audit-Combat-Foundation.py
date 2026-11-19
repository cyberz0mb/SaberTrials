"""Read-only accepted-source audit + derived fixtures/reports. No server launch.

Run after the native combat_catalog build. Only writes under the chosen output
directory, which must be a non-live directory inside this project's dist.
"""
from pathlib import Path
import argparse, hashlib, json, math, re, subprocess, sys, zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'dist/stance-candidate-02'
sys.path.insert(0,str(ROOT/'tools'))
from stance_library import rows

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def body(text,signature):
    begin=text.index(signature)
    brace=text.index('{',begin)
    depth=0
    # Ignore braces in strings and comments, including nested-looking comments.
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|//[^\n]*|/\*[\s\S]*?\*/|[{}]',text[brace:]):
        if token[0]=='{':depth+=1
        elif token[0]=='}':
            depth-=1
            if not depth:return text[begin:brace+token.end()]
    raise ValueError('Unclosed source function: '+signature)

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')

def verify_baseline():
    manifest=json.loads((BASE/'sources.json').read_text())
    count=0
    for kind in ('game','frontend'):
        for name,expected in manifest['sources'][kind].items():
            if sha(BASE/kind/name)!=expected:raise ValueError('Source drift: '+kind+'/'+name)
            count+=1
    for name,expected in manifest['protected'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Installed drift: '+name)
    package=BASE/'assets/zz_sabertrials_stances_v1.pk3'
    if sha(package)!=manifest['library_sha256']:raise ValueError('Stance package drift')
    return manifest,count,package

def main(output,catalog_exe):
    output=output.resolve()
    if not output.is_relative_to((ROOT/'dist').resolve()) or output==(ROOT/'dist').resolve():
        raise ValueError('Output must be a dedicated directory under dist')
    if output.is_relative_to(BASE.resolve()) or BASE.resolve().is_relative_to(output):
        raise ValueError('Never write audit output into the accepted stance candidate')
    manifest,count,package=verify_baseline()
    game=BASE/'game/codemp/game'
    saber=(game/'w_saber.c').read_text()
    combat=(game/'g_combat.c').read_text()
    code=(game/'bg_saber.c').read_text()
    enumtext=(game/'anims.h').read_text()
    enumtext=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',enumtext)
    enumtext=enumtext[enumtext.index('{')+1:enumtext.index('}')]
    names=[n.strip() for n in enumtext.split(',') if n.strip()]
    if any(not re.fullmatch(r'\w+',n) for n in names):raise ValueError('Animation enum changed')
    ids={n:i for i,n in enumerate(names)}
    stride=ids['BOTH_A2_T__B_']-ids['BOTH_A1_T__B_']
    with zipfile.ZipFile(package) as z:cfg=rows(z.read('models/players/_humanoid/animation.cfg'))
    table={}
    for match in re.finditer(r'\{\s*"[^"\n]+"\s*,\s*(\w+)[^\n]*?\}\s*,?\s*//\s*(LS_\w+)',code):
        table[match[2]]=match[1]
    catalog=json.loads(subprocess.check_output([str(catalog_exe.resolve())],text=True))
    directions=['TL2BR','L2R','BL2TR','BR2TL','R2L','TR2BL','T2B']
    for style in catalog['styles']:
        for direction in style['directions']:
            group=direction['animation_group'];records={}
            for label,prefix in [('windup','S'),('attack','A'),('return','R')]:
                move=f'LS_{prefix}_{directions[direction["direction"]]}'
                name=names[ids[table[move]]+(group-1)*stride]
                first,num,loop,fps=cfg[name]
                if not num or not fps:raise ValueError('Empty source animation '+name)
                records[label]={'move':move,'animation':name,'animation_id':ids[name],
                    'first_frame':first,'frames':num,'loop_frames':loop,'fps':fps,
                    'nominal_ms':num*math.ceil(1000/abs(fps)),
                    'reverse':fps<0}
            direction['clips']=records
    # Include every source transition for feasibility, including reverse-play rows.
    transitions={}
    for group in (1,2,3,6,7):
        transitions[str(group)]=[{'animation':name,'cfg':cfg.get(name)}
            for name in names if name.startswith(f'BOTH_T{group}_')]
    output.mkdir(parents=True,exist_ok=True)
    fixture=output/'fixtures';fixture.mkdir(exist_ok=True)
    functions=[body(saber,'static QINLINE int G_GetAttackDamage('),
               body(saber,'static QINLINE float G_GetAnimPoint('),
               body(combat,'int CheckArmor (')]
    constants=[]
    for name in ('ARMOR_PROTECTION','ARMOR_REDUCTION_FACTOR'):
        text=(game/'bg_public.h').read_text()+'\n'+(game/'g_local.h').read_text()
        match=re.search(r'^#define\s+'+name+r'\s+([^\n/]+)',text,re.M)
        if not match:raise ValueError('Missing source constant '+name)
        constants.append('#define '+name+' '+match[1].strip())
    (fixture/'accepted_damage_functions.inc').write_text(
        '/* Derived unchanged from accepted OpenJK/Saber Trials sources; GPL-2.0. */\n'+
        '\n'.join(constants+functions)+'\n',encoding='utf-8',newline='\n')
    cvars={}
    for match in re.finditer(r'XCVAR_DEF\(\s*(\w+)\s*,\s*"([^"]*)"',(game/'g_xcvar.h').read_text()):
        if match[1] in ('d_saberSPStyleDamage','g_saberDamageScale','g_saberRealisticCombat',
                       'st_masterSaberDamage','st_masterModeActive','g_saberDmgDelay_Idle','g_saberDmgDelay_Wound'):
            cvars[match[1]]=match[2]
    report={'status':'foundation only; no game integration or multiplayer validation',
        'baseline':str(BASE),'source_files_verified':count,
        'installed_files_verified':len(manifest['protected']),
        'manifest_sha256':sha(BASE/'sources.json'),'package_sha256':sha(package),
        'damage_sources':{n:sha(game/n) for n in ('w_saber.c','g_combat.c','g_stcombat.c','g_sabertrials.c')},
        'shared_pmove_equal':sha(game/'bg_pmove.c')==sha(BASE/'frontend/codemp/game/bg_pmove.c'),
        'animation_group_stride':stride,'animation_enum_count':ids['MAX_ANIMATIONS'],
        'declared_defaults_not_live_settings':cvars,'transitions':transitions,
        'fixture_sha256':sha(fixture/'accepted_damage_functions.inc'),
        'catalog_executable_sha256':sha(catalog_exe)}
    write(output/'style-move-matrix.json',catalog)
    write(output/'baseline-audit.json',report)
    verify_baseline()
    print(json.dumps({k:report[k] for k in ('source_files_verified','installed_files_verified',
        'animation_group_stride','animation_enum_count','shared_pmove_equal')}))
    print('Wrote 84 move-source records / 252 clips and unchanged damage/armor fixtures.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/combat-foundation-01')
    parser.add_argument('--catalog',type=Path,default=ROOT/'dist/combat-foundation-tests/Release/combat_catalog.exe')
    args=parser.parse_args();main(args.output,args.catalog)
