// Used by the engine and the optional client-game renderer after a gamestate arrives.
static inline int JA_MatchesServer(const char *server, const char *system) {
    if (!*server) return 0;
    char name[MAX_QPATH];
    Q_strncpyz(name,Info_ValueForKey(server,"gamename"),sizeof(name));
    Q_StripColor(name);
    const char *folder=Info_ValueForKey(system,"fs_game");
    if (!Q_stricmp(folder,"SaberTrials") || !Q_stricmpn(name,"JA++",4) || !Q_stricmpn(name,"jaPRO",5))
        return 0;
    return !Q_stricmpn(name,"JA+",3) || !Q_stricmpn(name,"japlus",6) || !Q_stricmp(folder,"japlus");
}
static inline int JA_ServerAllowsRGB(const char *server) {
    const char *flag=Info_ValueForKey(server,"jp_allowRGBsaber");
    return !*flag || atoi(flag)!=0;
}
