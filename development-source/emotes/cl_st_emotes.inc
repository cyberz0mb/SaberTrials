#include "qcommon/st_emotes.h"

static bool stWheelActive;
static int stWheelKey = -1;
static unsigned stWheelPressedAt;
static bool stWheelReleased;
static bool stWheelConsumed[MAX_KEYS];

static bool CL_EmotePhotoMode() { return Cvar_VariableIntegerValue("st_photoMode") != 0; }
static void CL_EmotePlayId(const char* id);

static void CL_EmoteClose(bool confirm) {
    if (!stWheelActive) return;
    stWheelActive = false;
    stWheelKey = -1;
    if (confirm) {
        Cvar_Set("st_emoteSelection","");
        UIVM_KeyEvent(A_ENTER,qtrue);
        CL_EmotePlayId(Cvar_VariableString("st_emoteSelection"));
        Cvar_Set("st_emoteSelection","");
    }
    Cvar_Set("st_emoteWheelOpen","0");
}

static void CL_EmotePlayId(const char* id) {
    if (!id || !*id || cls.state != CA_ACTIVE || clc.demoplaying || CL_EmotePhotoMode()) return;
    const auto clips = stemote::catalog(Cvar_VariableStringBuffer);
    const auto* clip = stemote::find(clips,id);
    const char* offer = cl.gameState.stringData+cl.gameState.stringOffsets[stemote::catalogString];
    if (clip && stemote::offered(offer,*clip) && (!clip->signature || !cl_connectedToPureServer)) {
        CL_AddReliableCommand(va("st_emote %s",clip->id.c_str()),qfalse);
        return;
    }
    if (!*offer && clip && clip->stock >= 0) {
        const char* commands[] = {"taunt","bow","meditate","flourish","gloat"};
        const int mode = atoi(Info_ValueForKey(cl.gameState.stringData+cl.gameState.stringOffsets[CS_SERVERINFO],"g_gametype"));
        if (clip == &clips.front() || mode == GT_DUEL || mode == GT_POWERDUEL) {
            Cmd_ExecuteString(commands[clip-clips.data()]);
            return;
        }
    }
    Com_Printf("Emote unavailable on this server.\n");
}

static void CL_EmotePlay() {
    if (Cmd_Argc() == 2) CL_EmotePlayId(Cmd_Argv(1));
}

static bool CL_EmoteWheelBinding(int key) {
    const char* binding = Key_GetBinding(key);
    return binding && !Q_stricmp(binding,"+st_emotewheel");
}

bool CL_EmoteWheelActive() {
    if (stWheelActive && (cls.state != CA_ACTIVE || !cls.uiStarted || Key_GetCatcher() || CL_EmotePhotoMode()))
        CL_EmoteClose(false);
    return stWheelActive;
}

static bool CL_EmoteKey(int key, qboolean down, unsigned time) {
    if (!CL_EmoteWheelActive() && key >= 0 && key < MAX_KEYS && stWheelConsumed[key]) {
        stWheelConsumed[key] = down != qfalse;
        return true;
    }
    if (!stWheelActive && !(cls.state == CA_ACTIVE && !clc.demoplaying && cls.uiStarted &&
        !Key_GetCatcher() && !CL_EmotePhotoMode() && down && CL_EmoteWheelBinding(key))) return false;
    if (!stWheelActive) {
        stWheelActive = true;
        stWheelKey = key;
        stWheelConsumed[key] = true;
        stWheelPressedAt = time;
        stWheelReleased = false;
        Cvar_Set("st_emoteWheelOpen","1");
        UIVM_KeyEvent(A_HOME,qtrue);
        return true;
    }
    if (key == stWheelKey) {
        const bool toggle = Cvar_VariableIntegerValue("st_emoteWheelToggle") != 0;
        stWheelConsumed[key] = down != qfalse;
        if (!down && !toggle) CL_EmoteClose(time != 0 && time >= stWheelPressedAt);
        if (!down && toggle) stWheelReleased = true;
        if (down && toggle && stWheelReleased) CL_EmoteClose(false);
        return true;
    }
    if (key < 0 || key >= MAX_KEYS) return false;
    if (!down) {
        const bool consumed = stWheelConsumed[key];
        stWheelConsumed[key] = false;
        return consumed;
    }
    if (Key_IsDown(key)) return false;
    const bool choice = (key >= A_1 && key <= A_8) || (key >= A_JOY9 && key <= A_JOY14) ||
        key == A_CURSOR_UP || key == A_CURSOR_DOWN || key == A_CURSOR_LEFT || key == A_CURSOR_RIGHT ||
        key == A_MWHEELUP || key == A_MWHEELDOWN;
    if (!choice && key != A_ESCAPE && key != A_MOUSE2 && key != A_ENTER && key != A_MOUSE1) return false;
    stWheelConsumed[key] = true;
    if (key == A_ESCAPE || key == A_MOUSE2) CL_EmoteClose(false);
    else if (key == A_ENTER || key == A_MOUSE1) CL_EmoteClose(true);
    else UIVM_KeyEvent(key,qtrue);
    return true;
}

static bool CL_EmotePadButton(int button,qboolean down,unsigned time) {
    if (button < 0 || button >= 18) return false;
    const int key = A_JOY0+button;
    if (key == stWheelKey || (!down && stWheelConsumed[key]) ||
        (down && !stWheelActive && CL_EmoteWheelBinding(key))) return CL_EmoteKey(key,down,time);
    if (!CL_EmoteWheelActive() || !down || Key_IsDown(key)) return false;
    const int accept = Cvar_VariableIntegerValue("st_controllerMenuLayout")==1 ? 1 : 0;
    if (button == accept || button == 1-accept || button == 6) {
        stWheelConsumed[key] = true;
        CL_EmoteClose(button == accept);
        return true;
    }
    return CL_EmoteKey(key,down,time);
}

static void CL_EmoteUnusedCommand() {}

void CL_GamepadButtonEvent(int button,qboolean down,unsigned time);

static void CL_EmoteInputQA() {
    if (!Cvar_VariableIntegerValue("developer") || Cmd_Argc() != 3) return;
    const int key = Key_StringToKeynum(Cmd_Argv(1));
    const qboolean down = atoi(Cmd_Argv(2)) ? qtrue : qfalse;
    if (key >= A_JOY0 && key <= A_JOY17) CL_GamepadButtonEvent(key-A_JOY0,down,Sys_Milliseconds());
    else if (key >= 0 && key < MAX_KEYS) CL_KeyEvent(key,down,Sys_Milliseconds());
    const char* binding = Key_GetBinding(key);
    Com_Printf("ST_EMOTE_INPUT %s %d %d %d %s\n",Cmd_Argv(1),key,down,stWheelActive,binding?binding:"");
}

void CL_EmotesInit() {
    Cvar_Get("st_emoteWheelOpen","0",CVAR_ROM|CVAR_NORESTART);
    Cvar_Get("st_emoteSelection","",CVAR_TEMP);
    Cvar_Get("st_emoteWheelToggle","0",CVAR_ARCHIVE|CVAR_NORESTART);
    Cvar_Get("st_emoteGroup","0",CVAR_ARCHIVE|CVAR_NORESTART);
    Cmd_AddCommand("st_emote",CL_EmotePlay);
    Cmd_AddCommand("+st_emotewheel",CL_EmoteUnusedCommand);
    Cmd_AddCommand("-st_emotewheel",CL_EmoteUnusedCommand);
    Cmd_AddCommand("st_emoteinputqa",CL_EmoteInputQA);
}
