"""Append distinct, retimed stock animation IDs. Never edit the underlying GLA."""
from pathlib import Path
import hashlib
import json
import math
import re
import zipfile

PREFIX = 'models/players/_humanoid/'
# FS_PathCmp folds to uppercase: '_' sorts after 'Z', so adding a third z
# incorrectly placed the expanded config below zz_sabertrials_stances_v1.pk3.
# Use a common prefix and a suffix that sorts above STANCES in the real engine.
PACKAGE_NAME = 'zz_sabertrials_styles_v1.pk3'
PARSER_BUFFER_BYTES = 131072
PROFILES = ((4, 'GREEN', 2, 1.20), (5, 'PURPLE', 1, 1.15), (6, 'ORANGE', 3, 1.25))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def enum_names(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    body = text.split('typedef enum', 1)[1].split('MAX_ANIMATIONS', 1)[0]
    names = re.findall(r'\b(?:BOTH|TORSO|LEGS|FACE)_[A-Za-z0-9_]+\b', body)
    if not names or len(names) != len(set(names)):
        raise ValueError('Unexpected animation enum layout')
    return names


def cfg_rows(data):
    rows = {}
    for line in data.decode('utf-8-sig').splitlines():
        fields = line.split('//', 1)[0].split()
        if len(fields) >= 5:
            try:
                row = [int(fields[1]), int(fields[2]), int(fields[3]), float(fields[4])]
            except ValueError:
                continue
            if fields[0] in rows:
                raise ValueError('Duplicate animation row '+fields[0])
            rows[fields[0]] = row
    return rows


def frame_lerp(fps):
    if not fps:
        raise ValueError('Zero FPS cannot provide a distinct timing contract')
    return math.floor(1000/fps) if fps < 0 else math.ceil(1000/fps)


def generate(baseline_package, enum_file, output):
    names = enum_names(Path(enum_file).read_text())
    with zipfile.ZipFile(baseline_package) as z:
        cfg = z.read(PREFIX+'animation.cfg')
    rows = cfg_rows(cfg)
    aliases = []
    for style, label, parent, rate in PROFILES:
        start = names.index(f'BOTH_A{parent}_T__B_')
        end = names.index(f'BOTH_D{parent}_B____')+1
        if end-start != 77:
            raise ValueError('Unexpected saber animation group size')
        for source_id in range(start, end):
            source = names[source_id]
            if source not in rows:
                raise ValueError('Missing motion row '+source)
            original = rows[source]
            row = original[:3]+[round(original[3]*rate, 6)]
            if row[0] < 0 or row[1] < 1 or row[2] < -1:
                raise ValueError('Invalid source motion '+source)
            aliases.append(dict(id=len(names)+len(aliases), name=f'BOTH_ST_{label}_{source[5:]}',
                                style=style, parent=parent, source_id=source_id, source_name=source,
                                source_row=original, row=row, rate=rate,
                                frame_lerp=frame_lerp(row[3]), source_frame_lerp=frame_lerp(original[3])))
    if len(names)+len(aliases) >= 2048:
        raise ValueError('Animation compatibility budget exceeded')
    additions = '\n// Saber Trials hybrid styles: retimed stock frames, original rows unchanged.\n'
    additions += ''.join(f"{a['name']} {a['row'][0]} {a['row'][1]} {a['row'][2]} {a['row'][3]:g}\n" for a in aliases)
    expanded = cfg+additions.encode('ascii')
    if len(expanded) >= PARSER_BUFFER_BYTES-1:
        raise ValueError('Expanded animation configuration exceeds the bounded parser capacity')
    manifest = dict(version=1, original_count=len(names), total_count=len(names)+len(aliases),
                    baseline_package_sha256=digest(Path(baseline_package).read_bytes()),
                    baseline_cfg_sha256=digest(cfg), cfg_sha256=digest(expanded),
                    motion_source='Retimed stock frames; no new mocap or GLA edits', aliases=aliases)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    info = zipfile.ZipInfo(PREFIX+'animation.cfg', date_time=(2026,10,30,0,0,0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    with zipfile.ZipFile(output/PACKAGE_NAME, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(info, expanded)
    (output/'aliases.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    (output/'st_hybrid_anims.h').write_text(header(manifest), encoding='utf-8', newline='\n')
    return manifest


def header(manifest):
    aliases = manifest['aliases']
    lines = ['/* Generated: retimed stock animations. Include after animation_t. */',
             '#ifndef ST_HYBRID_ANIMS_H', '#define ST_HYBRID_ANIMS_H',
             '#define ST_HYBRID_ASSET_VERSION "'+manifest['cfg_sha256'][:16]+'"',
             'static inline int STH_AnimStyle(int anim) {']
    for i in range(0,231,77):
        a, b = aliases[i], aliases[i+76]
        lines.append(f"    if(anim>={a['name']} && anim<={b['name']})return {a['style']};")
    lines += ['    return 0;', '}', 'static inline int STH_OriginalAnim(int anim) {']
    for i in range(0,231,77):
        a, b = aliases[i], aliases[i+76]
        lines.append(f"    if(anim>={a['name']} && anim<={b['name']})return {a['source_name']}+anim-{a['name']};")
    lines += ['    return anim;', '}', 'static inline int STH_AnimForStyle(int style,int legacyAnim) {',
              '    int anim=STH_OriginalAnim(legacyAnim), offset=-1;',
              '    if(anim>=BOTH_A1_T__B_ && anim<=BOTH_D1_B____)offset=anim-BOTH_A1_T__B_;',
              '    else if(anim>=BOTH_A2_T__B_ && anim<=BOTH_D2_B____)offset=anim-BOTH_A2_T__B_;',
              '    else if(anim>=BOTH_A3_T__B_ && anim<=BOTH_D3_B____)offset=anim-BOTH_A3_T__B_;',
              '    if(offset<0)return legacyAnim;', '    switch(style) {']
    for i in range(0,231,77):
        a = aliases[i]
        lines.append(f"    case {a['style']}:return {a['name']}+offset;")
    lines += ['    default:return anim;', '    }', '}',
              'static inline int STH_AnimationsValid(const animation_t* anims) {',
              '    static const int expected[231][4]={']
    lines += [f"        {{{a['row'][0]},{a['row'][1]},{a['frame_lerp']},{a['row'][2]}}}," for a in aliases]
    lines += ['    };', '    int i;', '    if(!anims)return 0;', '    for(i=0;i<231;i++) {',
              f"        const animation_t* a=&anims[{aliases[0]['name']}+i];",
              '        if(a->firstFrame!=expected[i][0] || a->numFrames!=expected[i][1] ||',
              '           a->frameLerp!=expected[i][2] || a->loopFrames!=expected[i][3])return 0;',
              '    }', '    return 1;', '}', '#endif', '']
    return '\n'.join(lines)


def fix_ui_parser(root):
    # The menu compiles its own parser, not bg_panimate.c. Both readers must
    # accommodate the same package; keep their existing oversize rejection.
    path = Path(root)/'codemp/ui/ui_main.c'
    text = path.read_text()
    old = 'static char UIPAFtext[60000];'
    if text.count(old) != 1:
        raise ValueError('Unexpected UI animation parser buffer')
    path.write_text(text.replace(old, f'static char UIPAFtext[{PARSER_BUFFER_BYTES}];', 1), newline='\n')


def apply(root, assets, manifest):
    root, assets = Path(root), Path(assets)
    additions = ''.join('\t'+a['name']+',\n' for a in manifest['aliases'])
    path = root/'codemp/game/anims.h'
    text = path.read_text()
    if '\tMAX_ANIMATIONS,' not in text or 'BOTH_ST_GREEN_' in text:
        raise ValueError('Unexpected or already patched enums')
    path.write_text(text.replace('\tMAX_ANIMATIONS,', additions+'\tMAX_ANIMATIONS,', 1), newline='\n')
    path = root/'codemp/cgame/animtable.h'
    text = path.read_text()
    if '\t//must be terminated' not in text:
        raise ValueError('Animation table marker missing')
    table = ''.join('\tENUM2STRING('+a['name']+'),\n' for a in manifest['aliases'])
    path.write_text(text.replace('\t//must be terminated', table+'\t//must be terminated', 1), newline='\n')
    path = root/'codemp/game/bg_public.h'
    text = path.read_text()
    if text.count('} animation_t;') != 1:
        raise ValueError('Animation type marker missing')
    path.write_text(text.replace('} animation_t;', '} animation_t;\n#include "st_hybrid_anims.h"', 1), newline='\n')
    (root/'codemp/game/st_hybrid_anims.h').write_bytes((assets/'st_hybrid_anims.h').read_bytes())
    path = root/'codemp/game/st_direction_map.h'
    text = path.read_text()
    marker = 'static inline int ST_DirectionAnim(int semanticAnim)\n{\n'
    if text.count(marker) != 1:
        raise ValueError('Directional animation adapter marker missing')
    addition = '''    int hybridStyle=STH_AnimStyle(semanticAnim);
    if(hybridStyle) {
        int original=STH_OriginalAnim(semanticAnim);
        return STH_AnimForStyle(hybridStyle, st_direction_normal_map[original-BOTH_A1_T__B_]);
    }
'''
    path.write_text(text.replace(marker, marker+addition, 1), newline='\n')
    path = root/'codemp/game/bg_panimate.c'
    text = path.read_text()
    if text.count('BGPAFtext[60000]') != 1:
        raise ValueError('Unexpected animation parser buffer')
    path.write_text(text.replace('BGPAFtext[60000]', f'BGPAFtext[{PARSER_BUFFER_BYTES}]', 1), newline='\n')
    fix_ui_parser(root)
