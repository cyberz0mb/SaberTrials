/* Isolated test UI only. This text must never appear in production. */
#include "ghoul2/G2.h"
static qboolean ST_MenuQA(void) {
    const char *op = UI_Argv(1);
    if (!Q_stricmp(op, "state")) {
        menuDef_t *menu = Menu_GetFocused();
        int i;
        trap->Print("MENU_QA focused=%s\n", menu ? menu->window.name : "none");
        if (menu) for (i=0; i<menu->itemCount; i++) {
            itemDef_t *item=menu->items[i];
            if (item->window.flags & WINDOW_HASFOCUS)
                trap->Print("MENU_QA item=%s\n", item->window.name);
        }
    } else if (!Q_stricmp(op,"profile")) {
        menuDef_t *menu = Menus_FindByName("playerMenu");
        itemDef_t *item = menu ? Menu_FindItemByName(menu,"st_profile_preview") : NULL;
        if (!item || item->type != ITEM_TYPE_MODEL || !item->ghoul2) {
            trap->Print("PROFILE_QA valid=0\n");
        } else {
            float frame=0, speed=0;
            int first=0,last=0,flags=0;
            modelDef_t *model=item->typeData.model;
            qboolean animated=trap->G2API_GetBoneAnim(item->ghoul2,"model_root",uiInfo.uiDC.realTime,
                &frame,&first,&last,&flags,&speed,NULL,0);
            trap->Print("PROFILE_QA valid=1 selected=%s anim=%d frame=%.3f first=%d last=%d loop=%d yaw=%.3f skin=%d\n",
                UI_Cvar_VariableString("model"),animated,frame,first,last,
                (flags&BONE_ANIM_OVERRIDE_LOOP)!=0,
                model->angle+(float)uiInfo.uiDC.realTime/model->rotationSpeed,model->g2skin);
            trap->Print("PROFILE_LAYOUT width=%.2f height=%.2f fovx=%.3f fovy=%.3f xscale=%.4f yscale=%.4f\n",
                item->window.rect.w-2,item->window.rect.h-2,model->fov_x,model->fov_y,uiInfo.uiDC.xscale,uiInfo.uiDC.yscale);
        }
    } else if (!Q_stricmp(op,"continue")) {
        /* Run the next main-menu test step after commands queued by a click.
           This avoids needing a game server/RCON merely to drive the UI. */
        trap->Cmd_ExecuteText(EXEC_APPEND, va("exec \"%s\"\n", UI_Argv(2)));
    } else if (!Q_stricmp(op,"tab")) {
        UI_KeyEvent(A_TAB,qtrue); UI_KeyEvent(A_TAB,qfalse);
    } else if (!Q_stricmp(op,"down")) {
        UI_KeyEvent(A_CURSOR_DOWN,qtrue); UI_KeyEvent(A_CURSOR_DOWN,qfalse);
    } else return qfalse;
    return qtrue;
}
