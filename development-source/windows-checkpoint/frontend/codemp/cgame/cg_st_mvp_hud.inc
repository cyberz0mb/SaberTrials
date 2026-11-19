/* Reference-matched MVP presentation; never paints letterbox bars. */
#include "st_mvp_hud_type.h"
static qhandle_t stMvpHudShaders[12];
static float stMvpHudX, stMvpHudY, stMvpHudCenter, stMvpHudBottom;

static void ST_MvpHudReset(void) {
    memset(stMvpHudShaders,0,sizeof(stMvpHudShaders));
}

static void ST_MvpHudPicture(int art,float x,float y,float w,float h) {
    CG_DrawPic(x*stMvpHudX,y*stMvpHudY,w*stMvpHudX,h*stMvpHudY,stMvpHudShaders[art]);
}

static void ST_MvpHudText(const char *text,float center,float top,float height,float maxWidth) {
    float width=0, unit=height/100, x;
    const unsigned char *p;
    qboolean ascii=qtrue;
    for (p=(const unsigned char *)text; *p; ++p) {
        if (*p<32 || *p>126) { ascii=qfalse; break; }
        width+=stMvpHudAdvance[*p-32];
    }
    if (!ascii) {
        // Keep the native font path for names outside the display atlas.
        float scale=height*stMvpHudY/CG_Text_Height(text,1,FONT_MEDIUM);
        float measured=CG_Text_Width(text,scale,FONT_MEDIUM);
        if (measured>maxWidth*stMvpHudX) scale*=maxWidth*stMvpHudX/measured;
        CG_Text_Paint(center*stMvpHudX-CG_Text_Width(text,scale,FONT_MEDIUM)/2,
            top*stMvpHudY,scale,colorWhite,text,0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_MEDIUM);
        return;
    }
    if (!width) return;
    // The wide letterforms echo the reference. Fit the complete name, rather
    // than clipping it into either of the decorative chevrons.
    if (width*unit*1.2f>maxWidth) unit=maxWidth/(width*1.2f);
    x=center-width*unit*.6f;
    top+=(height-unit*100)/2;
    for (p=(const unsigned char *)text; *p; ++p) {
        int index=*p-32;
        float u=(index%16)*128.f/2048, v=(index/16)*160.f/1024;
        trap->R_DrawStretchPic((x-16*unit*1.2f)*stMvpHudX,(top-24*unit)*stMvpHudY,
            128*unit*1.2f*stMvpHudX,160*unit*stMvpHudY,
            u,v,u+128.f/2048,v+160.f/1024,stMvpHudShaders[5]);
        x+=stMvpHudAdvance[index]*unit*1.2f;
    }
}

static void ST_MvpDrawHud(const stMvpClip_t *clip) {
    const char *art[]={"frame","title","nameplate","caption","skip","type",
        "title_duel","title_match","title_champion","nameplate_score","caption_winner","continue"};
    const char *name=clip->name;
    char displayName[MAX_NETNAME], kills[16];
    int i,n=0;
    qboolean winner=clip->presentation!=ST_MVP_PRESENT_MVP;
    float panel;
    float fit=Q_min(cgs.glconfig.vidWidth/1672.f,cgs.glconfig.vidHeight/941.f);
    stMvpHudX=fit*640/cgs.glconfig.vidWidth;
    stMvpHudY=fit*480/cgs.glconfig.vidHeight;
    stMvpHudCenter=(640/stMvpHudX-1672)/2;
    stMvpHudBottom=480/stMvpHudY-941;
    for (i=0;i<12;++i) if (!stMvpHudShaders[i])
        stMvpHudShaders[i]=trap->R_RegisterShaderNoMip(va("ui/assets/sabertrials/mvp/%s",art[i]));
    // Winner identity comes from the finalized match, not the art sample.
    // Display in the reference's silver treatment without embedded colors.
    while (*name && n<(int)sizeof(displayName)-1) {
        if (Q_IsColorString(name)) { name+=2; continue; }
        displayName[n++]=(unsigned char)*name<32 ? ' ' : *name;
        ++name;
    }
    displayName[n]='\0';
    if (winner) Com_sprintf(kills,sizeof(kills),"%d - %d",clip->winnerScore,clip->loserScore);
    else Com_sprintf(kills,sizeof(kills),"%d",clip->totalKills);
    panel=clip->cardOnly ? (480/stMvpHudY-246)/2 : stMvpHudBottom+666;
    trap->R_SetColor(NULL);
    // Only the perimeter stretches. Text, crest and panels retain their
    // physical proportions on 4:3, widescreen and ultrawide displays.
    CG_DrawPic(0,0,640,480,stMvpHudShaders[0]);
    ST_MvpHudPicture(winner ? 5+clip->presentation : 1,stMvpHudCenter+424,0,824,160);
    ST_MvpHudPicture(winner ? 9 : 2,stMvpHudCenter+368,panel,920,246);
    ST_MvpHudText(displayName,stMvpHudCenter+900,panel+55,40,548);
    ST_MvpHudText(kills,stMvpHudCenter+836,panel+164,45,190);
    if (!clip->cardOnly) ST_MvpHudPicture(winner ? 10 : 3,55,stMvpHudBottom+819,440,86);
    else if (clip->forfeit) ST_MvpHudText("FORFEIT",stMvpHudCenter+836,panel+264,20,250);
    ST_MvpHudPicture(clip->cardOnly ? 11 : 4,640/stMvpHudX-470,stMvpHudBottom+818,420,86);
    trap->R_SetColor(NULL);
}
