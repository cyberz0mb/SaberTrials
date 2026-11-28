"""Build the MP client and its matching native Setup menu from the installed release sources."""
import argparse
import hashlib
import json
import runpy
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "net"
FEATURE = ROOT / "development-source/network"
BASE = {"engine": DIST / "combat-controls-01/engine", "frontend": DIST / "match-rules-01/frontend"}
TARGET = {"engine": "openjk.x86_64", "frontend": "uix86_64"}
FLAGS = ("BuildMPEngine", "BuildMPDed", "BuildMPGame", "BuildMPCGame", "BuildMPUI",
         "BuildMPRdVanilla", "BuildMPRend2", "BuildMPRdVulkan", "BuildSPEngine", "BuildSPGame", "BuildSPRdVanilla")


def patch(role, name, edits):
    # Always patch the baseline. Re-running after editing the feature is safe.
    source = (BASE[role] / "codemp" / name).read_text()
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f"{name}: expected one occurrence of {old!r}")
        source = source.replace(old, new)
    path = OUT / role / "codemp" / name
    if path.read_text() != source:
        path.write_text(source)


def prepare():
    for role in BASE:
        tree = OUT / role
        if not tree.exists():
            shutil.copytree(BASE[role], tree)
        anchor = ' {"rate","Rate","Connection"'
        rows = (' {"st_netMode","Optimization","Connection","Auto adapts after measuring the connection.",'
                '"2=Auto (recommended)|1=Manual|0=Off","2",4,2,0,0,CVAR_ARCHIVE,0,2},\n'
                ' {"st_netStats","Network statistics","Connection","Show ping, jitter, incoming loss and live settings.",'
                '"0=Off|1=On","0",4,1,0,0,CVAR_ARCHIVE,0,1},\n')
        patch(role, "ui/st_setup_catalog.h", [(anchor, rows + anchor),
              ('CVAR_ARCHIVE,15,125}', 'CVAR_ARCHIVE,20,1000}')])

    client = OUT / "engine/codemp/client"
    for name in ("st_network.h", "cl_st_network.inc"):
        shutil.copyfile(FEATURE / name, client / name)
    def engine(name, edits):
        patch("engine", name, edits)
    decl = "void CL_SetCGameTime( void );"
    engine("client/client.h", [(decl, decl + """
bool CL_NetPacing(qboolean& ready);
void CL_NetPolicyChanged();
void CL_NetSnapshot(bool matched);
void CL_NetDraw();
const char* CL_NetPersonal(const cvar_t* var);
""")])
    anchor = 'Cmd_AddCommand ("cmd",'
    engine("client/cl_main.cpp", [
        ("clientStatic_t\t\tcls;", 'clientStatic_t\t\tcls;\n#include "cl_st_network.inc"'),
        (anchor, "netInit();\n\t" + anchor),
        ('Cmd_RemoveCommand ("disconnect");', 'Cmd_RemoveCommand("st_netStatus");\n\tCmd_RemoveCommand ("disconnect");'),
        ("void CL_ClearState (void) {", "void CL_ClearState (void) {\n\tresetNet();"),
        ("\tCL_CheckUserinfo();", "\tnetFrame();\n\tCL_CheckUserinfo();"),
        ("\tCL_ParseServerMessage( msg );", "\tnetMessage(clc.serverMessageSequence);\n\tCL_ParseServerMessage( msg );")])
    engine("client/cl_scrn.cpp", [('if (!Cvar_VariableIntegerValue("st_photoMode")) SCR_DrawDemoRecording();',
        'CL_NetDraw();\n\t\t\tif (!Cvar_VariableIntegerValue("st_photoMode")) SCR_DrawDemoRecording();')])
    engine("client/cl_input.cpp", [("// check for exceeding cl_maxpackets",
        "qboolean ready;\n\tif (CL_NetPacing(ready)) return ready;\n\n\t// check for exceeding cl_maxpackets")])
    engine("client/cl_cgame.cpp", [("if ( index == CS_SYSTEMINFO ) {", "if (index == CS_SERVERINFO || index == CS_SYSTEMINFO) CL_NetPolicyChanged();\n\tif ( index == CS_SYSTEMINFO ) {")])
    engine("client/cl_parse.cpp", [("// save the frame off in the backup array",
        "CL_NetSnapshot(i < PACKET_BACKUP && cl.outPackets[packetNum].p_realtime > 0);\n\t// save the frame off in the backup array")])
    # Native writeconfig, the automatic cfg writer and both personal-config
    # editors must agree even if the game exits during an adaptive trial.
    engine("qcommon/cvar.cpp", [
        ("value = Cvar_Validate(var, value, qtrue);", """value = Cvar_Validate(var, value, qtrue);
#ifndef DEDICATED
    extern void CL_NetExternalSet(const cvar_t*);
    CL_NetExternalSet(var);
#endif"""),
        ("if( strlen( var->name ) + strlen( var->string ) + 10 > sizeof( buffer ) )", """const char* saved = var->string;
#ifndef DEDICATED
                extern const char* CL_NetPersonal(const cvar_t*);
                saved = CL_NetPersonal(var);
#endif
                if( strlen( var->name ) + strlen( saved ) + 10 > sizeof( buffer ) )"""),
        ("!strcmp( var->string, var->resetString )", "!strcmp( saved, var->resetString )"),
        ('var->name, var->string);\n\t\t\t}\n\t\t\tFS_Write', 'var->name, saved);\n\t\t\t}\n\t\t\tFS_Write')])
    saved = ("v->latchedString?v->latchedString:v->string", "v->latchedString?v->latchedString:CL_NetPersonal(v)")
    engine("client/cl_st_controls.inc", [saved])
    engine("client/cl_st_setup.inc", [saved, ("if(s.dependency==1", """if(s.tab==4 && SS_Get("st_netMode")!="1" &&
    (!Q_stricmp(s.name,"rate") || !Q_stricmp(s.name,"snaps") || !Q_stricmp(s.name,"cl_maxpackets") ||
     !Q_stricmp(s.name,"cl_packetdup") || !Q_stricmp(s.name,"cl_timeNudge"))) return "Choose Manual to edit connection values.";
 if(s.dependency==1""")])
    patch("frontend", "cgame/cg_servercmds.c", [
        ("// synchronise our expected snaps/sec with the server's framerate", """// Older engines delegate snapshot selection to cgame. The adaptive client
    // owns the player's requested value in Manual, Off and Auto modes.
    char networkMode[16];
    trap->Cvar_VariableStringBuffer("st_netMode", networkMode, sizeof(networkMode));
    // synchronise our expected snaps/sec with the server's framerate"""),
        ('if ( i )\n\t\ttrap->Cvar_Set( "snaps",', 'if ( i && !networkMode[0] )\n\t\ttrap->Cvar_Set( "snaps",')])


    runpy.run_path(str(FEATURE / "live_settings.py"))["stage"](OUT/"engine")


def build():
    prepare()
    for role, target in TARGET.items():
        folder = OUT / ("b-" + role)
        options = ("BuildMPEngine",) if role == "engine" else ("BuildMPUI", "BuildMPCGame")
        subprocess.run(["cmake", "-S", OUT / role, "-B", folder, "-G", "Visual Studio 18 2026", "-A", "x64",
                        f"-DST_DEPS={DIST / 'handedness-baseline-06/deps'}", "-DST_STAFF_QA=OFF",
                        *[f"-D{f}={'ON' if f in options else 'OFF'}" for f in FLAGS]], check=True)
        targets = [target] if role == "engine" else [target, "cgamex86_64"]
        subprocess.run(["cmake", "--build", folder, "--config", "Release", "--parallel", "1", "--target", *targets], check=True)


def install():
    import importlib
    from datetime import datetime
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    files = {"client/SaberTrials.x86_64.exe": OUT / "b-engine/Release/openjk.x86_64.exe",
             "uix86_64.dll": OUT / "b-frontend/Release/uix86_64.dll",
             "cgamex86_64.dll": OUT / "b-frontend/Release/cgamex86_64.dll"}
    baseline = [BASE["engine"].parent / "build-engine/Release/openjk.x86_64.exe",
                BASE["frontend"].parent / "build-frontend/Release/uix86_64.dll",
                BASE["frontend"].parent / "build-frontend/Release/cgamex86_64.dll"]
    before = {name: sha(ROOT / name) for name in files}
    after = {name: sha(path) for name, path in files.items()}
    if before == after:
        return
    original = {name: sha(path) for name, path in zip(files, baseline)}
    previous = sorted(DIST.glob("network-install-*.json"), reverse=True)
    last = json.loads(previous[0].read_text()) if previous else {}
    if before != original and (before != last.get("after") or original != last.get("baseline", last.get("before"))):
        raise RuntimeError("Installed release differs from the selected source baseline")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = DIST / "backups" / ("network-" + stamp)
    importlib.import_module("Install-Handedness").install_transaction(
        ROOT, files, before, after, {}, backup, DIST / ("network-install-" + stamp + ".json"),
        dict(before=before, after=after, baseline=original, backup=str(backup)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "build", "install"))
    args = parser.parse_args()
    {"prepare": prepare, "build": build, "install": install}[args.action]()
