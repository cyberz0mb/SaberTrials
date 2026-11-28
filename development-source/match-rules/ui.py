"""Reproducible Match Rules frontend overlay; never edits the installed menus."""
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent


def _replace(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Match Rules frontend integration anchor missing: {old[:90]!r}")
    return text.replace(old, new, 1)


def apply(root: Path) -> None:
    """Apply to a disposable frontend source root before building its UI module."""
    root = Path(root)
    target = root / "codemp/ui"
    for name in ("st_match_rules.h", "ui_st_match_rules.inc"):
        shutil.copy2(HERE / name, target / name)
    path = target / "ui_main.c"
    text = path.read_text(encoding="utf-8")
    text = _replace(text, '#include "ui_st_legacy.inc"', '#include "ui_st_legacy.inc"\n#include "ui_st_match_rules.inc"')
    text = _replace(text, 'if ( ST_UIMenuScript( name ) ) { return; }', 'if ( MRUI_Script( name ) ) { return; }\n\t\tif ( ST_UIMenuScript( name ) ) { return; }')
    text = _replace(text, '\t\tSWI_Draw();', '\t\tSWI_Draw();\n\t\tMRUI_Draw();')
    text = _replace(text, 'void UI_KeyEvent( int key, qboolean down ) {', 'void UI_KeyEvent( int key, qboolean down ) {\n\tif (MRUI_Key(key,down)) return;')
    text = _replace(text, 'if (SWI_Mouse(dx, dy) || SWB_Mouse()) return;', 'if (MRUI_Mouse()) return;\n\t\tif (SWI_Mouse(dx, dy) || SWB_Mouse()) return;')
    path.write_text(text, encoding="utf-8", newline="\n")


def menus(output: Path) -> None:
    """Write only the three changed menu copies into a packaging staging root."""
    output = Path(output)
    target = output / "ui/jamp"
    target.mkdir(parents=True, exist_ok=True)
    host = (PROJECT / "ui/jamp/createserver.menu").read_text(encoding="utf-8")
    host = re.sub(r'text\s+"Advanced"', 'text "Match Rules"', host, count=1)
    host = re.sub(r'(onOpen\s*\{)', r'\1\n uiScript matchRulesHostReset ;', host, count=1)
    # StartServer is intercepted natively before the legacy script can change gameplay cvars.
    (target / "createserver.menu").write_text(host, encoding="utf-8", newline="\n")
    (target / "advancedcreateserver.menu").write_text('''{
 menuDef {
  name "advancedcreateserver" rect 0 0 640 480 fullscreen 1 visible 0
  focusColor 1 1 1 1
  onOpen { uiScript matchRules ; }
  onESC { uiScript matchRulesCancel ; }
 }
}
''', encoding="utf-8", newline="\n")
    pause = (PROJECT / "ui/jamp/ingame.menu").read_text(encoding="utf-8")
    marker = 'menuDef { name "st_pause_tools"'
    start = pause.index(marker)
    end = pause.index('menuDef { name "st_pause_vote"', start)
    tools = pause[start:end]
    anchor = 'itemDef { name "back_line"'
    button = '''itemDef { name "match_rules" rect 250 110 352 32 type 1 text "Match Rules (host)"
 font 2 textscale .85 textalignx 14 textaligny 6 forecolor .76 .86 .93 1 visible 1
 cvarTest "sv_running" showCvar { "1" }
 onFocus { show focus_glow ; setitemrect focus_glow 250 110 352 32 ; }
 leaveFocus { hide focus_glow ; }
 action { play "sound/interface/button1.wav" ; open advancedcreateserver ; }
}
'''
    if 'name "match_rules"' not in tools:
        if anchor not in tools:
            raise RuntimeError("Match Rules pause integration anchor missing")
        tools = tools.replace(anchor, button + anchor, 1)
    pause = pause[:start] + tools + pause[end:]
    (target / "ingame.menu").write_text(pause, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--menus", type=Path)
    options = parser.parse_args()
    apply(options.root)
    if options.menus:
        menus(options.menus)
