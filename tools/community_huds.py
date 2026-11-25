"""Stage the original community combat HUDs and their namespaced client art."""
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile
import re
import hud_diagnostics

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/"assets/hud-styles/community-huds.zip"
STYLES="|2=Simple HUD|3=Jedi Outcast|4=Elegance|5=Quake"


def stage_menu(tree):
    p=tree/"codemp/ui/st_setup_catalog.h"
    lines=p.read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line.startswith((' {"st_hudStyle",',' {"st_personalHud",')) and STYLES not in line:
            assert line.count('|1=Saber Trials"')==1 and line.endswith('0,1},\n')
            lines[i]=line.replace('|1=Saber Trials"', '|1=Saber Trials'+STYLES+'"').replace('0,1},\n','0,5},\n')
    p.write_text(''.join(lines))


def compact_menu(source,style):
    body=re.sub(r'//[^\n]*','',source.replace('\r',''))
    menus=[]
    for block in re.split(r'\bmenuDef\b',body,flags=re.I)[1:]:
        name=re.search(r'\bname\s+"(left|right)hud"',block,re.I)
        if not name or name.start()>55:continue
        depth=0
        for i,c in enumerate(block):
            if c=='{':depth+=1
            if c=='}':
                depth-=1
                if depth==0:break
        block=block[:i+1].replace(name[0],f'name "st_{style}_{name[1]}"',1)
        menus.append('menuDef '+block)
    assert len(menus)==2
    return ('{\n'+'\n'.join(menus)+'\n}').replace('gfx/elegance_hud/','st_huds/elegance/').replace('gfx/tayst_hud/','st_huds/quake/').encode()


def stage_engine(tree):
    client=tree/"codemp/client"
    win=tree/"codemp/win32"
    folder=win/"community-huds"
    folder.mkdir(exist_ok=True)
    ids=[];resources=[]
    with ZipFile(ART) as z:
        for i,name in enumerate(sorted(z.namelist()),7600):
            data=z.read(name)
            if name.startswith('shaders/'):
                path=name
            elif name.startswith('ui/'):
                style='elegance' if 'elegance' in name else 'quake'
                path=f'st_huds/{style}.menu'
                data=compact_menu(data.decode(),style)
            else:
                prefix={'hud':'jk2','tayst_hud':'quake','elegance_hud':'elegance'}[name.split('/')[1]]
                path='st_huds/'+prefix+'/'+name.rsplit('/',1)[1]
            (folder/f'{i}.bin').write_bytes(data)
            ids.append(f'{{"{path}",{i}}},')
            resources.append(f'{i} RCDATA "community-huds/{i}.bin"')
    table=client/"full_ui_resources.inc"
    rows=[r for r in table.read_text().splitlines() if '"st_huds/' not in r and 'shaders/st_community_huds.shader' not in r and r.strip()]
    table.write_text('\n'.join(sorted(rows+ids,key=str.upper))+'\n')
    (win/'st_community_huds.rc').write_text('\n'.join(resources)+'\n')
    rc=win/'openjk.rc'
    if '#include "st_community_huds.rc"' not in rc.read_text():
        with rc.open('a') as f:f.write('\n#include "st_community_huds.rc"\n')
    full=client/'full_ui.inc'
    src=full.read_text()
    if 'Q_stricmpn(path,"st_huds/",8)' not in src:
        marker='if(Q_stricmpn(path,"st_outfits/",11) &&'
        assert src.count(marker)==1
        full.write_text(src.replace(marker,'if(Q_stricmp(path,"shaders/st_community_huds.shader") && Q_stricmpn(path,"st_huds/",8) && Q_stricmpn(path,"st_outfits/",11) &&'))
    stage_menu(tree)


def stage_cgame(tree):
    hud_diagnostics.stage(tree)
    cg=tree/'codemp/cgame'
    for n in ('community_hud.inc','community_hud_draw.inc'):
        copyfile(ROOT/'development-source/compatibility'/n,cg/('st_'+n))
    draw=cg/'cg_draw.c'
    source=draw.read_text()
    if 'static void CG_DrawVoteText(' not in source:
        marker = 'static void CG_DrawVote(void) {'
        helper = '''static void CG_DrawVoteText(int y, const char *text) {
    // The registered HUD font selects its high-resolution atlas at draw time.
    // Keep the whole ballot, including its totals, inside the virtual screen.
    float scale = 0.72f;
    int width = CG_Text_Width(text, scale, FONT_MEDIUM);
    if (width > SCREEN_WIDTH - 8)
        scale *= (SCREEN_WIDTH - 8) / (float)width;
    CG_Text_Paint(4, y, scale, colorWhite, text, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
}

'''
        if source.count(marker) != 1:
            raise ValueError("Missing HUD vote renderer")
        source = source.replace(marker, helper + marker)
        for row in ('58', '58 + SMALLCHAR_HEIGHT + 2', '90'):
            old = f'CG_DrawSmallString( 4, {row}, s, 1.0F );'
            if source.count(old) != 1:
                raise ValueError("Missing HUD vote line " + row)
            source = source.replace(old, f'CG_DrawVoteText({row}, s);')
        draw.write_text(source)
    if '#include "st_community_hud.inc"' in source:return
    native='if (st_hudStyle.integer == 1) { ST_DrawCombatHud(); return; }' in source
    decl='void CG_DrawHUD(centity_t\t*cent)'
    assert source.count(decl)==1
    start=source.index(decl)
    anchor='if (cg_hudFiles.integer)'
    i=source.index(anchor,start)
    var='st_hudStyle' if native else 'stCommunityHudStyle'
    source=(source[:i]+f'if (ST_DrawCommunityHud(cent,{var}.integer)) return;\n\tif ({var}.integer==2 || cg_hudFiles.integer)'+source[i+len(anchor):])
    draw.write_text(source.replace(decl,('' if native else 'extern vmCvar_t stCommunityHudStyle;\n')+'#include "st_community_hud.inc"\n'+decl))
    if not native:
        cvars=cg/'cg_cvar.c'
        s=cvars.read_text()
        if 'vmCvar_t stCommunityHudStyle;' in s:return
        for name in ('Register','Update'):
            marker=f'void CG_{name}Cvars( void ) {{'
            assert s.count(marker)==1
            if name=='Register':
                s=s.replace(marker,'vmCvar_t stCommunityHudStyle;\n'+marker+'\n\ttrap->Cvar_Register(&stCommunityHudStyle,"st_personalHud","0",CVAR_ARCHIVE);')
            else:s=s.replace(marker,marker+'\n\ttrap->Cvar_Update(&stCommunityHudStyle);')
        cvars.write_text(s)
