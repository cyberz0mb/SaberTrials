// Input injection in the isolated QA client only.
static qboolean ST_PhotoEngineQA(void) {
    if (!Q_stricmp(Cmd_Argv(1),"key")) {
        CL_KeyEvent(atoi(Cmd_Argv(2)),atoi(Cmd_Argv(3)) ? qtrue : qfalse,Sys_Milliseconds());
    } else if (!Q_stricmp(Cmd_Argv(1),"mouse")) {
        CL_MouseEvent(atoi(Cmd_Argv(2)),atoi(Cmd_Argv(3)),Sys_Milliseconds());
    } else return qfalse;
    return qtrue;
}
