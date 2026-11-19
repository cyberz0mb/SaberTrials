"""Normal-play style availability and consistent color names; no combat retuning."""
from pathlib import Path

def edit(path,old,new,count=1):
    text=path.read_text()
    assert text.count(old)==count, (path,old,text.count(old))
    path.write_text(text.replace(old,new),newline='\n')

def apply(root,kind):
    root=Path(root)
    if kind=='game':
        edit(root/'codemp/game/g_xcvar.h',
             'XCVAR_DEF( g_hybridStyles, "0",', 'XCVAR_DEF( g_hybridStyles, "1",')
    if kind!='frontend':return
    for filename in ('cg_draw.c','cg_sabertrials_hud.inc'):
        path=root/'codemp/cgame'/filename
        for old,new in (('FAST','BLUE'),('MEDIUM','YELLOW'),('STRONG','RED')):
            edit(path,'"'+old+'"','"'+new+'"')
    path=root/'codemp/cgame/cg_st_hybrid_hud.inc'
    edit(path,'    case 4:',
         '    case 1:*color=colorTable[CT_ICON_BLUE];return "BLUE";\n'
         '    case 2:*color=colorTable[CT_YELLOW];return "YELLOW";\n'
         '    case 3:*color=colorTable[CT_HUD_RED];return "RED";\n    case 4:')
    # Classic HUD used baked FAST/MEDIUM/STRONG pictures. Route stock single
    # styles through the same text renderer as the existing hybrid labels.
    edit(root/'codemp/cgame/cg_draw.c',
         'ST_HybridHudLabel(cg.snap->ps.stHybrid.style,&color)',
         'ST_HybridHudLabel(cg.snap->ps.stHybrid.style ? cg.snap->ps.stHybrid.style : '
         '(cg.predictedPlayerState.fd.saberDrawAnimLevel>=1 && '
         'cg.predictedPlayerState.fd.saberDrawAnimLevel<=3 ? '
         'cg.predictedPlayerState.fd.saberDrawAnimLevel : 0),&color)',2)

def ui(root):
    root=Path(root)
    path=root/'codemp/ui/ui_main.c'
    for old,new in (('FAST','Blue'),('MEDIUM','Yellow'),('STRONG','Red')):
        edit(path,'"@MENUS_SINGLE_'+old+'"','"Single Saber, '+new+'"')
    path=root/'codemp/ui/ui_st_hybrid.inc'
    for old,new in (('fast','Blue'),('medium','Yellow'),('strong','Red')):
        edit(path,'Original '+old+' style.','Original '+new+' style.')
