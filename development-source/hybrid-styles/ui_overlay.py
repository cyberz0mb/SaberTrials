"""Apply hybrid presentation to a staged source/menu copy, never the installation."""
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parent


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Unexpected hybrid UI anchor count: ' + repr(old[:90]))
    return text.replace(old, new, count)


def block_span(text, kind, name):
    token = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/|[{}]')
    match = re.search(r'\b' + re.escape(kind) + r'\s*\{\s*name\s+(?:"' + re.escape(name) + r'"|' + re.escape(name) + r')\s', text, re.I)
    if not match:
        raise ValueError('Missing ' + kind + ' ' + name)
    brace = text.index('{', match.start())
    depth = 0
    for part in token.finditer(text, brace):
        if part[0] == '{':
            depth += 1
        elif part[0] == '}':
            depth -= 1
            if depth == 0:
                return match.start(), part.end()
    raise ValueError('Unclosed ' + kind + ' ' + name)


def named_block(text, kind, name):
    first, last = block_span(text, kind, name)
    return text[first:last]


def required_files(kind):
    if kind == 'engine':
        return []
    files = ['codemp/cgame/cg_draw.c', 'codemp/cgame/cg_sabertrials_hud.inc']
    if kind == 'frontend':
        files += ['codemp/ui/ui_main.c', 'codemp/ui/ui_xcvar.h',
                  'codemp/ui/ui_sabertrials_menu.inc', 'codemp/ui/ui_st_stances.inc']
    return files


def apply(root, kind):
    root = Path(root)
    if kind == 'engine':
        return
    def edit(relative, callback):
        path = root / relative
        path.write_text(callback(path.read_text()), newline='\n')
    def copy(relative, name):
        (root / relative).write_text((SOURCE / name).read_text(), newline='\n')

    copy('codemp/cgame/cg_st_hybrid_hud.inc', 'cg_st_hybrid_hud.inc')
    def hud(text):
        text = replace(text, '#include "ui/ui_public.h"', '#include "ui/ui_public.h"\n#include "cg_st_hybrid_hud.inc"')
        anchor = '\t// draw the current saber style in this window\n'
        branch = '''\t/* A queued preference never labels the HUD as active. */
    {
        const float *color=NULL;
        const char *label=ST_HybridHudLabel(cg.snap->ps.stHybrid.style,&color);
        if(label) {
            focusItem=Menu_FindItemByName(menuHUD,"saberstyle_medium");
            if(focusItem)CG_DrawProportionalString(focusItem->window.rect.x+focusItem->window.rect.w*.5f,
                focusItem->window.rect.y,label,UI_CENTER|UI_SMALLFONT|UI_DROPSHADOW,color);
            return;
        }
    }

'''
        text = replace(text, anchor, branch + anchor)
        start = text.index('static void CG_DrawSimpleSaberStyle(')
        switch = text.index('\tswitch ( cg.predictedPlayerState.fd.saberDrawAnimLevel )', start)
        simple = '''    {
        const float *color=NULL;
        const char *label=ST_HybridHudLabel(cg.snap->ps.stHybrid.style,&color);
        if(label) {
            CG_DrawProportionalString(SCREEN_WIDTH-64,SCREEN_HEIGHT-40,label,
                                     UI_SMALLFONT|UI_DROPSHADOW,color);
            return;
        }
    }
'''
        return text[:switch] + simple + text[switch:]
    edit('codemp/cgame/cg_draw.c', hud)
    def custom_hud(text):
        text = replace(text, 'static const char *ST_HudStyle(int style, qhandle_t *icon, const float **color)',
                       'static const char *ST_HudStyle(int style, int hybrid, qhandle_t *icon, const float **color)')
        text = replace(text, '    *icon = st_hudMedia.saber; *color = st_hudCyan;\n    switch (style)',
                       '    const char *label;\n    *icon = st_hudMedia.saber; *color = st_hudCyan;\n    label=ST_HybridHudLabel(hybrid,color);if(label)return label;\n    switch (style)')
        return replace(text, 'ST_HudStyle(cg.predictedPlayerState.fd.saberDrawAnimLevel, &icon, &styleColor)',
                       'ST_HudStyle(cg.predictedPlayerState.fd.saberDrawAnimLevel, ps->stHybrid.style, &icon, &styleColor)')
    edit('codemp/cgame/cg_sabertrials_hud.inc', custom_hud)
    if kind != 'frontend':
        return
    copy('codemp/ui/ui_st_hybrid.inc', 'ui_st_hybrid.inc')
    copy('codemp/ui/ui_st_hybrid_settings.inc', 'ui_st_hybrid_settings.inc')
    edit('codemp/ui/ui_xcvar.h', lambda text: replace(text,
         'XCVAR_DEF( saberStances, "000000000000", NULL, CVAR_ARCHIVE|CVAR_USERINFO )',
         'XCVAR_DEF( saberCombatStyle, "0", NULL, CVAR_ARCHIVE|CVAR_USERINFO )\n'
         'XCVAR_DEF( saberStyleLoadout, "", NULL, CVAR_ARCHIVE|CVAR_USERINFO )\n'
         'XCVAR_DEF( ui_saberStyleSlot1, "1", NULL, CVAR_INTERNAL )\n'
         'XCVAR_DEF( ui_saberStyleSlot2, "2", NULL, CVAR_INTERNAL )\n'
         'XCVAR_DEF( ui_saberStyleSlot3, "3", NULL, CVAR_INTERNAL )\n'
         'XCVAR_DEF( st_hybridAssets, "0", NULL, CVAR_USERINFO|CVAR_ROM )\n'
         'XCVAR_DEF( ui_hybridNotice, "", NULL, CVAR_INTERNAL )\n'
         'XCVAR_DEF( saberStances, "000000000000", NULL, CVAR_ARCHIVE|CVAR_USERINFO )'))
    def main(text):
        text = replace(text, 'static void UI_UpdateSaberCvars ( void )\n{',
                       '#include "ui_st_hybrid_settings.inc"\n\nstatic void UI_UpdateSaberCvars ( void )\n{')
        return replace(text, 'static void UI_GetSaberCvars ( void )\n{',
                       'static void UI_GetSaberCvars ( void )\n{\n if(st_hybridKeepSaberDraft)return;\n ST_UIHybridGetCvar();')
    edit('codemp/ui/ui_main.c', main)
    def shell(text):
        text = replace(text, '#include "ui_st_stances.inc"', '#include "ui_st_stances.inc"\n#include "ui_st_hybrid.inc"')
        text = replace(text, ' ST_UIStanceRefresh(menu);', ' ST_UIStanceRefresh(menu);\n ST_UIHybridRefresh(menu);')
        return replace(text, '\tif (ST_UIStanceScript(name)) return qtrue;',
                       '\tif (ST_UIHybridScript(name)) return qtrue;\n\tif (ST_UIStanceScript(name)) return qtrue;')
    edit('codemp/ui/ui_sabertrials_menu.inc', shell)
    def stances(text):
        text = replace(text, 'static int st_stanceDraft[ST_STANCE_SLOTS];',
                       'static int st_stanceDraft[ST_STANCE_SLOTS];\nstatic int st_hybridLibrary;')
        text = replace(text, 'style<=2?style:0', 'style<=5?style:0')
        anchor = '        st_stanceLibrary=index>=0 && ST_StanceLibraryValid(bgAllAnims[index].anims) && ST_StanceAssetsAvailable();'
        text = replace(text, anchor, anchor + '\n        st_hybridLibrary=st_stanceLibrary && STH_AnimationsValid(bgAllAnims[index].anims);')
        anchor = '    trap->Cvar_Set("st_stanceProtocol",st_stanceLibrary?ST_STANCE_VERSION:"0");'
        text = replace(text, anchor, anchor + '\n    trap->Cvar_Set("st_hybridAssets",st_hybridLibrary?ST_HYBRID_ASSET_VERSION:"0");')
        text = replace(text, 'trap->Cvar_Set("ui_stanceStyle","0");',
                       'trap->Cvar_Set("ui_stanceStyle",va("%d",ST_UIHybridFirstStyle()-1));')
        text = replace(text, '"The selected style keeps its original combat behavior."',
                       '(slot>=3?"Ready-pose choice only. Choose combat behavior in Combat styles.":"The original style keeps its original combat behavior.")')
        text = replace(text, 'slot==0?BOTH_SABERFAST_STANCE:slot==2?BOTH_SABERSLOW_STANCE:BOTH_STAND2;',
                       '(slot==0 || slot==4)?BOTH_SABERFAST_STANCE:(slot==2 || slot==5)?BOTH_SABERSLOW_STANCE:BOTH_STAND2;')
        text = replace(text, 'slot==0?BOTH_A1_T__B_:slot==2?BOTH_A3_T__B_:BOTH_A2_T__B_;',
                       '(slot==0 || slot==4)?BOTH_A1_T__B_:(slot==2 || slot==5)?BOTH_A3_T__B_:BOTH_A2_T__B_;\n'
                       '        if(family==0 && slot>=3 && st_hybridLibrary)attack=STH_AnimForStyle(slot+1,attack);')
        return text
    edit('codemp/ui/ui_st_stances.inc', stances)


def apply_menus(root):
    root = Path(root)
    page = (SOURCE / 'hybrid.menu').read_text()
    for file, parent, mode, rect in [('saber.menu', 'saberMenu', 'Main', '446 202 170 24'),
                                     ('ingame_saber.menu', 'ingame_saber', 'Game', '215 228 180 22')]:
        path = root / 'ui/jamp' / file
        text = path.read_text()
        if mode == 'Game':
            # The former 179 row overlapped the blade-color caption at 181.
            text = replace(text, '"Stances..." rect 15 179 180 22', '"Stances..." rect 15 228 180 22')
        first, last = block_span(text, 'menuDef', parent)
        button = '''itemDef {
 name st_hybrid_options text "Combat styles..." rect ''' + rect + '''
 type ITEM_TYPE_BUTTON font 4 textscale .75 forecolor .76 .86 .93 1 visible 1
 action { close ''' + parent + '''; uiScript stHybridOpen''' + mode + '''; }
}
'''
        text = text[:last-1] + button + text[last-1:]
        text = replace(text, 'cvarFloatList { "Blue" 0 "Yellow" 1 "Red" 2 }',
                       'cvarFloatList { "Blue" 0 "Yellow" 1 "Red" 2 "Green" 3 "Purple" 4 "Orange" 5 }')
        end = text.rfind('}')
        text = text[:end] + page.replace('@PAGE@', 'st_hybrid_' + mode.lower()) + text[end:]
        path.write_text(text, newline='\n')
