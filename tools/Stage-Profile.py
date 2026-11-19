"""Stage Profile menus privately and make their UI-only release package."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'dist/profile-candidate-01';SRC=ROOT/'development-source/profile'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=sha(OUT/'source-receipt.json')
 records={kind:json.loads((OUT/('build-record-qa.json' if kind=='build-qa' else 'build-record.json')).read_text()) for kind in ('build','build-qa')}
 for kind,record in records.items():assert record['source_receipt_sha256']==source and record['ui_sha256']==sha(OUT/kind/'Release/uix86_64.dll')
 menus=OUT/'menus/ui/jamp';menus.mkdir(parents=True,exist_ok=True)
 for name in ('player.menu','ingame_player.menu'):shutil.copy2(SRC/name,menus/name)
 package=OUT/'zzzzzzz_sabertrials_profile.pk3'
 with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(menus.glob('*.menu')):
   entry=zipfile.ZipInfo('ui/jamp/'+p.name,(2026,11,6,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
 record={'source_receipt_sha256':source,'menus':{p.relative_to(OUT/'menus').as_posix():sha(p) for p in menus.glob('*.menu')},'package':{package.name:sha(package)},'builds':{kind:sha(OUT/kind/'Release/uix86_64.dll') for kind in ('build','build-qa')},'build_records':records}
 (OUT/'stage-receipt.json').write_text(json.dumps(record,indent=2));print('Profile menus staged. No installed files or launchers changed.')
if __name__=='__main__':main()
