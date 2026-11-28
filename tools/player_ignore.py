"""Install player-ignore hooks into a combined Saber Trials client source tree."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    raw = path.read_bytes()
    source = raw.decode("latin1").replace("\r\n", "\n")
    if new in source:
        return
    if source.count(old) != 1:
        raise ValueError(f"Missing unique ignore integration point in {path}: {old!r}")
    source = source.replace(old, new)
    if b"\r\n" in raw:
        source = source.replace("\n", "\r\n")
    path.write_bytes(source.encode("latin1"))


def catalog(path):
    marker = ' {"Private chat with target","messagemode3"'
    replace(path, marker, ' {"Ignore player","ignore","Communication","Aim at a player and press to ignore or unignore their chat",0},\n' + marker)


def engine(client):
    shutil.copyfile(ROOT/'development-source/compatibility/player_ignore.inc', client/'player_ignore.inc')
    replace(client/'client.h', 'void CL_SetCGameTime( void );',
            'void CL_IgnoreRegister();\nvoid CL_IgnoreReset();\nvoid CL_IgnoreNewGameState();\nvoid CL_DrawIgnoreNotice();\nvoid CL_SetCGameTime( void );')
    replace(client/'cl_cgame.cpp', '#include "cl_cgameapi.h"', '#include "cl_cgameapi.h"\n#include "player_ignore.inc"')
    replace(client/'cl_cgame.cpp', 'if ( !strcmp( old, s ) ) {', 'if (index >= CS_PLAYERS && index < CS_PLAYERS + MAX_CLIENTS)\n\t\tCL_IgnorePlayerInfo(index - CS_PLAYERS, s);\n\tif ( !strcmp( old, s ) ) {')
    anchor='Com_DPrintf( "serverCommand: %i : %s\\n", serverCommandNumber, s );'
    replace(client/'cl_cgame.cpp', anchor, 'if (playerIgnore::filtersCommand()) return qfalse;\n\t'+anchor)
    replace(client/'cl_parse.cpp','clc.clientNum = MSG_ReadLong(msg);','clc.clientNum = MSG_ReadLong(msg);\n\tCL_IgnoreNewGameState();')
    replace(client/'cl_main.cpp','void CL_Disconnect( qboolean showMainMenu ) {','void CL_Disconnect( qboolean showMainMenu ) {\n\tCL_IgnoreReset();')
    replace(client/'cl_main.cpp','Cmd_AddCommand ("cmd",','CL_IgnoreRegister();\n\tCmd_AddCommand ("cmd",')
    replace(client/'cl_main.cpp','Cmd_RemoveCommand ("cmd");','Cmd_RemoveCommand("ignore");\n\tCmd_RemoveCommand("unignore");\n\tCmd_RemoveCommand ("cmd");')
    active = 'case CA_ACTIVE:\n\t\t\tCL_CGameRendering( stereoFrame );'
    replace(client/'cl_scrn.cpp',active,active+'\n\t\t\tCL_DrawIgnoreNotice();')
    catalog(client.parent/'ui/st_controls_catalog.h')


def cgame(folder):
    draw = folder/'cg_draw.c'
    source = draw.read_bytes().decode('latin1').replace('\r\n','\n')
    if 'static void CG_TraceCrosshairTarget' not in source:
        start = source.index('static void CG_ScanForCrosshairEntity( void ) {')
        end = source.index('if ( trace.entityNum >= 0 && trace.entityNum < MAX_CLIENTS &&',start) if 'CG_DuelHideEntity(' in source[start:source.index('static void CG_DrawCrosshairNames',start)] else source.index('if (trace.entityNum < MAX_CLIENTS)',start)
        head = source[start:end].rstrip()
        trace = head.replace('static void CG_ScanForCrosshairEntity( void ) {','static void CG_TraceCrosshairTarget( trace_t *result ) {').replace('int\t\t\tcontent;', '')
        visibility = '\n\tif (CG_DuelHideEntity(state)) return -1;' if 'CG_DuelHideEntity(' in source else ''
        query = """
int CG_CurrentAimPlayer( void ) {
    trace_t trace;
    entityState_t *state;
    if (!cg.snap) return -1;
    CG_TraceCrosshairTarget(&trace);
    if (trace.allsolid || trace.startsolid || trace.fraction >= 1.0f ||
        trace.entityNum < 0 || trace.entityNum >= MAX_CLIENTS ||
        trace.entityNum == cg.snap->ps.clientNum || !cg_entities[trace.entityNum].currentValid)
        return -1;
    state = &cg_entities[trace.entityNum].currentState;""" + visibility + """
    if (CG_IsMindTricked(state->trickedentindex, state->trickedentindex2,
            state->trickedentindex3, state->trickedentindex4, cg.snap->ps.clientNum) ||
        (CG_PointContents(trace.endpos, 0) & CONTENTS_FOG)) return -1;
    return trace.entityNum;
}

static void CG_ScanForCrosshairEntity( void ) {
    trace_t trace;
    int content;
    CG_TraceCrosshairTarget(&trace);
"""
        replace(draw, head, trace + '\n\t*result = trace;\n}\n' + query)
    replace(folder/'cg_local.h', 'int CG_CrosshairPlayer( void );', 'int CG_CurrentAimPlayer( void );\nint CG_CrosshairPlayer( void );')
    replace(folder/'cg_main.c', 'int CG_CrosshairPlayer( void ) {', 'int CG_CrosshairPlayer( void ) {\n\tconst char *command = CG_Argv(0);\n\tif (!Q_stricmp(command, "ignore") || !Q_stricmp(command, "unignore")) return CG_CurrentAimPlayer();')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('kind',choices=['engine','cgame','catalog'])
    parser.add_argument('target',type=Path)
    args = parser.parse_args()
    {'engine':engine, 'cgame':cgame,'catalog':catalog}[args.kind](args.target)
