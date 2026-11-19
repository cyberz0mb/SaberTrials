"""Developer-only explicit retrieval of the user-selected translation models/fonts."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import shutil
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/translator-02'
SOURCE=ROOT/'development-source/translator'
CODES=('en','es','ru','ja','zh','zt','ar','de','fr','it','pt','pb','ko','hi','pl','tr','uk')


def get(url):
    return urlopen(Request(url,headers={'User-Agent':'ArgosTranslate/1.9'}),timeout=90)


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def download(entry):
    path=OUT/'downloads'/entry['file'];path.parent.mkdir(parents=True,exist_ok=True)
    prior=ROOT/'dist/translator-01/downloads'/entry['file']
    if not path.exists() and prior.exists():shutil.copyfile(prior,path)
    if not path.exists():
        with get(entry['url']) as response,path.with_suffix('.part').open('wb') as dest:shutil.copyfileobj(response,dest)
        path.with_suffix('.part').replace(path)
    digest=sha(path)
    if 'sha256' in entry:assert digest==entry['sha256'],entry['file']
    entry.update(bytes=path.stat().st_size,sha256=digest)
    if entry['kind']=='model':
        with ZipFile(path) as archive:
            notes=[n for n in archive.namelist() if n.count('/')==1 and n.lower().endswith('readme.md')]
            text=archive.read(notes[0]).decode('utf8',errors='replace') if notes else ''
            target=OUT/'research'/('license-'+entry['pair']+'.md');target.parent.mkdir(exist_ok=True)
            target.write_text(text,encoding='utf8')
            entry['license']='CC-BY-4.0 (model README)' if 'CC-BY' in text else 'Argos maintainer MIT-or-CC0 statement; package/corpus rights require redistribution review'
    print(entry['file'],entry['bytes'],flush=True)
    return entry


def run():
    OUT.mkdir(exist_ok=True)
    with get('https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json') as response:index_bytes=response.read()
    (OUT/'research').mkdir(exist_ok=True)
    (OUT/'research/index.json').write_bytes(index_bytes)
    index=json.loads(index_bytes)
    lock=json.loads((SOURCE/'dependencies.json').read_text())
    known={e.get('pair'):e for e in lock['files'] if e['kind'] in ('model','marian')}
    entries=[e for e in lock['files'] if e['kind'] not in ('model','marian','font')]
    for code in CODES[1:]:
        for a,b in (('en',code),(code,'en')):
            pair=a+'-'+b
            if pair in known:entries.append(known[pair]);continue
            record=next(e for e in index if e['from_code']==a and e['to_code']==b)
            url=next(link for link in record['links'] if link.startswith('https://argos-net.com/'))
            entries.append(dict(file=url.rsplit('/',1)[1],url=url,kind='model',pair=pair,
                package_version=record['package_version']))
    base='https://raw.githubusercontent.com/notofonts/noto-fonts/main/'
    for family in ('NotoSans','NotoSansArabic','NotoSansDevanagari'):
        name=family+'-Regular.ttf'
        entries.append(dict(file='fonts/'+name,url=base+'hinted/ttf/'+family+'/'+name,kind='font',license='OFL-1.1'))
    entries.append(dict(file='fonts/OFL-Noto.txt',url=base+'LICENSE',kind='font',license='OFL-1.1'))
    base='https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/'
    for region,suffix in (('Japanese','jp'),('SimplifiedChinese','sc'),('TraditionalChinese','tc'),('Korean','kr')):
        name='NotoSansCJK'+suffix+'-Regular.otf'
        entries.append(dict(file='fonts/'+name,url=base+'OTF/'+region+'/'+name,kind='font',license='OFL-1.1'))
    entries.append(dict(file='fonts/OFL-CJK.txt',url=base+'LICENSE',kind='font',license='OFL-1.1'))
    with ThreadPoolExecutor(max_workers=3) as pool:entries=list(pool.map(download,entries))
    lock.update(version=2,files=entries,index_sha256=hashlib.sha256(index_bytes).hexdigest())
    (SOURCE/'dependencies.json').write_text(json.dumps(lock,indent=2)+'\n',encoding='utf8')
    print('Locked selected models and fonts; no runtime downloads enabled.',flush=True)


if __name__=='__main__':run()
