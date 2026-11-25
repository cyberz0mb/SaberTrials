"""Windows menu and lifecycle regression. Pass the ST_CONTROLS_QA UI DLL."""
from pathlib import Path
import re
import shutil
import sys
import tempfile

from playback import DATA, ROOT, run
from peer_color import port, start, wait


def check(log):
    assert "THEME_RUN_COMPLETE" in log, log[-1800:]
    failures = [line for line in log.splitlines() if any(s in line for s in
                ("ST_LEGACY_FAIL", "ST_SETUP_FAIL", "Unknown command \"st_", "UI_Alloc: Failure",
                 "default menu file not found", "ERROR: file st_retail"))]
    assert not failures, failures[:15]


def foreign_pause(exe, qa):
    for theme in (0,1):
        home=qa/f"pure-{theme}"
        mod=home/"base"
        mod.mkdir(parents=True)
        # The server VM must match this engine ABI. The non-Trials directory
        # selects the regular stock client modules and the personal pause UI.
        shutil.copyfile(ROOT/"jampgamex86_64.dll",mod/"jampgamex86_64.dll")
        commands=[f"set st_menuTheme {theme}","set sv_pure 1",'set sv_master1 ""',
                  "set st_combatMode 0","set g_hybridStyles 0","set g_directionalFeints 0",
                  "set g_manualBlocking 0","set g_saberHandedness 0","set g_stanceLibrary 0",
                  "map mp/duel1","wait 195"]
        # Retail opens the player setup on the first spawn in a fresh home.
        for _ in range(2 if theme==0 else 1):
            commands+=["st_emoteinputqa ESCAPE 1","st_emoteinputqa ESCAPE 0","wait 15"]
        commands+=["st_personalStatus","st_legacyqa assertmenu ingame",f"st_legacyqa layout {1-theme}",
                   f"screenshot_png pure-pause-{theme}",f"set st_menuTheme {1-theme}","wait 15",
                   f"st_legacyqa layout {theme}","st_legacyqa assertmenu ingame",
                   f"set st_menuTheme {theme}","wait 15","disconnect","wait 20",
                   "st_menuTheme","echo THEME_RUN_COMPLETE","quit"]
        log=run(exe,home,"base",commands)
        check(log)
        assert "Connected to a pure server." in log and "PERSONAL_UI frontend=ingame\n" in log
        assert "Going from CS_PRIMED to CS_ACTIVE" in log
        assert (mod/f"screenshots/pure-pause-{theme}.png").is_file()
        assert (home/"SaberTrials/menu-theme.txt").read_text()==str(theme)


def main(qa_dll):
    qa = Path(tempfile.mkdtemp(prefix="menu-theme-",dir=ROOT/"dist/compat/qa"))
    print(qa,flush=True)
    binary = qa/"bin"
    binary.mkdir()
    for name in ("SaberTrials.x86_64.exe","SDL2.dll","OpenAL32.dll","rd-vanilla_x86_64.dll"):
        shutil.copyfile(ROOT/"client"/name,binary/name)
    for name in ("stock","ja-compat"):
        shutil.copytree(ROOT/"client"/name,binary/name)
    shutil.copyfile(qa_dll,binary/"SaberTrialsUI.x86_64.dll")
    exe = binary/"SaberTrials.x86_64.exe"
    home = qa/"player"
    mod = home/"SaberTrials"
    mod.mkdir(parents=True)
    shutil.copyfile(qa_dll,mod/"uix86_64.dll")
    catalog = (ROOT/"dist/compat/frontend/codemp/ui/st_setup_catalog.h").read_text()
    theme_id = 2200+re.findall(r'^ \{"([^"]+)"',catalog,re.M).index("st_menuTheme")

    def play(lines, safe=True, after=None):
        end = ["echo THEME_RUN_COMPLETE","quit"]
        if after:
            (mod/"post-host.cfg").write_text("\n".join(after+end)+"\n")
            end = ["st_setupqa continue post-host.cfg"]
        log = run(exe,home,"SaberTrials",["wait 35",*lines,*end],safe=safe)
        check(log)
        return log

    screens = ("main","multiplayermenu","joinserver","createserver","quickgame","playerMenu","setup_menu","controlsMenu")
    def capture(theme):
        lines = []
        for screen in screens:
            lines += [f"ui_openmenu {screen}","wait 6",f"st_legacyqa assertmenu {screen}",
                      f"screenshot_png {theme}-{screen}"]
        return lines

    play(["st_legacyqa layout 0","seta st_hudStyle 2","seta st_combatMode 1",
          "bind F8 +scores","set name ThemeTester",*capture("trials"),
          "ui_openmenu setup_menu","wait 4","st_setupqa click 2002","wait 4",
          f"st_setupqa click {theme_id}","st_setupqa click 2902","wait 16",
          "st_legacyqa layout 1",*capture("classic"),"ui_openmenu setup_menu","wait 4",
          "st_legacyqa hover stInterface","st_legacyqa pad accept","wait 4",
          "st_legacyqa assertmenu st_theme_interface","screenshot_png classic-interface",
          "st_legacyqa hover allSettings","st_legacyqa pad down","st_legacyqa pad accept",
          "st_legacyqa assertmenu setup_menu","st_legacyqa click stInterface","wait 4",
          "st_legacyqa hover allSettings","st_legacyqa pad accept","wait 12",
          "st_setupqa asserttab 2","st_legacyqa layout 0","ui_openmenu main","wait 4",
          "st_legacyqa pad back","wait 12","st_legacyqa layout 1",
          "st_setupqa assertvar st_hudStyle 2","st_setupqa assertvar st_combatMode 1",
          "st_setupqa assertvar name ThemeTester"])
    assert (mod/"menu-theme.txt").read_text()=="0"
    for theme in ("classic","trials"):
        for screen in screens:
            assert (mod/f"screenshots/{theme}-{screen}.png").is_file()

    # A stale per-mod startup preference must not displace the shared choice.
    with (mod/"openjk.cfg").open("a") as cfg:
        cfg.write('\nseta st_menuTheme "1"\n')
    play(["st_legacyqa layout 1","st_setupqa assertvar st_menuTheme 0",
          "ui_openmenu setup_menu","wait 4","st_legacyqa click stInterface","wait 4",
          "st_legacyqa click menuTheme","wait 12","st_legacyqa layout 0",
          "st_setupqa asserttab 2","st_setupqa assertvar st_hudStyle 2"],safe=False)
    assert (mod/"menu-theme.txt").read_text()=="1"
    assert 'bind "F8" "+scores"' in (mod/"openjk.cfg").read_text()

    for theme in (0,1):
        for preset in (0,1):
            log = play([f"set st_menuTheme {theme}",f"set st_combatMode {1-preset}",
                        f"set ui_stHostPreset {1-preset}","set ui_stHostPresetSet 0",
                        "set sv_pure 0",'set sv_master1 ""',"ui_openmenu createserver","wait 12",
                        "st_legacyqa click stHostPreset",f"st_setupqa assertvar ui_stHostPreset {preset}",
                        "st_setupqa assertvar ui_stHostPresetSet 1",
                        f"st_setupqa assertvar st_combatMode {1-preset}","st_legacyqa click accept",
                        "wait 12","st_legacyqa pointer 500 416"],
                       after=["wait 160",f"st_setupqa assertvar st_combatMode {preset}",
                        "st_legacyqa pause","wait 12","st_legacyqa assertmenu ingame",
                        f"st_legacyqa layout {1-theme}",f"screenshot_png pause-{theme}-{preset}",
                        "disconnect","wait 35",f"st_legacyqa layout {1-theme}"])
            assert "Going from CS_PRIMED to CS_ACTIVE" in log

    foreign_pause(exe,qa)
    print("Passed both selectors, restart, four listen matches and pure-server pause switching.",flush=True)
    if "--udp" in sys.argv:
        dedicated(exe,qa)


def dedicated(exe,qa):
    # Optional external process test for hosts permitting IPv4 loopback UDP.
    server_port = port()
    server = start(DATA/"openjkded.x86_64.exe",qa/"server",
                   dict(net_port=server_port,dedicated=1,sv_pure=1,sv_master1="",sv_maxclients=4),
                   ["map mp/duel1","echo LOCAL_THEME_SERVER"])
    try:
        wait(qa/"server","LOCAL_THEME_SERVER",server)
        for theme in (0,1):
            client_home=qa/f"online-{theme}"
            pulse=["st_personalStatus","st_emoteinputqa ESCAPE 1","st_emoteinputqa ESCAPE 0","wait 18"]
            process=start(exe,client_home,dict(cl_renderer="rd-vanilla"),[
                f"set st_menuTheme {theme}",f"connect 127.0.0.1:{server_port}","wait 900",
                *pulse,*pulse,*pulse,"st_personalStatus","disconnect","wait 45","st_menuTheme",
                "echo THEME_RUN_COMPLETE","quit"])
            try:
                process.wait(timeout=70)
                log=(client_home/"base/qconsole.log").read_text(errors="replace")
                check(log)
                assert "Connected to a pure server." in log and "PERSONAL_UI frontend=ingame\n" in log
            finally:
                if process.poll() is None: process.kill()
    finally:
        server.terminate()
        server.wait(timeout=10)
    print("Passed both dedicated-server connections.")


if __name__=="__main__":
    main(Path(sys.argv[1]).resolve())
