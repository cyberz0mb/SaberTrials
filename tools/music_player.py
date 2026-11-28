"""Stage the client music feature and compile its Windows desktop companion."""
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "development-source/music-player"
OUT = ROOT / "dist/music-player/release"
PLAYER = OUT / "SaberTrials Music.exe"


def stage_bridge(tree):
    client = tree / "codemp/client"
    shutil.copyfile(SOURCE / "cl_music.inc", client / "cl_music.inc")
    main = client / "cl_main.cpp"
    original = main.read_text()
    result = original
    for anchor, addition in (
        ('#include "cl_st_network.inc"', '#include "cl_music.inc"'),
        ('CL_InitInput ();', 'stmusic::init();'),
        ('CL_BrowserMasterFrame();', 'stmusic::frame();'),
        ('CL_ShutdownInput();', 'stmusic::shutdown();'),
    ):
        if addition in result:
            continue
        if result.count(anchor) != 1:
            raise RuntimeError("Unexpected client source around " + anchor)
        result = result.replace(anchor, anchor + "\n" + addition)
    if result != original:
        main.write_text(result)
    edits = [
        (client / "cl_uiapi.cpp", "intptr_t CL_UISystemCalls( intptr_t *args ) {",
         "qhandle_t CL_RegisterMusicUIShader(const char *);\n\nintptr_t CL_UISystemCalls( intptr_t *args ) {"),
        (client / "cl_uiapi.cpp", "case UI_R_REGISTERSHADERNOMIP:\n\t\treturn re->RegisterShaderNoMip( (const char *)VMA(1) );",
         "case UI_R_REGISTERSHADERNOMIP:\n\t\treturn CL_RegisterMusicUIShader( (const char *)VMA(1) );"),
        (client / "cl_uiapi.cpp", "uii.R_RegisterShaderNoMip\t\t\t\t= re->RegisterShaderNoMip;",
         "extern qhandle_t CL_RegisterMusicUIShader(const char *);\n\t\tuii.R_RegisterShaderNoMip = CL_RegisterMusicUIShader;"),
        (client / "foreign_art.inc", 'static_assert(ARRAY_LEN(personalArt) <= 64, "reserved personal UI texture slots");',
         'static_assert(ARRAY_LEN(personalArt) <= 63, "slot 223 is reserved for music artwork");'),
        (client / "cl_st_menu_font.inc", "    CL_ResetPersonalArt();",
         "    CL_ResetPersonalArt();\n    extern void CL_ResetMusicShader();\n    CL_ResetMusicShader();"),
    ]
    for path, anchor, replacement in edits:
        body = path.read_text()
        if replacement not in body:
            if body.count(anchor) != 1:
                raise RuntimeError("Unexpected music artwork integration point in " + path.name)
            path.write_text(body.replace(anchor, replacement))


def menu():
    return runpy.run_path(str(SOURCE / "menu/overlay.py"))


def stage_engine(tree):
    stage_bridge(tree)
    overlay = menu()
    overlay["stage_catalog"](tree)
    overlay["stage_resources"](tree)
    personal = tree / "codemp/client/full_ui.inc"
    source = personal.read_text()
    hook = "    if(!CL_PersonalPauseActive())return false;"
    opening_music = """    if (!CL_PersonalPauseActive()) {
        if (CL_TrialsGame() || cls.state != CA_ACTIVE || Q_stricmp(Cmd_Argv(0), "ui_openmenu") ||
            Q_stricmp(Cmd_Argv(1), "st_music_player") || !PersonalLoad()) return false;
        personalShown = true;
    }"""
    if opening_music not in source:
        if source.count(hook) != 1:
            raise RuntimeError("Unexpected personal menu console handler")
        personal.write_text(source.replace(hook, opening_music))


def stage_frontend(tree):
    overlay = menu()
    overlay["stage_catalog"](tree)
    overlay["stage_ui"](tree)


def windows_tools():
    pf86 = Path(os.environ["ProgramFiles(x86)"])
    fw = pf86 / "Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8"
    locator = pf86 / "Microsoft Visual Studio/Installer/vswhere.exe"
    compilers = subprocess.check_output([str(locator), "-latest", "-products", "*", "-requires",
        "Microsoft.Component.MSBuild", "-find", r"MSBuild\**\Bin\Roslyn\csc.exe"], text=True).splitlines()
    if not compilers:
        raise RuntimeError("Install Visual Studio's MSBuild and C# compiler.")
    sdk = pf86 / "Windows Kits/10/UnionMetadata"
    metadata = max((v for v in sdk.iterdir() if v.name[:1].isdigit() and (v / "Windows.winmd").exists()),
                   key=lambda v: tuple(map(int, v.name.split(".")))) / "Windows.winmd"
    runtime = next((Path(os.environ["WINDIR"]) / "Microsoft.NET/assembly/GAC_MSIL/System.Runtime.WindowsRuntime").glob("*/System.Runtime.WindowsRuntime.dll"))
    return Path(compilers[0]), fw, metadata, runtime


def build_desktop():
    compiler, fw, metadata, runtime = windows_tools()
    OUT.mkdir(parents=True, exist_ok=True)
    references = ["mscorlib", "System", "System.Core", "System.Xaml", "System.Xml", "System.Xml.Linq",
                  "System.Runtime.Serialization", "PresentationFramework", "PresentationCore", "WindowsBase",
                  "Facades/System.Runtime", "Facades/System.Runtime.InteropServices.WindowsRuntime",
                  "Facades/System.ObjectModel"]
    resources = {SOURCE / "MainWindow.xaml": "MainWindow.xaml",
        ROOT / "assets/runtime-packages/main/ui/assets/sabertrials/main/emblem.png": "Emblem.png",
        ROOT / "assets/runtime-packages/rich/ui/assets/sabertrials/rich/wordmark.png": "Wordmark.png"}
    subprocess.run([str(compiler), "/nologo", "/noconfig", "/nostdlib+", "/optimize+", "/deterministic+",
        "/target:winexe", "/platform:x64", "/langversion:7.3", "/main:SaberTrials.Music.PlayerHost",
        "/out:" + str(PLAYER), "/win32icon:" + str(ROOT / "assets/branding/SaberTrials.ico"),
        *["/reference:" + str(fw / (r + ".dll")) for r in references],
        "/reference:" + str(metadata), "/reference:" + str(runtime),
        *["/resource:" + str(path) + ",SaberTrials.Music." + alias for path, alias in resources.items()],
        *[str(SOURCE / f) for f in ("MainWindow.cs", "MusicModel.cs", "TrackArtwork.cs", "AppVolume.cs", "PlayerHost.cs")]], check=True)


if __name__ == "__main__":
    build_desktop()
