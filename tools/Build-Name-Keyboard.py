"""Build Profile's on-screen name keyboard on the installed gamepad client."""
from datetime import datetime
from importlib import import_module
import shutil
import sys

sys.dont_write_bytecode = True
baseline = import_module('Build-Gamepad-Menus')
builder, ROOT = baseline.builder, baseline.ROOT
OUT = ROOT/'dist/name-keyboard-01'
RECEIPT = OUT/'source-receipt.json'
builder.OUT, builder.RECEIPT = OUT, RECEIPT
sha, read, write, tree = baseline.sha, baseline.read, baseline.write, baseline.tree


def prepare(refresh=False):
    prior = read(ROOT/'dist/gamepad-menus-install.json')
    installed = {**prior['protected'], **prior['after']}
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed'
    base = read(baseline.RECEIPT)
    assert sha(baseline.RECEIPT)==prior['source_sha256']
    for role in ('engine','frontend'):
        assert tree(baseline.OUT/role)==base['sources'][role], role+' source changed'
        if not refresh:
            shutil.copytree(baseline.OUT/role,OUT/role,dirs_exist_ok=True)
    source = ROOT/'development-source'
    engine, ui = OUT/'engine', OUT/'frontend/codemp/ui'
    if not refresh:
        shutil.copyfile(source/'controls/cl_st_pad_menu.inc',engine/'codemp/client/cl_st_pad_menu.inc')
        shutil.copyfile(source/'controls/st_controller.inc',engine/'shared/sdl/st_controller.inc')
    shutil.copyfile(source/'profile/ui_st_name_keyboard.inc',ui/'ui_st_name_keyboard.inc')
    # Apply only the keyboard changes. The installed Profile has additional DLC integration.
    replacements = {
      'ui_st_profile.inc': (
        ('static std::string SPUI_Var', '#include "ui_st_name_keyboard.inc"\nstatic std::string SPUI_Var'),
        ('if(!spui.built)SPUI_BuildCatalog();', 'SPN_Close(false);\n if(!spui.built)SPUI_BuildCatalog();'),
        ('if(!SPUI_IsMenu()){spui.active=false;return;}', 'if(!SPUI_IsMenu()){SPN_Close(false);spui.active=false;return;}'),
        ('if(spui.modal)item->window.flags', 'if(spui.modal||spName.active)item->window.flags'),
        ('if(!spui.active)return;\n spui.mouse=true;', 'if(!spui.active)return;\n if(spName.active){spName.focusNavigation=false;return;}\n spui.mouse=true;'),
        ('if(!spui.active)SPUI_Start();if(!down)', 'if(!spui.active)SPUI_Start();\n if(spName.active){SPN_Key(key,down);return qtrue;}\n if(!down)'),
        ('else if(op=="assertdirty")', 'else if(op=="assertname"){if(spui.draft.value.name!=a)fail("staged name");}\n else if(op=="assertkeyboard"){if(spName.active!=(a=="1"))fail("virtual keyboard state");}\n else if(op=="assertdirty")'),
      ),
      'ui_st_profile_actions.inc': (
        ('static void SPUI_Click(int id,int arg){', 'static void SPUI_Click(int id,int arg){\n if(id==102||(id==101&&trap->Cvar_VariableValue("st_uiPadClick"))){SPN_Open();return;}'),
      ),
      'ui_st_profile_draw.inc': (
        ('if(spui.wide&&UI_TrueJediEnabled())SPUI_Button(276,identityY,118,22,',
         'SPUI_Button(275,identityY,spui.wide&&UI_TrueJediEnabled()?30:96,22,spui.wide&&UI_TrueJediEnabled()?"Keys":"Keyboard",102);\n'
         ' if(spui.wide&&UI_TrueJediEnabled())SPUI_Button(310,identityY,86,22,'),
        ('if(!spui.modal){if(spui.mouse)SPUI_Mouse();SPUI_Tooltip();}',
         'if(spName.active){spui.hits.clear();SPN_Draw();}\n else if(!spui.modal){if(spui.mouse)SPUI_Mouse();SPUI_Tooltip();}'),
      ),
    }
    for name, edits in replacements.items():
        path = ui/name
        data = (baseline.OUT/'frontend/codemp/ui'/name).read_text(encoding='utf8')
        for before, after in edits:
            assert data.count(before)==1, (name,before)
            data = data.replace(before,after)
        path.write_text(data,encoding='utf8')
    write(RECEIPT,dict(installed=installed,sources={role:tree(OUT/role) for role in ('engine','frontend')}))
    print('Prepared Profile name keyboard.',flush=True)


def install(tag):
    helper = import_module('Install-Profile-Browser')
    helper.stopped()
    home, settings = helper.settings()
    installed = read(RECEIPT)['installed']
    assert all(sha(ROOT/name)==digest for name,digest in installed.items()), 'Installed client changed during testing'
    sources = baseline.files()
    assert not (home/'uix86_64.dll').exists(), 'Profile has a UI module override'
    evidence = OUT/tag/'result.json'
    assert read(evidence)==dict(source=sha(RECEIPT),files={name:sha(path) for name,path in baseline.files(qa=True).items()})
    after = {name:sha(path) for name,path in sources.items()}
    for role in ('engine','engine-qa','ui','qa'):
        assert read(OUT/f'build-{role}.json')==dict(source=sha(RECEIPT),sha256=sha(builder.binary(role)))
    before = {name:installed[name] for name in sources}
    protected = {name:digest for name,digest in installed.items() if name not in sources}
    backup = ROOT/'dist/backups'/f'name-keyboard-{datetime.now():%Y%m%d-%H%M%S}'
    payload = dict(before=before,after=after,protected=protected,backup=str(backup),source_sha256=sha(RECEIPT),
                   evidence=sha(evidence),preserved_settings=settings)
    import_module('Install-Handedness').install_transaction(ROOT,sources,before,after,protected,backup,
        ROOT/'dist/name-keyboard-install.json',payload)
    print('Installed Profile name keyboard.')


if __name__=='__main__':
    operation = sys.argv[1]
    if operation in ('prepare','refresh'):
        prepare(operation=='refresh')
    elif operation=='install':
        install(sys.argv[2])
    else:
        builder.build(operation)
