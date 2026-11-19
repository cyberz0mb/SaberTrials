"""Extract production parsing functions and archive bytes for an offline harness."""
from pathlib import Path
import argparse
import re
import zipfile


def function(text, signature):
    if text.count(signature) != 1:
        raise ValueError('Function signature changed: ' + signature)
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2] + '\n'


def struct(text, name):
    start = text.index('typedef struct ' + name)
    return text[start:text.index(';', text.index('\n}', start)) + 1] + '\n'


def prepare(candidate, output, ui_source=None):
    game = candidate / 'game/codemp'
    output.mkdir(parents=True, exist_ok=True)
    shared = (game / 'qcommon/q_shared.c').read_text()
    strings = (candidate / 'game/shared/qcommon/q_string.c').read_text()
    animations = (game / 'game/bg_panimate.c').read_text()
    types = (game / 'game/bg_public.h').read_text()
    definitions = '#pragma pack(push,1)\n' + struct(types, 'animation_s') + '#pragma pack(pop)\n'
    definitions += struct(types, 'bgLoadedAnim_s')
    definitions += struct((game / 'qcommon/q_shared.h').read_text(), 'stringID_table_s')
    (output / 'parser_types_under_test.h').write_text(definitions)
    body = function(strings, 'int Q_stricmpn (') + function(strings, 'int Q_stricmp (')
    body += function(shared, 'int GetIDForString (')
    body += function(shared, 'const char *SkipWhitespace(')
    body += function(shared, 'char *COM_ParseExt(') + function(shared, 'char *COM_Parse(')
    body += function(animations, 'void BG_InitAnimsets(')
    body += function(animations, 'int BG_ParseAnimationFile(')
    (output / 'parser_functions_under_test.h').write_text(body)
    # The menu has its own parser and its own buffer. Do not substitute the
    # shared BG parser: isHumanoid=false does not turn BG into the UI parser.
    ui_root = ui_source or candidate / 'frontend'
    frontend = ui_root / 'codemp'
    ui = (frontend / 'ui/ui_main.c').read_text()
    ui_shared = (frontend / 'qcommon/q_shared.c').read_text()
    ui_strings = (ui_root / 'shared/qcommon/q_string.c').read_text()
    ui_types = (frontend / 'game/bg_public.h').read_text()
    ui_definitions = '#pragma pack(push,1)\n' + struct(ui_types, 'animation_s') + '#pragma pack(pop)\n'
    ui_definitions += struct(ui_types, 'bgLoadedAnim_s')
    ui_definitions += struct((frontend / 'qcommon/q_shared.h').read_text(), 'stringID_table_s')
    (output / 'ui_parser_types_under_test.h').write_text(ui_definitions)
    ui_body = function(ui_strings, 'int Q_stricmpn (') + function(ui_strings, 'int Q_stricmp (')
    ui_body += function(ui_strings, 'void Q_strncpyz(')
    ui_body += function(ui_shared, 'int GetIDForString (')
    ui_body += function(ui_shared, 'const char *SkipWhitespace(')
    ui_body += function(ui_shared, 'char *COM_ParseExt(') + function(ui_shared, 'char *COM_Parse(')
    ui_body += function(ui_shared, 'void COM_BeginParseSession(')
    declaration, = re.findall(r'static char UIPAFtext\[\d+\];', ui)
    ui_body += declaration + '\n' + function(ui, 'int UI_ParseAnimationFile(')
    (output / 'ui_parser_functions_under_test.h').write_text(ui_body)
    packages = sorted((candidate / 'assets').glob('*.pk3'))
    baseline = candidate / 'assets/zz_sabertrials_stances_v1.pk3'
    expanded, = [p for p in packages if p != baseline]
    prefix = 'models/players/_humanoid/'
    with zipfile.ZipFile(baseline) as z:
        (output / 'baseline.cfg').write_bytes(z.read(prefix + 'animation.cfg'))
        (output / 'stance.gla').write_bytes(z.read(prefix + '_humanoid.gla'))
    with zipfile.ZipFile(expanded) as z:
        (output / 'expanded.cfg').write_bytes(z.read(prefix + 'animation.cfg'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--ui-source', type=Path)
    args = parser.parse_args()
    prepare(args.candidate, args.output, args.ui_source)
