/* Kept before the existing Saber load function. Editing is committed by the
 * Combat styles page only, never by an unrelated equipment Apply action. */
static qboolean st_hybridKeepSaberDraft=qfalse;
static int ST_UIHybridReadStyle(const char *name) {
    char value[32];
    trap->Cvar_VariableStringBuffer(name,value,sizeof(value));
    return value[0]>='1' && value[0]<='6' && !value[1]?value[0]-'0':-1;
}
static qboolean ST_UIHybridParseLoadout(const char *value,int *styles) {
    int i;
    for(i=0;i<3;i++) {
        while(*value==' ' || *value=='\t')value++;
        if(*value<'1' || *value>'6')return qfalse;
        styles[i]=*value++-'0';
        if(i<2 && *value!=' ' && *value!='\t')return qfalse;
    }
    while(*value==' ' || *value=='\t')value++;
    return !*value && styles[0]!=styles[1] && styles[0]!=styles[2] && styles[1]!=styles[2];
}
static void ST_UIHybridSavedStyles(int *styles) {
    char value[128];
    int legacy;
    trap->Cvar_VariableStringBuffer("saberStyleLoadout",value,sizeof(value));
    if(ST_UIHybridParseLoadout(value,styles))return;
    styles[0]=1;styles[1]=2;styles[2]=3;
    /* An existing but malformed selection falls back to stock. Only an absent
     * selection migrates the former one-style preference, without saving yet. */
    if(!value[0]) {
        legacy=ST_UIHybridReadStyle("saberCombatStyle");
        if(legacy>=4)styles[0]=legacy;
    }
}
static int ST_UIHybridFirstStyle(void) {
    int styles[3];ST_UIHybridSavedStyles(styles);return styles[0];
}
static void ST_UIHybridSetDraft(const int *styles) {
    trap->Cvar_Set("ui_saberStyleSlot1",va("%d",styles[0]));
    trap->Cvar_Set("ui_saberStyleSlot2",va("%d",styles[1]));
    trap->Cvar_Set("ui_saberStyleSlot3",va("%d",styles[2]));
}
static void ST_UIHybridGetCvar(void) {
    int styles[3];ST_UIHybridSavedStyles(styles);ST_UIHybridSetDraft(styles);
}
static int ST_UIHybridReadDraft(int *styles) {
    styles[0]=ST_UIHybridReadStyle("ui_saberStyleSlot1");
    styles[1]=ST_UIHybridReadStyle("ui_saberStyleSlot2");
    styles[2]=ST_UIHybridReadStyle("ui_saberStyleSlot3");
    if(styles[0]<1 || styles[1]<1 || styles[2]<1)return -1;
    return styles[0]!=styles[1] && styles[0]!=styles[2] && styles[1]!=styles[2];
}
