// JA+ session input and userinfo. Preferences are local, only the outgoing
// userinfo of an identified JA+ session carries the extra saber fields.
#include "ja_identity.h"
static const char *JA_ConfigString(int index) {
    return cl.gameState.stringData + cl.gameState.stringOffsets[index];
}

bool CL_JAConnection() {
    if (cls.state < CA_CONNECTED || CL_TrialsGame()) return false;
    return JA_MatchesServer(JA_ConfigString(CS_SERVERINFO),JA_ConfigString(CS_SYSTEMINFO))!=0;
}

bool JA_ActionsActive() {
    return cls.state==CA_ACTIVE && !clc.demoplaying && CL_JAConnection();
}

bool JA_RGBAllowed() {
    return JA_ServerAllowsRGB(JA_ConfigString(CS_SERVERINFO))!=0;
}

static const char *JA_HookRule() {
    return Info_ValueForKey(JA_ConfigString(CS_SERVERINFO),"jp_allowHook");
}

bool JA_HookPressAllowed() {
    if (!JA_ActionsActive()) return false;
    if (!strcmp(JA_HookRule(),"0")) {
        Com_Printf("Grapple is disabled on this JA+ server.\n");
        return false;
    }
    return true;
}

void JA_PrintHookPackets();
static void JA_Jetpack() {
    if (JA_ActionsActive()) CL_AddReliableCommand("jetpack",qfalse);
}

static void JA_FullForceDuel() {
    if (JA_ActionsActive()) CL_AddReliableCommand("engage_FullForceDuel",qfalse);
}

static cvar_t *jaRGB[2], *jaStyle[2];
static void JA_Status() {
    const bool active=JA_ActionsActive();
    Com_Printf("JA+ client: active=%d rgb=%d hook button=%d\n",active,active && JA_RGBAllowed(),
        (cl.cmds[cl.cmdNumber & CMD_MASK].buttons & (1<<12))!=0);
    if(active) {
        const char *rule=JA_HookRule();
        Com_Printf("Grapple rule: %s.\n", !*rule?"unreported":!strcmp(rule,"0")?"disabled":
            !strcmp(rule,"1")?"allowed for all":!strcmp(rule,"2")?"restricted to mercenaries":rule);
        bool found=false;
        for(int key=1;key<MAX_KEYS;++key) {
            const char *binding=Key_GetBinding(key);
            if(binding && (!Q_stricmp(binding,"+st_jaGrapple") || !Q_stricmp(binding,"+button12"))) {
                Com_Printf("Grapple key: %s\n",Key_KeynumToString(key));
                found=true;
            }
        }
        if(!found) Com_Printf("Grapple key: unassigned. Open Controls > Movement and apply a binding.\n");
        JA_PrintHookPackets();
        Com_Printf("JA+ saber choices: %d/%d and %d/%d (RGB/style).\n",
            jaRGB[0]->integer,jaStyle[0]->integer,jaRGB[1]->integer,jaStyle[1]->integer);
        if(clc.clientNum>=0 && clc.clientNum<MAX_CLIENTS) {
            const char *player=JA_ConfigString(CS_PLAYERS+clc.clientNum);
            for(int slot=0;slot<2;++slot) {
                const char *rgb=Info_ValueForKey(player,slot?"c4":"c3");
                Com_Printf("Server-reported packed RGB for saber %d: %s\n",slot+1,*rgb?rgb:"unreported");
            }
        }
    }
}
static void JA_Init() {
    for (int i=0;i<2;++i) {
        jaRGB[i]=Cvar_Get(i?"st_jaRGB2":"st_jaRGB1","-1",CVAR_ARCHIVE);
        jaStyle[i]=Cvar_Get(i?"st_jaStyle2":"st_jaStyle1","6",CVAR_ARCHIVE);
    }
    Cmd_AddCommand("st_jaJetpack",JA_Jetpack);
    Cmd_AddCommand("st_jaFullForceDuel",JA_FullForceDuel);
    Cmd_AddCommand("st_jaStatus",JA_Status);
}

static void JA_Userinfo(char *info) {
    if (!CL_JAConnection() || !JA_RGBAllowed()) return;
    for (int i=0;i<2;++i) {
        int rgb=jaRGB[i]->integer;
        if (rgb<0 || rgb>0xffffff) continue;
        int packed=((rgb&0xff)<<16) | (rgb&0xff00) | ((rgb>>16)&0xff);
        // JA+ reserves zero for an unset RGB value.
        if (packed==0) packed=0x010101;
        char updated[MAX_INFO_STRING];
        Q_strncpyz(updated,info,sizeof(updated));
        const char *key=i?"cp_sbRGB2":"cp_sbRGB1";
        const char *colorKey=i?"color2":"color1";
        const int style=Com_Clampi(6,10,jaStyle[i]->integer);
        Info_SetValueForKey(updated,key,va("%d",packed));
        Info_SetValueForKey(updated,colorKey,va("%d",style));
        if(atoi(Info_ValueForKey(updated,key))==packed && atoi(Info_ValueForKey(updated,colorKey))==style &&
           strlen(updated)+sizeof("userinfo \"\"")<=MAX_STRING_CHARS)
            Q_strncpyz(info,updated,MAX_INFO_STRING);
    }
}

static void JA_CheckUserinfo() {
    static bool lastActive=false;
    bool active=CL_JAConnection() && JA_RGBAllowed();
    if (active!=lastActive) cvar_modifiedFlags|=CVAR_USERINFO;
    lastActive=active;
    for (int i=0;i<2;++i) {
        if (active && (jaRGB[i]->modified || jaStyle[i]->modified)) cvar_modifiedFlags|=CVAR_USERINFO;
        jaRGB[i]->modified=jaStyle[i]->modified=qfalse;
    }
}
