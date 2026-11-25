// Feed two independent JA+ blade records and a hook to the production cgame
// drawing functions. Capture exactly what they submit to the engine renderer.
#include "cgame/cg_players.c"
#include "cgame/ja_hook.inc"
#include "cgame/ja_identity.h"
#include <stdio.h>

static refEntity_t drawn[3];
static vec3_t light;
static int count;
static void submit(const refEntity_t *ent){if(count<3)drawn[count++]=*ent;}
static void illuminate(const vec3_t pos,float size,float r,float g,float b){VectorSet(light,r,g,b);}

int main(void) {
    static cgameImport_t imports;
    vec3_t origin={0,0,0}, dir={1,0,0};
    int style;
    imports.R_AddRefEntityToScene=submit;
    imports.R_AddLightToScene=illuminate;
    trap=&imports;
    if(!JA_MatchesServer("\\gamename\\^2JA+ v2.4","\\fs_game\\custom") ||
       JA_MatchesServer("\\gamename\\JA++","\\fs_game\\japlus") ||
       JA_MatchesServer("\\gamename\\JA+","\\fs_game\\SaberTrials") ||
       JA_MatchesServer("","\\fs_game\\japlus") ||
       JA_ServerAllowsRGB("\\jp_allowRGBsaber\\0"))return 6;
    if(JA_ReadRGB("")!=-1 || JA_ReadRGB("-1")!=-1 || JA_ReadRGB("16777216")!=-1 ||
       JA_ReadRGB("65x")!=-1 || JA_ReadRGB("16777215")!=0xffffff)return 1;
    for(style=0;style<5;++style){
        int packed=style%2?0xc78324:0x3251eb;
        count=0;
        cgs.media.jaGlow[style]=100+style;
        cgs.media.jaLine[style]=200+style;
        JA_DoSaber(origin,dir,40,40,2,(saber_colors_t)(6+style),0,qtrue,packed);
        if(count!=2 || drawn[0].customShader!=100+style || drawn[1].customShader!=200+style)return 2;
        for(int channel=0;channel<3;++channel){
            int expected=(packed>>(channel*8))&255;
            if(drawn[0].shaderRGBA[channel]!=expected || drawn[1].shaderRGBA[channel]!=expected ||
               fabs(light[channel]-expected/255.f)>.0001f)return 3;
        }
    }
    centity_t hook={0};
    // Original JA+ client reads the signed slot at offset 0xBC. Missile
    // clientNum and owner are intentionally different from that slot.
    if (offsetof(entityState_t,otherEntityNum)!=0xBC) return 9;
    hook.currentState.clientNum=0;
    hook.currentState.owner=7;
    hook.currentState.otherEntityNum=2;
    VectorSet(hook.lerpOrigin,145,98,20);
    VectorSet(cg_entities[2].lerpOrigin,5,3,10);
    cg_entities[2].currentValid=qtrue;
    cgs.media.jaHook=42;
    count=0;JA_DrawHook(&hook);
    if(count!=2 || drawn[0].reType!=RT_LINE || drawn[0].origin[2]!=34 ||
        drawn[0].oldorigin[0]!=145 || drawn[1].hModel!=42)return 4;
    static snapshot_t localSnap;
    cg.snap=&localSnap;
    cg.snap->ps.clientNum=2;
    cg_entities[2].currentValid=qfalse;
    VectorSet(cg.predictedPlayerState.origin,32,18,90);
    count=0;JA_DrawHook(&hook);
    if(count!=2 || drawn[0].origin[0]!=32 || drawn[0].origin[2]!=114)return 7;
    // Both grapples can coexist. Slot zero is a valid owner, never a default.
    cg.snap->ps.clientNum=0;
    cg_entities[2].currentValid=qtrue;
    count=0;JA_DrawHook(&hook);
    if(count!=2 || drawn[0].origin[0]!=5)return 10;
    hook.currentState.otherEntityNum=0;hook.currentState.clientNum=2;
    count=0;JA_DrawHook(&hook);
    if(count!=2 || drawn[0].origin[0]!=32 || drawn[0].oldorigin[0]!=145)return 11;
    hook.currentState.otherEntityNum=2;
    cg_entities[2].currentValid=qfalse;
    cg.snap->ps.clientNum=1;
    count=0;JA_DrawHook(&hook);
    if(count)return 8;
    hook.currentState.otherEntityNum=MAX_CLIENTS;
    count=0;JA_DrawHook(&hook);
    if(count)return 5;
    puts("All five JA+ blade styles submitted the correct RGB, light and core. Hook used its owner's position and server endpoint.");
    return 0;
}
