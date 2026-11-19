/* Test-build only: dispatch real UI key/mouse events. Never ship this hook. */
static void ST_ClientQA_f(void) {
    const char *op = UI_Argv(1);
    if (!Q_stricmp(op, "move")) {
        menuDef_t *menu = Menus_FindByName(UI_Argv(2));
        itemDef_t *item = menu ? Menu_FindItemByName(menu, UI_Argv(3)) : NULL;
        if (!item) { trap->Print("QA item missing\n"); return; }
        UI_MouseEvent((int)(item->window.rect.x + item->window.rect.w / 2 - uiInfo.uiDC.cursorx),
                      (int)(item->window.rect.y + item->window.rect.h / 2 - uiInfo.uiDC.cursory));
    } else if (!Q_stricmp(op, "click")) {
        UI_KeyEvent(A_MOUSE1, qtrue);
        UI_KeyEvent(A_MOUSE1, qfalse);
    } else if (!Q_stricmp(op, "bindf8")) {
        UI_KeyEvent(A_F8, qtrue);
        UI_KeyEvent(A_F8, qfalse);
    } else if (!Q_stricmp(op, "type")) {
        const char *p = UI_Argv(2);
        for (; *p; p++) UI_KeyEvent(*p | K_CHAR_FLAG, qtrue);
    } else if (!Q_stricmp(op, "enter")) {
        UI_KeyEvent(A_ENTER, qtrue);
        UI_KeyEvent(A_ENTER, qfalse);
    } else if (!Q_stricmp(op, "escape")) {
        UI_KeyEvent(A_ESCAPE, qtrue);
        UI_KeyEvent(A_ESCAPE, qfalse);
    }
}
