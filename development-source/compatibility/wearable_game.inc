#include "st_wearable_id.h"
#include "st_wearable_draw.inc"
static qhandle_t stWearModels[MAX_CLIENTS][2];
static stWearBolts_t stWearBolts[MAX_CLIENTS];

static void ST_ReadWearables(int client, const char *info) {
    int slot;
    char game[MAX_QPATH];
    trap->Cvar_VariableStringBuffer("fs_game",game,sizeof(game));
    if (Q_stristr(game,"japro") || Q_stristr(Info_ValueForKey(CG_ConfigString(CS_SERVERINFO),"gamename"),"japro")) info="";
    const char *system=CG_ConfigString(CS_SYSTEMINFO);
    const qboolean unrestricted=(qboolean)(!atoi(Info_ValueForKey(system,"sv_pure")) && !*Info_ValueForKey(system,"sv_paks"));
    for (slot=0;slot<2;++slot) {
        const char *name=ST_WearableSuffix(Info_ValueForKey(info,slot?"c2":"c1"));
        stWearModels[client][slot]=*name ? trap->R_RegisterModel(va("models/cosmetics/%s/%s.md3",slot?"capes":"hats",name)) : 0;
        if (*name && !stWearModels[client][slot] && unrestricted)
            stWearModels[client][slot]=trap->R_RegisterModel(va("st_outfits/%s/%s.md3",slot?"capes":"hats",name));
    }
}
static void ST_DrawPlayerWearables(centity_t *cent, const refEntity_t *body) {
    const int client=cent->currentState.number;
    vec3_t angles;
    if (client<0 || client>=MAX_CLIENTS || cent->currentState.eType!=ET_PLAYER ||
        (cent->currentState.eFlags & (EF_DEAD|EF_NODRAW)) || !cg.snap ||
        (!cg.renderingThirdPerson && cg.snap->ps.clientNum==client) ||
        CG_IsMindTricked(cent->currentState.trickedentindex,cent->currentState.trickedentindex2,
            cent->currentState.trickedentindex3,cent->currentState.trickedentindex4,cg.snap->ps.clientNum)) return;
    VectorSet(angles,0,cent->turAngles[YAW],cent->lerpAngles[ROLL]);
    for(int slot=0;slot<2;++slot) ST_DrawWearable(body,stWearModels[client][slot],slot,cg.time,angles,cgs.gameModels,&stWearBolts[client]);
}
