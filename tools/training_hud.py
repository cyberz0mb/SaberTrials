"""Expose optional movement readouts in the existing Interface settings."""
from pathlib import Path
from shutil import copyfile

OPTIONS=(
    ("st_trainStrafe","Strafe guide","Target angles for standard JKA ground and air acceleration."),
    ("st_trainSnap","SnapHUD","Horizontal velocity rounding zones for your current movement step."),
    ("st_trainPitch","Pitch guide","View pitch in degrees and a level marker."),
    ("st_trainSpeed","Speedometer","Horizontal speed in game units per second."),
    ("st_trainKeys","Movement keys","Forward, left, back, right, jump and crouch input."),
)

def stage_menu(tree):
    path=tree/"codemp/ui/st_setup_catalog.h"
    source=path.read_text()
    marker="};\nstatic const int SS_COUNT="
    if OPTIONS[0][0] in source:return
    if source.count(marker)!=1:raise ValueError("Setup catalog changed")
    rows=[f' {{"{name}","{label}","Movement training","{help}","0=Off|1=On","0",2,1,0,0,CVAR_ARCHIVE,0,1}},' for name,label,help in OPTIONS]
    path.write_text(source.replace(marker,"\n".join(rows)+"\n"+marker))

def stage_engine(tree):
    client=tree/"codemp/client"
    copyfile(Path(__file__).resolve().parents[1]/"development-source/compatibility/training_hud.inc",client/"st_training_hud.inc")
    p=client/"cl_scrn.cpp"
    s=p.read_text()
    if '#include "st_training_hud.inc"' not in s:
        marker="void SCR_DrawScreenField( stereoFrame_t stereoFrame ) {"
        draw="case CA_ACTIVE:\n\t\t\tCL_CGameRendering( stereoFrame );"
        if s.count(marker)!=1 or s.count(draw)!=1:raise ValueError("Screen renderer entry point changed")
        p.write_text(s.replace(marker,'#include "st_training_hud.inc"\n'+marker).replace(draw,draw+"\n            ST_DrawTrainingHud();"))
    stage_menu(tree)
