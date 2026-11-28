#include "st_wearable_id.h"
static void ST_OutfitUserinfo(char *info) {
    if (cls.state<CA_PRIMED) return;
    const char *server=cl.gameState.stringData+cl.gameState.stringOffsets[CS_SERVERINFO];
    if (Q_stristr(Info_ValueForKey(server,"gamename"),"japro") ||
        Q_stristr(Cvar_VariableString("fs_game"),"japro")) return;
    char key[2*MAX_QPATH+16], pair[32];
    ST_OutfitKey(Info_ValueForKey(info,"model"),key,sizeof(key));
    Q_strncpyz(pair,Cvar_VariableString(key),sizeof(pair));
    char *second=strchr(pair,',');
    if (!second) return;
    *second++=0;
    for (int slot=0;slot<2;++slot) {
        const char *id=slot?second:pair, *field=slot?"color2":"color1";
        if (strcmp(id,"-") && !ST_WearableName(id)) continue;
        const char *color=Info_ValueForKey(info,field);
        size_t digits=strspn(color,"0123456789");
        if (!digits || (color[digits] && !ST_WearableSuffix(color)[0])) continue;
        if (!strcmp(id,"-")) id="";
        char combined[16];
        if (digits+strlen(id)>=sizeof(combined) ||
            strlen(info)-strlen(color)+digits+strlen(id)>=MAX_INFO_STRING) continue;
        memcpy(combined,color,digits);
        strcpy(combined+digits,id);
        if (strcmp(combined,color)) Info_SetValueForKey(info,field,combined);
    }
}
