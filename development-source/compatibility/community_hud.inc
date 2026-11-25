// The two original menu layouts are parsed once per cgame instance on demand.
// They have distinct menu names so a style switch never replaces a server menu.
#include "st_community_hud_draw.inc"
void CG_ParseMenu(const char *menuFile);
static void ST_CommunityIcon(menuDef_t *menu, const char *name, qboolean right) {
    itemDef_t *item=Menu_FindItemByName(menu,name);
    if (!item) return;
    rectDef_t rect=item->window.rect;
    const float x=right ? SCREEN_WIDTH-(SCREEN_WIDTH-rect.x)*stHudRatio : rect.x*stHudRatio;
    trap->R_SetColor(colorWhite);
    CG_DrawPic(x,rect.y,rect.w*stHudRatio,rect.h,item->window.background);
}

static qboolean ST_DrawCommunityHud(centity_t *cent, int style) {
    menuDef_t *left, *right;
    if (style<3 || style>5) return qfalse;
    if (cg.predictedPlayerState.pm_type==PM_SPECTATOR) return qtrue;
    stSelectedHud=style;
    stHudRatio=cgs.screenXScale>0 ? cgs.screenYScale/cgs.screenXScale : 1;
    if (style==3) {
        if (!stOutcast.JK2HUDLeftFrame) ST_RegisterOutcast();
        ST_HudJK2HUDLeftFrame1(0,400);
        ST_HudArmorJK2(0,400);
        ST_HudHealthJK2(0,400);
        ST_HudJK2HUDLeftFrame2(0,400);
        ST_HudJK2HUDRightFrame1(560,400);
        ST_HudForcePowerJK2(560,400);
        ST_HudAmmoJK2(cent,560,400);
        ST_HudJK2HUDRightFrame2(560,400);
    } else {
        const char *prefix=style==4 ? "elegance" : "quake";
        left=Menus_FindByName(va("st_%s_left",prefix));
        if (!left) {
            CG_ParseMenu(va("st_huds/%s.menu",prefix));
            left=Menus_FindByName(va("st_%s_left",prefix));
        }
        right=Menus_FindByName(va("st_%s_right",prefix));
        if (!left || !right) return qfalse;
        ST_HudArmor(left);
        ST_HudHealth(left);
        ST_HudForcePower(right);
        if (cent->currentState.weapon==WP_SABER) ST_HudSaberStyle(cent,right);
        else ST_HudAmmo(cent,right);
        if (style==5) {
            ST_CommunityIcon(left,"health_icon",qfalse);
            ST_CommunityIcon(left,"armor_icon",qfalse);
            ST_CommunityIcon(right,"force_icon",qtrue);
        }
        itemDef_t *score=Menu_FindItemByName(right,"score_line");
        if (score && cg_drawScores.integer) {
            const char *label=CG_GetStringEdString("MP_INGAME","SCORE");
            CG_DrawScaledProportionalString(SCREEN_WIDTH-(SCREEN_WIDTH-score->window.rect.x)*stHudRatio,
                score->window.rect.y,va("%s: %i",label,cg.snap->ps.persistant[PERS_SCORE]),
                UI_RIGHT|UI_DROPSHADOW,score->window.foreColor,0.7f);
        }
    }
    trap->R_SetColor(NULL);
    return qtrue;
}
