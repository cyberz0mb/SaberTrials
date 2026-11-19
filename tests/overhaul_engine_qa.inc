// Compiled only by Build-Overhaul.py --qa, never into the delivered client.
static void ST_EngineQA_f( void ) {
    const char *operation = Cmd_Argv(1);
    if (!Q_stricmp(operation, "f8")) {
        CL_KeyEvent(A_F8, qtrue, Sys_Milliseconds());
        CL_KeyEvent(A_F8, qfalse, Sys_Milliseconds());
    } else if (!Q_stricmp(operation, "type")) {
        const char *text = Cmd_Argv(2);
        while (*text) CL_CharEvent(*text++);
    } else if (!Q_stricmp(operation, "enter")) {
        CL_KeyEvent(A_ENTER, qtrue, Sys_Milliseconds());
        CL_KeyEvent(A_ENTER, qfalse, Sys_Milliseconds());
    }
}
