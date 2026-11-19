"""Verify, install or roll back the locally qualified Map + Model candidate.

Default is read-only verification. --apply explicitly installs the exact tested
files. Model backups stay on E:, engine backups stay in SaberTrials/dist.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,time
R=Path(__file__).resolve().parents[1]
MANIFEST=R/'dist/enhanced-model-install/install-manifest.json'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def read(p):return json.loads(Path(p).read_text())

def save(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.new');temp.write_text(json.dumps(value,indent=2));os.replace(temp,p)

def verify(manifest,qualified=True):
    if qualified:
        q=Path(manifest['qualification'])
        expected=manifest.get('qualification_sha256')
        if not expected or not q.is_file() or sha(q)!=expected or not read(q).get('ready_for_local_install',False):
            raise RuntimeError('Qualification receipt missing, changed or incomplete')
    for row in manifest['files']:
        if sha(row['source'])!=row['after']:raise RuntimeError('Candidate changed: '+row['source'])
        if sha(row['target'])!=row['before']:raise RuntimeError('Installed file changed; rebuild candidate: '+row['target'])
    for path,digest in manifest['protected'].items():
        if sha(path)!=digest:raise RuntimeError('Protected game module changed: '+path)
    return {'verified_files':len(manifest['files']),'protected_modules':len(manifest['protected']),'installed':False}

def rollback(receipt_path):
    receipt=read(receipt_path)
    # Verify the whole operation before restoring anything. Refuse to overwrite
    # another feature's later install, and tolerate a prior interrupted rollback.
    for row in receipt['files']:
        if sha(row['backup'])!=row['before']:raise RuntimeError('Backup changed: '+row['backup'])
        if sha(row['target']) not in (row['before'],row['after']):raise RuntimeError('Installed file changed since candidate: '+row['target'])
    for row in reversed(receipt['files']):
        if sha(row['target'])==row['before']:continue
        target=Path(row['target']);temp=target.with_name(target.name+'.strestore')
        shutil.copy2(row['backup'],temp)
        if sha(temp)!=row['before']:raise RuntimeError('Rollback copy failed')
        os.replace(temp,target)
    receipt['status']='rolled_back';save(receipt_path,receipt)
    return {'rolled_back':True,'files':len(receipt['files'])}

def install(manifest,receipt_path,*,qualified=True,fail_after=None):
    verify(manifest,qualified)
    if Path(receipt_path).exists():raise RuntimeError('Receipt already exists')
    receipt={'status':'preparing','files':[],'protected':manifest['protected']}
    staged=[]
    # All backups and replacements are written and hash-checked before the first
    # installed file changes. A durable receipt permits recovery after a crash.
    try:
        for row in manifest['files']:
            item=dict(row);backup=Path(row['backup']);target=Path(row['target'])
            if backup.exists():raise RuntimeError('Backup already exists: '+str(backup))
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            temp=target.with_name(target.name+'.stinstall')
            if temp.exists():raise RuntimeError('An earlier staged install needs attention: '+str(temp))
            shutil.copy2(row['source'],temp);staged.append(temp)
            if sha(backup)!=row['before'] or sha(temp)!=row['after']:raise RuntimeError('Copy verification failed')
            receipt['files'].append(item)
        save(receipt_path,receipt)
        for index,(row,temp) in enumerate(zip(receipt['files'],staged)):
            if sha(row['target'])!=row['before']:raise RuntimeError('Concurrent install detected')
            if fail_after is not None and index==fail_after:raise RuntimeError('Injected rehearsal failure')
            os.replace(temp,row['target'])
        for row in receipt['files']:
            if sha(row['target'])!=row['after']:raise RuntimeError('Installed hash mismatch')
        for path,digest in receipt['protected'].items():
            if sha(path)!=digest:raise RuntimeError('Protected module changed during install')
        receipt['status']='installed';save(receipt_path,receipt)
    except Exception:
        if Path(receipt_path).exists():rollback(receipt_path)
        raise
    finally:
        for temp in staged:
            if temp.exists():temp.unlink()
    return {'installed':True,'files':len(receipt['files']),'receipt':str(receipt_path)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group();g.add_argument('--apply',action='store_true');g.add_argument('--rollback',type=Path)
    args=p.parse_args()
    if args.rollback:result=rollback(args.rollback)
    else:
        manifest=read(MANIFEST)
        if args.apply:
            stamp=str(time.time_ns())
            for row in manifest['files']:
                row['backup']=str(Path(row['backup_root'])/stamp/Path(row['target']).name)
            result=install(manifest,R/'dist/enhanced-model-install/receipts'/(stamp+'.json'))
        else:result=verify(manifest)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
