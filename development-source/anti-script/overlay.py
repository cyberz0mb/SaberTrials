"""Apply the multiplayer hooks to a staged OpenJK tree. Fail on ambiguous anchors."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def apply(source):
    mp = Path(source) / "codemp"
    target = mp / "antiscript"
    target.mkdir(exist_ok=True)
    for p in HERE.iterdir():
        if p.suffix in {".cpp", ".h", ".inc"}:
            shutil.copyfile(p, target / p.name)

    def edit(file, old, new):
        path = mp / file
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise RuntimeError(f"{file}: expected a single occurrence of {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")

    def client(code):
        return "\n#ifndef DEDICATED\n" + code + "\n#endif\n"

    f = "qcommon/cmd.cpp"
    edit(f, "typedef struct cmd_s", client('#include "cmd_tags.inc"') + "typedef struct cmd_s")
    edit(f, "cmd_wait = 1;\n\t}\n}", "cmd_wait = 1;\n\t}" +
         client("if (cmd_wait > 0 && CL_ASCollecting()) CL_ASWait(asExecuting);") + "}")
    edit(f, "cmd_text.cursize += l;", client("if (CL_ASCollecting()) asTags.append(cmd_text.cursize,l,asAdding);") + "\tcmd_text.cursize += l;")
    edit(f, "cmd_text.cursize += len;", client("if (CL_ASCollecting()) asTags.prepend(len,asInserting);") + "\tcmd_text.cursize += len;")
    edit(f, "if (i == cmd_text.cursize)", client("uint32_t previousOrigin = asExecuting;\n"
         "asExecuting = CL_ASCollecting() ? asTags.take(i,i+(i<cmd_text.cursize)) : 0;") + "\t\tif (i == cmd_text.cursize)")
    edit(f, "Cmd_ExecuteString (line);", "Cmd_ExecuteString (line);" + client("asExecuting = previousOrigin;"))
    for old, arg in [('Cbuf_InsertText (f.c);', 'f.c'), ('Cbuf_InsertText( va("%s\\n", v ) );', 'va("%s\\n", v )')]:
        edit(f, old, f"\n#ifdef DEDICATED\n\t{old}\n#else\n\tCbuf_ASScript({arg});\n#endif")
    edit(f, "cmd->function ();", client("if (CL_ASCollecting()) CL_ASAction(asExecuting,cmd->name);") + "\t\t\t\tcmd->function ();")
    f = "client/cl_keys.cpp"
    text = (mp / f).read_text(encoding="utf-8")
    start = text.index("void CL_ParseBinding(")
    stop = text.index("\n}", start)+2
    body = text[start:stop]
    bound = body.replace("while( 1 )", "const uint32_t origin = Cbuf_ASOrigin();\n\twhile( 1 )")
    for arg in ("cmd", "p", "icc->conCommand", '"\\n"'):
        bound = bound.replace(f"Cbuf_AddText( {arg} );", f"Cbuf_ASBound({arg},origin);")
    if bound == body or "Cbuf_AddText(" in bound:
        raise ValueError("Unexpected key binding implementation")
    edit(f, body, bound)
    edit("client/cl_input.cpp","cl.cmds[cmdNum] = CL_CreateCmd();","cl.cmds[cmdNum] = CL_CreateCmd();\n\tCL_ASFrame();")
    for f in ("cl_main.cpp","cl_parse.cpp","cl_cgame.cpp"):
        edit("client/"+f, "CL_StaffReset();", "CL_StaffReset(); CL_ASReset();")
    for f in ("cl_input.cpp","cl_keys.cpp","cl_main.cpp","cl_parse.cpp","cl_cgame.cpp"):
        path = mp/"client"/f
        path.write_text('#include "client_trace.h"\n'+path.read_text(encoding="utf-8"), encoding="utf-8")

    f = "server/sv_client.cpp"
    edit(f,"GVM_ClientBegin( client - svs.clients );","if (!SV_ASDeferBegin(client - svs.clients)) GVM_ClientBegin( client - svs.clients );")
    edit(f,"if (SV_AccountCommand((int)(cl-svs.clients))) return;",
         "if (SV_AccountCommand((int)(cl-svs.clients))) { SV_ASAccountChanged(cl-svs.clients); return; }\n"
         "\tif (SV_ASCommand(cl-svs.clients)) return;")
    edit(f,"GVM_ClientCommand( cl - svs.clients );","if (SV_ASAllowed(cl-svs.clients)) GVM_ClientCommand( cl - svs.clients );")
    edit(f,"cl->lastUsercmd = *cmd;", "if (!SV_ASAllowed(cl-svs.clients)) return;\n\tcl->lastUsercmd = *cmd;")
    edit(f,"GVM_ClientThink( cl - svs.clients, NULL );",
         "GVM_ClientThink( cl - svs.clients, NULL );\n\tif (cl->state == CS_ACTIVE) SV_ASSample(cl-svs.clients,*cmd);")
    edit(f,"!com_cl_running->integer &&\n\t\tcl->state >= CS_ACTIVE",
         'Q_strncmp(s,"st_as1 ",7) && !com_cl_running->integer &&\n\t\tcl->state >= CS_ACTIVE')
    f = "server/sv_gameapi.cpp"
    edit(f,"SV_AccountFrame();","SV_AccountFrame(SV_ASAllowed);")
    edit(f,"SV_StaffFrame();", "SV_StaffFrame();\n    SV_ASFrame();")
    edit(f,"SV_StaffConnect(clientNum,isBot!=qfalse);","SV_ASReset(clientNum);\n    SV_StaffConnect(clientNum,isBot!=qfalse);")
    edit(f,"SV_StaffDisconnect(clientNum);","SV_ASReset(clientNum);\n    SV_StaffDisconnect(clientNum);")
    edit("server/sv_ccmds.cpp",'Cmd_AddCommand("accountserver",','SV_ASInit();\n\tCmd_AddCommand("accountserver",')
    for f in ("sv_client.cpp","sv_gameapi.cpp","sv_ccmds.cpp"):
        path = mp/"server"/f
        path.write_text('#include "server_hooks.h"\n'+path.read_text(encoding="utf-8"), encoding="utf-8")

    with (mp.parent/"CMakeLists.txt").open("a", encoding="utf-8") as cmake:
        cmake.write("""
foreach(st_target ${MPEngine} ${MPDed})
  if(TARGET ${st_target})
    target_sources(${st_target} PRIVATE "${MPDir}/antiscript/detection.cpp" "${MPDir}/antiscript/ledger.cpp" "${MPDir}/antiscript/server_hooks.cpp")
    target_include_directories(${st_target} PRIVATE "${MPDir}/antiscript")
  endif()
endforeach()
if(TARGET ${MPEngine})
  target_sources(${MPEngine} PRIVATE "${MPDir}/antiscript/client_trace.cpp")
endif()
""")
