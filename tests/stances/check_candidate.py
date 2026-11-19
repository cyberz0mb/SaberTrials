"""Audit real candidate assets and preserved source, without running any server."""
from pathlib import Path
import argparse,hashlib,json,re,struct,sys,zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from stance_library import parse_gla, rows
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(text,signature):
    begin=text.index(signature);brace=text.index('{',begin);depth=1;end=brace+1
    while depth:
        if text[end]=='{':depth+=1
        elif text[end]=='}':depth-=1
        end+=1
    return text[begin:end]
def main(out):
    m=json.loads((out/'sources.json').read_text());library=json.loads((out/'assets/library.json').read_text())
    with zipfile.ZipFile(out/'assets/zz_sabertrials_stances_v1.pk3') as z:
        assert z.testzip() is None
        combined=z.read('models/players/_humanoid/_humanoid.gla')
        cfg=z.read('models/players/_humanoid/animation.cfg');events=z.read('models/players/_humanoid/animevents.cfg')
    base_path=ROOT.parent/'base/japlus_gla_anims.pk3'
    with zipfile.ZipFile(base_path) as z:
        original=z.read('models/players/_humanoid/_humanoid.gla');old_cfg=z.read('models/players/_humanoid/animation.cfg')
        assert events==z.read('models/players/_humanoid/animevents.cfg')
    before=parse_gla(original);after=parse_gla(combined)
    assert combined[100:after[5]]==original[100:before[5]]
    assert combined[after[5]:after[5]+before[4]*before[6]*3]==original[before[5]:before[5]+before[4]*before[6]*3]
    assert combined[after[7]:after[7]+before[9]-before[7]]==original[before[7]:before[9]]
    assert cfg.startswith(old_cfg) and all(rows(cfg)[k]==v for k,v in rows(old_cfg).items())
    # Independent per-bone value comparison, including remapped pool indices.
    samples=0
    for clip in library['stances']:
        path=ROOT/'assets/stance-inputs'/clip['pack']
        with zipfile.ZipFile(path) as z:
            name='models/players/_humanoid/_humanoid.gla'
            donor=z.read(name) if name in z.namelist() else original
        d=parse_gla(donor)
        for f in range(clip['count']):
            for b in range(after[6]):
                old=d[5]+((clip['donor_frame']+f)*d[6]+b)*3
                new=after[5]+((clip['frame']+f)*after[6]+b)*3
                oi=int.from_bytes(donor[old:old+3],'little');ni=int.from_bytes(combined[new:new+3],'little')
                assert donor[d[7]+oi*14:d[7]+(oi+1)*14]==combined[after[7]+ni*14:after[7]+(ni+1)*14]
                samples+=1
    # Never mix in broader pending account/tournament source trees.
    allowed={'codemp/game/anims.h','codemp/cgame/animtable.h','codemp/game/bg_public.h',
             'codemp/game/bg_panimate.c','codemp/game/bg_pmove.c','codemp/game/bg_saber.c',
             'codemp/game/st_stance_policy.h','codemp/game/st_stance_runtime.h','codemp/game/st_stance_assets.h',
             'codemp/cgame/cg_main.c',
             'codemp/game/g_xcvar.h','codemp/game/g_client.c','codemp/ui/ui_xcvar.h',
             'codemp/ui/ui_st_stances.inc','codemp/ui/ui_st_stance_catalog.h',
             'codemp/ui/ui_sabertrials_menu.inc','codemp/ui/ui_saber.c','codemp/ui/ui_shared.c'}
    for kind in ('game','frontend'):
        assert set(m['changes'][kind])<=allowed
        for name,h in m['sources'][kind].items():assert sha(out/kind/name)==h, name
        for name in ('codemp/game/w_saber.c','codemp/game/g_combat.c','codemp/game/g_cmds.c',
                     'codemp/game/g_sabertrials.c','codemp/game/g_hand_lock.inc'):
            if name in m['baseline_sources'][kind]:assert m['sources'][kind][name]==m['baseline_sources'][kind][name],name
        # Enum IDs preceding the append must not shift.
        old=(Path(m['origins'][kind])/'codemp/game/anims.h').read_text()
        new=(out/kind/'codemp/game/anims.h').read_text()
        assert old.split('\tMAX_ANIMATIONS,')[0]==new.split('\tBOTH_ST_READY_01,')[0]
        old=(Path(m['origins'][kind])/'codemp/game/bg_pmove.c').read_text()
        new=(out/kind/'codemp/game/bg_pmove.c').read_text()
        assert function(old,'int PM_GetSaberStance(void)')==function(new,'static int PM_GetStockSaberStance(void)').replace('static int PM_GetStockSaberStance','int PM_GetSaberStance',1)
    for name,h in m['protected'].items():assert sha(ROOT/name)==h,'Installed file changed: '+name
    # Shared code must be identical for authoritative simulation and prediction.
    for name in ('anims.h','st_stance_runtime.h','st_stance_policy.h','st_stance_assets.h'):
        assert (out/'game/codemp/game'/name).read_bytes()==(out/'frontend/codemp/game'/name).read_bytes(),name
    for name,signatures in [('bg_pmove.c',['int PM_GetSaberStance(void)','static int PM_GetStockSaberStance(void)']),
                            ('bg_panimate.c',['qboolean BG_SaberStanceAnim( int anim )','qboolean BG_InSaberStandAnim( int anim )'])]:
        for signature in signatures:
            assert function((out/'game/codemp/game'/name).read_text(),signature)==function((out/'frontend/codemp/game'/name).read_text(),signature)
    report={'base_frames_preserved':before[4],'total_frames':after[4],'donor_bone_samples_verified':samples,
            'original_cfg_rows_preserved':len(rows(old_cfg)), 'original_events_preserved':True,
            'installed_files_preserved':len(m['protected']),'damage_and_lock_sources_preserved':True,
            'stance_policy_game_prediction_agree':True,'map_or_server_launched':False}
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);main(p.parse_args().candidate.resolve())
