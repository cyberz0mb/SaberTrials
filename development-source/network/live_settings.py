"""Apply current networking fixes to the original and compatibility MP engines."""
from pathlib import Path
import shutil


def update(path, old, new):
    text = path.read_text()
    if new in text:
        return
    if text.count(old) != 1:
        raise ValueError(f"Missing adaptive network insertion point in {path}")
    path.write_text(text.replace(old, new))


def stage(tree):
    source = Path(__file__).resolve().parent
    client = tree / "codemp/client"
    for name in ("cl_st_network.inc", "st_network.h"):
        dest = client / name
        if dest.read_bytes() != (source / name).read_bytes():
            shutil.copyfile(source / name, dest)

    # Cvar_Set2 sees mod and engine maintenance writes as well as actual edits.
    # Surrender ownership only after the unchanged/protected-value checks.
    cvar = tree / "codemp/qcommon/cvar.cpp"
    hook = "    extern void CL_NetExternalSet(const cvar_t*);\n    CL_NetExternalSet(var);"
    text = cvar.read_text()
    free = "Cvar_FreeString (var->string);\t// free the old value string"
    block = "#ifndef DEDICATED\n" + hook + "\n#endif"
    if block + "\n\t" + free not in text:
        if text.count(block) != 1 or text.count(free) != 1:
            raise ValueError("Missing cvar ownership hook")
        cvar.write_text(text.replace(block + "\n", "").replace(free, block + "\n\t" + free))

    transmit = "CL_Netchan_Transmit (&clc.netchan, &buf);"
    menu_font = 'cls.menuFont = re->RegisterFont( "ocr_a" );'
    update(client / "cl_main.cpp", menu_font, menu_font + '\n\tnetHudFont = re->RegisterFont("arialnb");')
    update(client / "cl_input.cpp", transmit,
           transmit + "\n\textern void CL_NetCommandPacketSent();\n\tCL_NetCommandPacketSent();")
    anchor = "auto value=SS_Get(s.name);"
    update(client / "cl_st_setup.inc", anchor, anchor + '''
  if(s.tab==4 && SS_Get("st_netMode")=="2" && Cvar_VariableIntegerValue("st_netMode")==2 &&
     (!Q_stricmp(s.name,"rate") || !Q_stricmp(s.name,"cl_maxpackets") || !Q_stricmp(s.name,"snaps") ||
      !Q_stricmp(s.name,"cl_timeNudge") || !Q_stricmp(s.name,"cl_packetdup")))
      value=Cvar_VariableString(s.name);''')
