"""Exercise every selected model and representative non-English routes offline."""
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/translator-02'
spec=importlib.util.spec_from_file_location('translator',ROOT/'development-source/translator/worker.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


def run():
    translator=w.Translator(OUT/'runtime')
    fixtures=json.loads((ROOT/'tests/translator/language-fixtures.json').read_text(encoding='utf8'))
    results=[];ids={code:id for id,code in w.LANGUAGES.items()}
    pairs=[pair for c in ids if c!='en' for pair in [('en',c),(c,'en')]]
    pairs += [('ru','ja'),('ar','hi'),('ko','uk'),('pb','de'),('zt','fr'),('tr','pl'),('es','it')]
    for source,target in pairs:
        started=time.perf_counter()
        raw=fixtures[source].encode('utf8')
        status,translated=translator.translate(raw,b'',ids[source],ids[target])
        automatic,auto_output=translator.translate(raw,b'',0,ids[target])
        assert automatic=='ok' and auto_output and w.safe_text(auto_output),(source,target,automatic,auto_output)
        row=dict(source=source,target=target,status=status,input=fixtures[source],output=translated,seconds=round(time.perf_counter()-started,3))
        results.append(row)
        print(json.dumps(row,ensure_ascii=True),flush=True)
        assert status=='ok' and w.safe_text(translated) and '\u2581' not in translated and '{{' not in translated,row
    # Script detection must not force English on unsupported text.
    detected={code:translator.detect(text) for code,text in fixtures.items()}
    for code,actual in detected.items():
        assert actual in ({code,'pt'} if code=='pb' else {code,'zh'} if code=='zt' else {code}),(code,actual)
    for sample,code in [('hola amigos','es'),('bonjour','fr'),('guten tag','de'),('obrigado','pt'),
                        ('ciao ragazzi','it'),('merhaba','tr'),('ありがとう','ja'),('дякую','uk')]:
        assert translator.detect(sample)==code,(sample,code)
    for sample in ('no','OK','123'):
        assert translator.detect(sample) is None,sample
    status,translated=translator.translate(b'bonjour Saber Trials',b'',0,1)
    assert status=='ok' and 'Saber Trials' in translated,(status,translated)
    assert translator.translate(b'Saber Trials',b'',0,1)[0]=='same'
    from hashlib import sha256
    (OUT/'language-results.json').write_text(json.dumps(dict(results=results,detected=detected,
        worker=sha256((ROOT/'development-source/translator/worker.py').read_bytes()).hexdigest()),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('All selected direct pairs and representative pivot routes produced translations offline.',flush=True)


if __name__=='__main__':run()
