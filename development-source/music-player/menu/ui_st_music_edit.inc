bool ST_MusicQueryEditing(bool finish) {
    if (!g_editingField || !g_editItem || !g_editItem->cvar || Q_stricmp(g_editItem->cvar, "st_musicQuery"))
        return false;
    if (finish) {
        Leaving_EditField(g_editItem);
        g_editItem = NULL;
        g_editingField = qfalse;
        DC->setOverstrikeMode(qfalse);
    }
    return true;
}

void ST_MusicFocusQuery() {
    menuDef_t *menu = Menu_GetFocused();
    if (!menu || Q_stricmp(menu->window.name,"st_music_player")) return;
    itemDef_t *field = Menu_FindItemByName(menu,"query");
    if (!field) return;
    Item_SetFocus(field, DC->cursorx, DC->cursory);
    g_editItem = field;
    g_editingField = qtrue;
    char text[MAX_STRING_CHARS];
    DC->getCVarString("st_musicQuery",text,sizeof(text));
    field->cursorPos = strlen(text);
    DC->setOverstrikeMode(qfalse);
}
