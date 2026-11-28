"""Apply the language tables and keyboards to the assembled Windows beta sources."""
import argparse
import json
from pathlib import Path
import shutil
import importlib
import sys

SOURCE = Path(__file__).resolve().parent.parent
LANGS = json.loads((SOURCE / "translator/languages.json").read_text(encoding="utf8"))


def replace(path, old, new):
    text = path.read_text(encoding="utf8")
    if new in text:
        return
    if old not in text:
        raise ValueError(f"Missing integration point in {path}: {old[:55]}")
    path.write_text(text.replace(old, new), encoding="utf8", newline="\n")


def tables(tree):
    native = tree / "codemp"
    for path in native.rglob("st_translation_api.h"):
        replace(path, "ST_TRANSLATION_LANGUAGES 17", f"ST_TRANSLATION_LANGUAGES {len(LANGS)}")
    for path in native.rglob("st_translation_languages.h"):
        for marker, key in [('"UK"}', "code"), ('"uk-UA"}', "locale")]:
            values = [row[key].upper() if key == "code" else row[key] for row in LANGS[17:]]
            replace(path, marker, marker[:-1] + "," + ",".join(map(json.dumps, values)) + "}")
        replace(path, "id<=17", "id<=(int)(sizeof(values)/sizeof(*values))")
    catalog = native / "ui/st_setup_catalog.h"
    if catalog.exists():
        replace(catalog, '17=Ukrainian"', '17=Ukrainian|18=Dutch|19=Swedish|20=Finnish"')
        # The last endonym is stored as octal UTF-8 in the original C resource.
        if "st_menuLanguage" in catalog.read_text():
            replace(catalog, '","1",2,2,0,0,CVAR_ARCHIVE | CVAR_NORESTART,1,17}',
                    '|18=Nederlands|19=Svenska|20=Suomi","1",2,2,0,0,CVAR_ARCHIVE | CVAR_NORESTART,1,20}')


def keyboard(engine, frontend):
    for native in (engine, frontend):
        shutil.copyfile(SOURCE / "controls/st_keyboard_layout.h", native / "codemp/qcommon/st_keyboard_layout.h")
    client = engine / "codemp/client"
    for name in ("cl_st_console_pad.inc", "cl_st_keyboard_edit.inc"):
        shutil.copyfile(SOURCE / "controls" / name, client / name)
    shutil.copyfile(SOURCE / "profile/ui_st_name_keyboard.inc", frontend / "codemp/ui/ui_st_name_keyboard.inc")
    keys = client / "cl_keys.cpp"
    replace(keys, '#include "cl_st_chat_input.inc"', '#include "cl_st_chat_input.inc"\n#include "cl_st_keyboard_edit.inc"')
    replace(keys, "if(edit==&chatField){ST_ChatKey(key);return;}", """if(edit==&chatField){ST_ChatKey(key);return;}
    if(edit==&g_consoleField && (key==A_DELETE || key==A_CURSOR_LEFT || key==A_CURSOR_RIGHT)){
        ST_ConsoleMove(edit,key==A_CURSOR_LEFT,key==A_DELETE);return;
    }""")
    replace(keys, "if(edit==&chatField){ST_ChatChar(ch);return;}", """if(edit==&chatField){ST_ChatChar(ch);return;}
    if(edit==&g_consoleField){
        if(ch==8){ST_ConsoleMove(edit,true,true);return;}
        if(ch>=32){ST_ConsoleChar(edit,ch);return;}
    }""")
    replace(keys, "key=ConvertUTF32ToExpectedCharset(cp);}", """if(catcher&KEYCATCH_CONSOLE){Field_CharEvent(&g_consoleField,cp);return;}
        key=ConvertUTF32ToExpectedCharset(cp);}""")
    replace(keys, "Field_CharEvent( edit, ConvertUTF32ToExpectedCharset( utf32 ) );",
            "Field_CharEvent( edit, edit==&g_consoleField ? (int)utf32 : ConvertUTF32ToExpectedCharset( utf32 ) );")


def embed(engine):
    sys.path.insert(0, str(SOURCE.parent / "tools"))
    builder = importlib.import_module("Build-Menu-Languages")
    win32 = engine / "codemp/win32"
    rc = win32 / "openjk.rc"
    script = rc.read_bytes()
    for row in (r for r in LANGS if r["code"] in ("pl", "nl", "sv", "fi")):
        name = f'{row["id"]}.tsv'
        source = SOURCE / "menu-language/catalogs" / name
        values = dict(line.split("\t", 1) for line in source.read_text(encoding="utf8").splitlines())
        values.update(builder.reviewed(row["code"]))
        data = "".join(f"{key}\t{value}\n" for key, value in sorted(values.items())).encode("utf8")
        if not 0 < len(data) <= 1024 * 1024:
            raise ValueError(f"Menu catalog too large: {name}")
        (win32 / "menu-catalogs" / name).write_bytes(data)
        declaration = f'{4100+row["id"]} RCDATA "menu-catalogs/{name}"'.encode("ascii")
        if declaration not in script:
            script += b"\n" + declaration + b"\n"
    rc.write_bytes(script)


def apply(engine, frontend, cgame):
    for path in (engine, frontend, cgame):
        tables(path)
    keyboard(engine, frontend)
    for path in (frontend / "codemp/ui/ui_st_menu_language.inc",
                 engine / "codemp/client/foreign_menu_language.inc",
                 engine / "codemp/client/cl_st_menu_font.inc"):
        replace(path, "language > 17", "language > ST_TRANSLATION_LANGUAGES")
    generic = SOURCE / "translator/st_translation_api.h"
    for path in (frontend / "codemp/ui/ui_st_menu_language.inc",
                 engine / "codemp/client/foreign_menu_language.inc"):
        replace(path, '#include "qcommon/st_utf8.h"',
                '#include "qcommon/st_utf8.h"\n#include "qcommon/' + generic.name + '"')
    label = (SOURCE.parent / "templates/windows/beta-version.txt").read_text().strip()
    (engine / "codemp/qcommon/st_beta_version.h").write_text(
        f'#define ST_BETA_BUILD_LABEL "Saber Trials Windows {label}"\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("engine", "frontend", "cgame"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    apply(args.engine, args.frontend, args.cgame)
    embed(args.engine)
