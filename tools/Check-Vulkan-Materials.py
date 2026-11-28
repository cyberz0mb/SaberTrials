"""Verify real installed character materials do not default when Rend2 add-ons are present."""
import argparse
from importlib import import_module
import re
import zipfile

c=import_module('Check-Vulkan');b=c.b

def expected_materials(model):
    name,skin=model.split('/',1)
    path=f'models/players/{name}/model_{skin}.skin'
    matches=[]
    for package in sorted((b.ROOT.parent/'base').glob('*.pk3')):
        with zipfile.ZipFile(package) as archive:
            if path in archive.namelist():
                matches.append((package,archive.read(path).decode('utf-8',errors='replace')))
    assert matches,'Installed skin missing: '+path
    package,skintext=matches[-1]
    materials={line.split(',',1)[1].strip().lower() for line in skintext.splitlines()
        if ',' in line and not line.lstrip().startswith('//')}
    return {m for m in materials if m.startswith('models/')},package

def run(renderer,models):
    folder,mod=c.stage(renderer+'-materials')
    lines=['wait 100','set g_gametype 0','set g_warmup 0','set cg_forceModel 0',
        'set model '+models[0],'devmap mp/ffa3','wait 450','team free','wait 140',
        'st_emoteuiqa resume','set cg_thirdPerson 1','set cg_thirdPersonAngle 180',
        'set cg_thirdPersonRange 100','wait 30']
    expected={};packages={}
    for model in models:
        materials,package=expected_materials(model);expected[model]=sorted(materials)
        packages[package.name]=b.sha(package)
        addon=package.with_name(package.stem+'_rend2.pk3')
        if addon.exists():packages[addon.name]=b.sha(addon)
        lines+=['set model '+model,'wait 160','screenshot_png '+model.replace('/','-'),'wait 30']
    lines+=['shaderlist','imagelist','st_activeRenderer','st_rendererError','echo ST_MATERIALS_DONE','wait 20','quit']
    process=c.launch(folder,mod,renderer,lines)
    try:code=process.wait(timeout=100)
    finally:
        if process.poll() is None:process.kill();process.wait()
    log=(mod/'qconsole.log').read_text(errors='replace')
    clean=re.sub(r'\^[0-9]','',log)
    failures=[]
    for model,names in expected.items():
        for material in names:
            rows=[line for line in clean.splitlines() if re.search(r'(?<![\w/])'+re.escape(material)+r'\s*(?:\(DEFAULTED\))?\s*$',line,re.I)]
            if not rows or any('(DEFAULTED)' in row for row in rows):failures.append(material)
    active=f'Cvar st_activeRenderer = "{renderer}"' in clean and 'Saved graphics settings retained.' not in log
    complete=code==0 and 'ST_MATERIALS_DONE' in log and active
    result=dict(passed=not failures and complete,
        source=b.sha(b.OUT/'source-receipt.json'),renderer=renderer,scenario='materials',models=models,
        expected=expected,failed_materials=failures,inputs=b.read(folder/'inputs.json'),packages=packages,
        log=b.sha(mod/'qconsole.log'),screenshots={p.name:b.sha(p) for p in (mod/'screenshots').glob('*.png')})
    b.write(folder/'result.json',result)
    print(folder,flush=True)
    assert complete,'Renderer failed, fell back, or did not complete the check'
    assert not failures,'Defaulted/missing character materials: '+', '.join(failures)
    print('Passed installed character material check.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renderer',default='rd-vulkan',choices=('rd-vulkan','rd-rend2','rd-vanilla'))
    parser.add_argument('--models',nargs='+',default=['ichigo_hollow/default'])
    args=parser.parse_args();run(args.renderer,args.models)
