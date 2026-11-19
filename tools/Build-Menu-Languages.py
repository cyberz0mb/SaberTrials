"""Collect and render the offline Saber Trials menu catalogs."""
from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path
import json
import re
import unicodedata
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'development-source/menu-language'
BASE = ROOT / 'dist/ffa-controller-01/frontend/codemp/ui'
LANGUAGES = ROOT / 'development-source/translator/languages.json'
LITERAL = r'"(?:\\.|[^"\\\n])*"'
C_TOKENS = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|' + LITERAL)
MENU_LABELS = re.compile(r'\b(?:text|text2|descText|description|setitemtext)\s+(' + LITERAL + ')', re.I)
REFERENCE = re.compile(r'@[A-Z][A-Z0-9_]+', re.I)
PROTECTED = re.compile(r'(%[dsifug]|%[.0-9]+[dsifug]|%%|\^[0-9]|\b(?:Saber Trials|Star Wars|Jedi Academy|OpenJK|Direct Input|Rend2|DLC|FFA|TFFA|CTF|FPS|RGB|HUD|V-Sync|[a-z]+_[A-Za-z0-9_]+)\b)', re.I)


def candidate(text):
    return (bool(re.search(r'[A-Z]{2,}|[A-Z][a-z]{1,}|\b[a-z]{3,}\b', text))
            and not re.search(r'[/\\][a-z0-9_.]+\.(?:png|tga|cfg|menu|wav|roq)|^(?:ui|gfx|sound|models|fonts|textures)/', text, re.I)
            and not re.fullmatch(r'(?:[a-zA-Z]+_[a-z0-9_]+|[a-z]+[A-Z][A-Za-z]+|\w+\.(?:cfg|menu)|[0-9x. ]+)', text)
            and text not in ('Saber Trials', 'Star Wars', 'STAR WARS', 'Jedi Academy', 'OpenJK')
            and not re.search(r'[\t\r]|\.(?:exe|dll|pk3|otf|ttf)$',text,re.I)
            and len(text) <= 1500)


def menu_files():
    active = {}
    paths = list((ROOT.parent/'base').glob('assets?.pk3')) + list(ROOT.glob('*.pk3'))
    for path in sorted(paths, key=lambda x: (x.parent == ROOT, x.name.lower())):
        with zipfile.ZipFile(path) as pack:
            active.update({name.lower(): pack.read(name).decode('cp1252', 'replace') for name in pack.namelist()
                           if name.lower().startswith('ui/jamp/') and name.lower().endswith(('.menu','.inc'))})
    active.update({path.relative_to(ROOT).as_posix(): path.read_text(encoding='utf8', errors='replace')
                   for path in (ROOT/'ui/jamp').glob('*.menu')})
    return active


def inventory():
    keys, refs = set(), set()
    for text in menu_files().values():
        keys.update(m[1][1:-1].replace('\\n','\n') for m in MENU_LABELS.finditer(text))
        refs.update(r[1:].upper() for r in REFERENCE.findall(text))
    files = [p for p in BASE.glob('*.inc') if p.name.startswith(('ui_st_', 'st_presentation', 'ui_sabertrials'))]
    files += [BASE/'st_controls_catalog.h', BASE/'ui_main.c', BASE/'ui_saber.c']
    files += list((BASE.parent/'../client').glob('cl_st_*.inc'))
    files += list((ROOT/'dist/ffa-controller-01/engine/codemp/client').glob('cl_st_*.inc'))
    # Collect authored English copy, skipping include paths, commands and cvar identifiers.
    for path in files:
        for token in C_TOKENS.findall(path.read_text(encoding='utf8', errors='replace')):
            if not token.startswith('"'):
                continue
            try:
                text = json.loads(token)
            except ValueError:
                continue
            if path.name in ('ui_main.c','ui_saber.c') and not text.startswith(('MENUS_','MP_INGAME_')):
                continue
            if re.fullmatch(r'(?:MENUS|MP_INGAME)_\w+', text):
                refs.add(text)
            elif not re.fullmatch(r'[a-z_][a-z_0-9]*', text) and not any(c in text for c in '\t\r\n'):
                keys.add(text)
    rows = json.loads((ROOT/'development-source/setup/catalog.json').read_text())
    for row in rows:
        keys.update(row[k] for k in ('label','group','help'))
        keys.update(v.split('=',1)[1] for v in row['choices'].split('|') if '=' in v)
    keys.update(('Play','Profile','Controls','Setup','Exit','Menu language','Language',
                 'Changes the language of menus.','English','Español','Français','Deutsch','Italiano',
                 'Português','Português (Brasil)','Русский','Українська','日本語','简体中文','繁體中文','العربية',
                 '한국어','हिन्दी','Polski','Türkçe'))
    output = {key: key for key in keys if candidate(key) and not key.startswith('@')}
    with zipfile.ZipFile(ROOT.parent/'base/assets0.pk3') as pack:
        files = {name.lower(): name for name in pack.namelist()}
        for package in ('menus','mp_ingame','mp_svgame'):
            name = f'strings/english/{package}.str'
            if name not in files:
                continue
            data = pack.read(files[name]).decode('cp1252','replace')
            for ref, value in re.findall(r'^REFERENCE\s+(\w+)\s*\n(?:\s*NOTES.*\n)*\s*LANG_ENGLISH\s+"(.*)"',data,re.M):
                key = f'{package.upper()}_{ref}'
                if key in refs and candidate(value):
                    output['@'+key] = value.replace('\\n','\n')
    return dict(sorted(output.items()))


def translate(code, language_id, output):
    runtime = ROOT/'client/translator'
    sys.path.insert(0,str(runtime))
    worker = import_module('worker')
    trans = worker.Translator(runtime)
    trans.load('en',code)
    entries = inventory()
    overrides = json.loads((SOURCE/'terms.json').read_text(encoding='utf8'))
    words = {}
    def translate_paragraphs(text):
        parts = text.split('\n')
        tokens = [trans.encode(part) for part in parts if part]
        results = iter(trans.model.translate_batch(tokens,beam_size=2,max_decoding_length=300,disable_unk=True))
        return '\n'.join(trans.decode(next(results).hypotheses[0]).strip() if part else '' for part in parts)

    for start in range(0,len(entries),48):
        batch = list(entries.items())[start:start+48]
        tokens = [trans.encode(value) for _,value in batch]
        results = trans.model.translate_batch(tokens,beam_size=2,max_decoding_length=220,disable_unk=True)
        for (key, original), result in zip(batch,results):
            curated = overrides.get(original,{}).get(code)
            value = curated or (translate_paragraphs(original) if '\n' in original else trans.decode(result.hypotheses[0]).strip())
            if sorted(PROTECTED.findall(original)) != sorted(PROTECTED.findall(value)) and curated is None:
                continue
            if (value and value!=original and len(value.encode('utf8'))<=4000
                    and not re.search(r'(.{2,12})(?:[ ,、，]*\1){5,}',value,re.I)
                    and not any(ord(c)<32 and c!='\n' for c in value)
                    and not any(0x202a<=ord(c)<=0x202e or 0x2066<=ord(c)<=0x2069 for c in value)):
                words[key] = value
    output.mkdir(parents=True,exist_ok=True)
    def escape(text):
        return text.replace('\\','\\\\').replace('\n','\\n')
    (output/f'{language_id}.tsv').write_text(''.join(f'{escape(k)}\t{escape(v)}\n' for k,v in sorted(words.items())),encoding='utf8',newline='\n')
    print(f'{code}: {len(words)} of {len(entries)} strings',flush=True)


def reviewed(code):
    rows = (SOURCE/'labels.tsv').read_text(encoding='utf8').splitlines()
    columns = rows[0].split('\t')
    index = columns.index(code)
    values = {key: variants[code] for key,variants in
              json.loads((SOURCE/'terms.json').read_text(encoding='utf8')).items() if code in variants}
    for row in rows[1:]:
        cells = row.split('\t')
        assert len(cells)==len(columns), cells[0]
        values[cells[0]] = unicodedata.normalize('NFC',cells[index])
    values.update({key.upper():value for key,value in list(values.items()) if key not in ('Menu motion: On','Menu motion: Off')})
    return values


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('language',nargs='?')
    parser.add_argument('--output',type=Path,default=SOURCE/'catalogs')
    args = parser.parse_args()
    languages = json.loads(LANGUAGES.read_text())
    if args.language is None:
        print(len(inventory()),'source strings')
    else:
        language = next(row for row in languages if row['code']==args.language and row['id']>1)
        translate(language['code'],language['id'],args.output)
