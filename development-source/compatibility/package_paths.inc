// A beta EXE lives two levels below the retail installation. The shortcut and
// command line can still provide their own base, mod and writable profile.
#if defined(_WIN32) && !defined(DEDICATED)
static void FS_SetPackagedClientDefaults() {
    char executable[MAX_OSPATH];
    const DWORD size = GetModuleFileNameA(nullptr, executable, sizeof(executable));
    if (!size || size >= sizeof(executable)) return;
    char *name = strrchr(executable, '\\');
    if (!name || Q_stricmp(name + 1, "SaberTrials.x86_64.exe")) return;
    *name = 0;
    char *client = strrchr(executable, '\\');
    if (!client || Q_stricmp(client + 1, "client")) return;
    char binary[MAX_OSPATH];
    Q_strncpyz(binary, executable, sizeof(binary));
    *client = 0;
    char *mod = strrchr(executable, '\\');
    if (!mod || Q_stricmp(mod + 1, "SaberTrials")) return;
    *mod = 0;

    extern void Sys_SetBinaryPath(const char *);
    extern void Sys_SetDefaultInstallPath(const char *);
    Sys_SetBinaryPath(binary);
    Sys_SetDefaultInstallPath(executable);
    if (Cvar_Flags("fs_basepath") != CVAR_NONEXISTENT) return;
    if (Cvar_Flags("fs_game") == CVAR_NONEXISTENT) Cvar_Set("fs_game", "SaberTrials");
    if (Cvar_Flags("fs_homepath") == CVAR_NONEXISTENT) {
        char home[MAX_OSPATH];
        const DWORD length = GetEnvironmentVariableA("LOCALAPPDATA", home, sizeof(home));
        if (length && length + sizeof("\\SaberTrials") <= sizeof(home)) {
            Q_strcat(home, sizeof(home), "\\SaberTrials");
            Cvar_Set("fs_homepath", home);
        }
    }
}
#endif
