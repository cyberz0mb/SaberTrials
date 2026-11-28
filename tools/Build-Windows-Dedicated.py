"""Build the Windows host from the same engine checkpoint as the dedicated server."""
from pathlib import Path
import subprocess
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "dist/pug-01"
STARTUP = r'''
#if defined(_WIN32) && defined(DEDICATED)
    // Installed inside GameData/SaberTrials, alongside the game module.
    char gameData[_MAX_PATH];
    char executable[_MAX_PATH];
    if (!_fullpath(executable, argv[0], sizeof(executable)) ||
        !_fullpath(gameData, va("%s\\..", Sys_Dirname(executable)), sizeof(gameData))) {
        fprintf(stderr, "Could not locate the Jedi Academy installation.\n");
        return 1;
    }
    Sys_SetDefaultInstallPath(gameData);
    Q_strcat(commandLine, sizeof(commandLine), "+set fs_game SaberTrials ");
    const char *local = getenv("LOCALAPPDATA");
    if (local && *local)
        Q_strcat(commandLine, sizeof(commandLine),
            va("+set fs_homepath \"%s\\SaberTrials\\Server\" ", local));
    bool customStart = false;
    for (int arg = 1; arg < argc; ++arg)
        if (!Q_stricmp(argv[arg], "+map") || !Q_stricmp(argv[arg], "+exec"))
            customStart = true;
#endif
'''


def build():
    path = BASE / "engine/shared/sys/sys_main.cpp"
    source = path.read_text()
    if STARTUP not in source:
        anchor = "Sys_SetDefaultInstallPath( DEFAULT_BASEDIR );"
        init = "Com_Init (commandLine);"
        if source.count(anchor) != 1 or source.count(init) != 1:
            raise ValueError("Dedicated engine startup changed")
        source = source.replace(anchor, anchor + "\n" + STARTUP)
        source = source.replace(init, '''#if defined(_WIN32) && defined(DEDICATED)
    if (!customStart)
        Q_strcat(commandLine, sizeof(commandLine), " +exec server/sabertrials-host.cfg");
#endif
    Com_Init (commandLine);''')
        path.write_text(source)
    console = BASE / "engine/shared/sys/con_win32.cpp"
    text = console.read_text()
    old_title = 'SetConsoleTitle(CLIENT_WINDOW_TITLE " Dedicated Server Console");'
    new_title = 'SetConsoleTitle("Saber Trials Dedicated Server");'
    if new_title not in text:
        if text.count(old_title) != 1:
            raise ValueError("Dedicated console title changed")
        console.write_text(text.replace(old_title, new_title))
    subprocess.run(["cmake", "--build", BASE / "build-engine", "--config", "Release",
                    "--target", "openjkded.x86_64", "--parallel", "1", "--", "/nr:false"], check=True)
    shutil.copyfile(BASE / "build-engine/Release/openjkded.x86_64.exe", ROOT / "SaberTrialsDed.x86_64.exe")


if __name__ == "__main__":
    build()
