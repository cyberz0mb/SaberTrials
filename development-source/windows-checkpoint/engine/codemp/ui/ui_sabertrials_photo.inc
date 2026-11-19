// Photo settings only; no broad menu styling. GPL-2.0-or-later.
static qboolean ST_UIPhotoScript(const char *name) {
    const char *fields[] = {"Fov", "Roll", "Speed"};
    const char *sources[] = {"st_photoFov", "st_photoRoll", "st_photoSpeed"};
    const char *defaults[] = {"90", "0", "200"};
    const double low[] = {20,-45,20}, high[] = {120,45,800};
    int i;
    if (!Q_stricmp(name,"stPhotoInit") || !Q_stricmp(name,"stPhotoReset")) {
        trap->Cvar_Register(NULL,"st_photoHelp","1",CVAR_ARCHIVE);
        trap->Cvar_Register(NULL,"st_photoGuides","0",CVAR_ARCHIVE);
        for (i=0;i<3;i++) {
            menuDef_t *menu = Menu_GetFocused();
            itemDef_t *item;
            trap->Cvar_Register(NULL,sources[i],defaults[i],CVAR_ARCHIVE);
            if (!Q_stricmp(name,"stPhotoReset")) trap->Cvar_Set(sources[i],defaults[i]);
            ST_UIInputValue(va("st_uiPhoto%s",fields[i]),sources[i]);
            item = menu ? Menu_FindItemByName(menu,va("value%d",i)) : NULL;
            if (item && item->typeData.edit) {
                item->typeData.edit->paintOffset=0; item->cursorPos=0;
            }
        }
        if (!Q_stricmp(name,"stPhotoReset")) {
            trap->Cvar_Set("st_photoHelp","1"); trap->Cvar_Set("st_photoGuides","0");
            trap->Cvar_Set("st_photoFreeze","0");
        }
        trap->Cvar_Set("st_uiPhotoStatus","Drag or type values, then Apply camera.");
        return qtrue;
    }
    if (!Q_stricmp(name,"stPhotoApply")) {
        double numbers[3];
        for (i=0;i<3;i++) {
            char text[64], *end;
            trap->Cvar_VariableStringBuffer(va("st_uiPhoto%s",fields[i]),text,sizeof(text));
            numbers[i]=strtod(text,&end);
            if (end==text || *end || numbers[i]!=numbers[i] || numbers[i]<low[i] || numbers[i]>high[i]) {
                trap->Cvar_Set("st_uiPhotoStatus","Use FOV 20-120, tilt -45 to 45, speed 20-800.");
                return qtrue;
            }
        }
        for (i=0;i<3;i++) trap->Cvar_Set(sources[i],va("%.6g",numbers[i]));
        trap->Cvar_Set("st_uiPhotoStatus","Camera settings applied.");
        return qtrue;
    }
    if (!Q_stricmp(name,"stPhotoStart") || !Q_stricmp(name,"stPhotoCapture")) {
        trap->Cvar_Set("st_photoMode","1");
        ST_UICloseVote();
        if (!Q_stricmp(name,"stPhotoCapture")) trap->Cmd_ExecuteText(EXEC_APPEND,"st_photoCapture\n");
        return qtrue;
    }
    if (!Q_stricmp(name,"stPhotoExit")) {
        trap->Cvar_Set("st_photoMode","0"); trap->Cvar_Set("st_photoFreeze","0");
        ST_UICloseVote();
        return qtrue;
    }
    return qfalse;
}
