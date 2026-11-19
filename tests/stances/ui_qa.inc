/* Test build only: calls real page actions and input handlers; never distributed. */
static const char* ST_StanceArgv(int index) {
    static char values[4][MAX_STRING_CHARS];static int cursor;
    char* value=values[(cursor++)&3];trap->Cmd_Argv(index,value,MAX_STRING_CHARS);return value;
}
void ST_StanceQA_f(void) {
    const char* action=ST_StanceArgv(1);
    if(!Q_stricmp(action,"open") || !Q_stricmp(action,"game")) {
        menuDef_t* parent;itemDef_t* entry;
        if(!Q_stricmp(action,"game"))UI_LoadMenus("ui/jampingame.txt",qtrue);
        UI_GetSaberCvars();
        Menus_CloseAll();
        parent=Menus_ActivateByName(!Q_stricmp(action,"game")?"ingame_saber":"saberMenu");
        entry=parent?Menu_FindItemByName(parent,"st_stances_options"):NULL;
        if(!entry){trap->Print("STANCE_QA missing stance entry on Saber page\n");return;}
        Item_RunScript(entry,entry->action);
        trap->Key_SetCatcher(KEYCATCH_UI);return;
    }
    if(!Q_stricmp(action,"click")) {
        menuDef_t* menu=Menu_GetFocused();
        itemDef_t* item=menu?Menu_FindItemByName(menu,ST_StanceArgv(2)):NULL;
        if(!item) {trap->Print("STANCE_QA missing item %s\n",ST_StanceArgv(2));return;}
        UI_MouseEvent((int)(item->window.rect.x+item->window.rect.w/2-uiInfo.uiDC.cursorx),
                      (int)(item->window.rect.y+item->window.rect.h/2-uiInfo.uiDC.cursory));
        UI_KeyEvent(A_MOUSE1,qtrue);UI_KeyEvent(A_MOUSE1,qfalse);return;
    }
    if(!Q_stricmp(action,"action")) {ST_UIStanceScript(ST_StanceArgv(2));return;}
    if(!Q_stricmp(action,"swing") || !Q_stricmp(action,"rest")) {
        trap->Cvar_Set("ui_stanceMotion","1");
        st_stanceCycleStart=uiInfo.uiDC.realTime-(!Q_stricmp(action,"swing")?2000:0);
        ST_UIStanceRefresh(Menu_GetFocused());return;
    }
    if(!Q_stricmp(action,"probe")) {
        menuDef_t* menu=Menu_GetFocused();
        itemDef_t* item=menu?Menu_FindItemByName(menu,"st_stance_preview"):NULL;
        menuDef_t* parent=Menus_FindByName(st_stanceReturn);
        char saved[64],hilt[64];float frame=0,speed=0;int first=0,last=0,flags=0;
        trap->Cvar_VariableStringBuffer("saberStances",saved,sizeof(saved));
        trap->Cvar_VariableStringBuffer("saber1",hilt,sizeof(hilt));
        if(item && item->ghoul2)trap->G2API_GetBoneAnim(item->ghoul2,"model_root",uiInfo.uiDC.realTime,
            &frame,&first,&last,&flags,&speed,NULL,0);
        trap->Print("STANCE_QA label=%s menu=%s slot=%d choice=%d supported=%d protocol=%d saved=%s hand=%d hilt=%s anim=%d first=%d last=%d frame=%.3f flags=%d parentFlags=%d pending=%d\n",
            ST_StanceArgv(2),menu?menu->window.name:"none",ST_UIStanceSlot(),st_stanceDraft[ST_UIStanceSlot()],
            (int)trap->Cvar_VariableValue("ui_stanceSupported"),(int)trap->Cvar_VariableValue("st_stanceProtocol"),saved,
            (int)trap->Cvar_VariableValue("saberHand"),hilt,item?item->typeData.model->g2anim:-1,first,last,frame,flags,parent?parent->window.flags:-1,st_stancePendingReturn);
    }
}
