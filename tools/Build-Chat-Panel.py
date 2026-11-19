"""Build and install the chat panel on the verified combined client."""
from datetime import datetime
from importlib import import_module
from pathlib import Path
import shutil
import sys
from zipfile import ZIP_DEFLATED, ZipFile

sys.dont_write_bytecode = True
base = import_module('Build-UI-HUD-Polish')
ROOT, HUD = base.ROOT, base.HUD
OUT = ROOT/'dist/chat-ui-01'
RECEIPT = OUT/'source-receipt.json'
sha, read, write, tree, insert = base.sha, base.read, base.write, base.tree, base.insert
build_tools = base.build_tools
build_tools.OUT, build_tools.RECEIPT = OUT, RECEIPT


def prepare():
    prior = read(ROOT/'dist/ui-hud-polish-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items())
    old = base.OUT
    receipt = read(old/'source-receipt.json')
    assert sha(old/'source-receipt.json')==prior['source_sha256']
    for role in ('engine','frontend'):
        assert tree(old/role)==receipt['sources'][role]
    for role in ('engine','ui','cgame'):
        _,_,module,name = build_tools.ROLES[role]
        assert sha(old/('build-'+role)/'Release'/module)==installed[name]

    OUT.mkdir(exist_ok=True)
    for role in ('engine','frontend'):
        shutil.copytree(old/role,OUT/role,dirs_exist_ok=True)

    wire()
    art = OUT/'art'
    art.mkdir(exist_ok=True)
    import_module('hud_theme_art').chat_panel(art)
    with ZipFile(ROOT/HUD) as source, ZipFile(OUT/HUD,'w',compression=ZIP_DEFLATED) as target:
        for item in source.infolist():
            target.writestr(item, source.read(item))
        for name in ('chat_frame','chat_frame_fill','chat_header'):
            target.write(art/(name+'.png'),'gfx/sabertrials/hud_theme/'+name+'.png')
    sources = {role:tree(OUT/role) for role in ('engine','frontend')}
    write(RECEIPT,dict(installed=installed,sources=sources,hud=sha(OUT/HUD)))
    print('Prepared chat artwork and client sources.')


def wire():
    source = ROOT/'development-source'
    native = source/'client-game/codemp'
    front = OUT/'frontend/codemp'
    engine = OUT/'engine/codemp'
    for role in (front,engine):
        shutil.copyfile(source/'setup/st_setup_catalog.h',role/'ui/st_setup_catalog.h')
        shutil.copyfile(native/'ui/st_chat_layout.h',role/'ui/st_chat_layout.h')
    shutil.copyfile(native/'cgame/cg_st_chat_panel.inc',front/'cgame/cg_st_chat_panel.inc')
    shutil.copyfile(source/'setup/ui_st_chat_preview.inc',front/'ui/ui_st_chat_preview.inc')

    cvars = [line for line in (native/'cgame/cg_xcvar.h').read_text().splitlines()
             if line.startswith(('XCVAR_DEF( st_chatSize,','XCVAR_DEF( st_chatWidth,','XCVAR_DEF( st_chatHeight,'))]
    assert len(cvars)==3
    insert(front/'cgame/cg_xcvar.h','XCVAR_DEF( st_chatSize, "1", NULL, CVAR_ARCHIVE )','\n'.join(cvars))
    insert(front/'cgame/cg_local.h','\tchar\tstring[MAX_SAY_TEXT];','\tchar\tstring[MAX_SAY_TEXT];\n\tchar\tstamp[8];')
    hud = front/'cgame/cg_sabertrials_hud.inc'
    insert(hud,'    qhandle_t track, healthMeter, armorMeter, reticle;',
           '    qhandle_t track, healthMeter, armorMeter, reticle;\n    qhandle_t chatFrame, chatFill, chatHeader;')
    insert(hud,'    ST_HUD_SHADER(reticle, "reticle");','''    ST_HUD_SHADER(reticle, "reticle");
    ST_HUD_SHADER(chatFrame, "chat_frame");
    ST_HUD_SHADER(chatFill, "chat_frame_fill");
    ST_HUD_SHADER(chatHeader, "chat_header");''')

    shutil.copyfile(source/'setup/ui_st_setup_draw.inc',front/'ui/ui_st_setup_draw.inc')
    shutil.copyfile(source/'setup/cl_st_setup.inc',engine/'client/cl_st_setup.inc')


def files(qa=False):
    roles = ('engine','qa' if qa else 'ui','cgame')
    return {build_tools.EXE:build_tools.binary(roles[0]), 'uix86_64.dll':build_tools.binary(roles[1]),
            'cgamex86_64.dll':build_tools.binary(roles[2]), HUD:OUT/HUD}


def install(*tags):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    receipt = read(RECEIPT)
    current = receipt['installed']
    assert all(sha(ROOT/name)==digest for name,digest in current.items())
    sources = files()
    assert not any((home/name).exists() for name in sources if name.endswith('.dll'))
    after = {name:sha(path) for name,path in sources.items()}
    assert after[HUD]==receipt['hud']
    evidence = {}
    for tag in tags:
        path = OUT/tag/'result.json'
        report = read(path)
        assert report['source']==sha(RECEIPT)
        assert report['files']=={name:sha(p) for name,p in files(report['qa']).items()}
        evidence[report['mode']]=sha(path)
    assert set(evidence)=={'wide','tall','production'}
    before = {name:current[name] for name in sources}
    protected = {name:digest for name,digest in current.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'chat-panel-{datetime.now():%Y%m%d-%H%M%S}'
    state = ROOT/'dist/chat-panel-install.json'
    payload = dict(before=before,after=after,protected=protected,backup=str(backup),evidence=evidence,
                   preserved_settings=settings,source_sha256=sha(RECEIPT))
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,state,payload)
    assert all(sha(Path(name))==digest for name,digest in settings.items())
    print('Installed the chat panel update.')


if __name__=='__main__':
    if sys.argv[1]=='prepare':
        prepare()
    elif sys.argv[1]=='install':
        install(*sys.argv[2:])
    else:
        build_tools.build(sys.argv[1])
