// One local preference across fs_game changes. The stock config for a
// different mod may have been written while another theme was selected.
static bool themeReady;
static char savedTheme = 0;

static void CL_LoadMenuTheme() {
    Cvar_Get("st_menuTheme","1",CVAR_ARCHIVE|CVAR_PROTECTED|CVAR_NORESTART);
    std::ifstream file(JA_ProfilePath("menu-theme.txt"),std::ios::binary);
    char value = 0;
    if (file.get(value) && (value == '0' || value == '1') && file.peek() == EOF) {
        char text[] = {value,0};
        Cvar_Set("st_menuTheme",text);
        savedTheme = value;
    }
    themeReady = true;
}

void CL_SaveMenuTheme(const char *value) {
    if (!themeReady || savedTheme == *value) return;
    const std::string temp = "menu-theme-" + std::to_string(GetCurrentProcessId()) + ".tmp";
    const auto from = JA_ProfilePath(temp.c_str());
    const auto to = JA_ProfilePath("menu-theme.txt");
    fileHandle_t file = FS_SV_FOpenFileWrite(("SaberTrials/"+temp).c_str());
    if (file) {
        bool written = FS_Write(value,1,file) == 1;
        FS_FCloseFile(file);
        if (written && STC_AtomicReplace(from,to)) { savedTheme = *value; return; }
        std::remove(from.c_str());
    }
    Com_Printf("Could not save the shared menu theme.\n");
}
