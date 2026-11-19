"""DLC body compatibility, preserving the installed model archives."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent

def once(text,old,new):
    assert text.count(old)==1,old[:120]
    return text.replace(old,new)

def apply(root,role):
    root=Path(root)
    if role=='engine':
        for name in ('st_gla_compat.h','st_mirror_gla.h'):
            shutil.copyfile(HERE/name,root/'codemp/ghoul2'/name)
        # Keep the CPU palette, GPU uniform block and GLM preflight on the
        # same bound. The old 72-joint palette rejected Alien's 74-joint rig.
        p=root/'codemp/rd-rend2/tr_local.h';s=p.read_text()
        p.write_text(once(s,'#define MAX_G2_BONES  72','#define MAX_G2_BONES  128'))
        for renderer in ('rd-vanilla','rd-rend2','rd-dedicated'):
            p=root/'codemp'/renderer/'G2_API.cpp';s=p.read_text()
            start=s.index('qboolean G2API_SetBoneAnim(');end=s.index('qboolean G2API_GetBoneAnim(',start)
            part=s[start:end]
            part=once(part,'\t\t\t// ensure we flush the cache',
                '''            // Missing DLC animation frames must not replace a valid pose.
            if(startFrame<0 || startFrame>=ghlInfo->aHeader->numFrames ||
               endFrame<=0 || endFrame>ghlInfo->aHeader->numFrames ||
               (setFrame!=-1 && (setFrame<0 || setFrame>=ghlInfo->aHeader->numFrames)))return qfalse;
\t\t\t// ensure we flush the cache''')
            part=once(part,'int map[53];','int map[ST_MIRROR_MAX_BONES];')
            p.write_text(s[:start]+part+s[end:])
            p=root/'codemp'/renderer/'tr_ghoul2.cpp';s=p.read_text()
            s=once(s,'int mirrorMap[53];','int mirrorMap[ST_MIRROR_MAX_BONES];')
            s=once(s,'const bool enabled=mirror && cache.mirrorValid;',
                'const bool enabled=mirror && cache.mirrorValid && ST_MirrorGLAReflectBone(cache.header,bone);')
            p.write_text(s)
        p=root/'codemp/ghoul2/st_lock_renderer.inc';s=p.read_text()
        s=once(s,'for(int i=0;i<h->numBones;i++){mdxaBone_t m;UnCompressBone(m.matrix,mirror?map[i]:i,h,frame);if(mirror)ST_MirrorMatrix(m.matrix,m.matrix);local[i]=ST_LockMatrix(m);}',
            'for(int i=0;i<h->numBones;i++){const bool reflect=mirror && ST_MirrorGLAReflectBone(h,i);mdxaBone_t m;UnCompressBone(m.matrix,reflect?map[i]:i,h,frame);if(reflect)ST_MirrorMatrix(m.matrix,m.matrix);local[i]=ST_LockMatrix(m);}')
        p.write_text(s)
    elif role=='game':
        p=root/'codemp/game/g_client.c';s=p.read_text()
        s=once(s,'static int G_STHandAtSpawn(','''/* Validate the loaded private GLA, including any in-memory extension. Restore
 * the track immediately; this probe must not choose the player's animation. */
static qboolean G_STStanceFramesAvailable(gentity_t *ent) {
    float frame=0,speed=1;
    int first=0,end=1,flags=BONE_ANIM_OVERRIDE_FREEZE;
    qboolean had,available;
    if(!ent->ghoul2)return qfalse;
    had=trap->G2API_GetBoneAnim(ent->ghoul2,"model_root",level.time,&frame,&first,&end,&flags,&speed,NULL,0);
    available=trap->G2API_SetBoneAnim(ent->ghoul2,0,"model_root",22442,22443,
        BONE_ANIM_OVERRIDE_FREEZE,1,level.time,-1,0);
    if(available)trap->G2API_SetBoneAnim(ent->ghoul2,0,"model_root",had?first:0,had?end:1,
        had?flags:BONE_ANIM_OVERRIDE_FREEZE,had?speed:1,level.time,had&&speed?frame:-1,0);
    return available;
}

static int G_STHandAtSpawn(''')
        s=once(s,'ST_StanceLibraryValid(bgAllAnims[ent->localAnimIndex].anims) && ST_StanceAssetsAvailable();',
            'ST_StanceLibraryValid(bgAllAnims[ent->localAnimIndex].anims) && ST_StanceAssetsAvailable() &&\n           G_STStanceFramesAvailable(ent);')
        p.write_text(s)
    else:
        assert role=='frontend'
        p=root/'codemp/cgame/cg_hand_anim.inc';s=p.read_text()
        s=once(s,'''    if (!trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,next.poseFirst,next.poseEnd,
        flags,next.poseSpeed,cg.time,begin,blend)) {''', '''    {
    qboolean applied=trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,next.poseFirst,next.poseEnd,
        flags,next.poseSpeed,cg.time,begin,blend);
    /* A new model/configstring can arrive before the snapshot retiring its
     * previous ready pose. Use its stock ready pose during that transition;
     * an unavailable cosmetic idle is not a broken combat animation pack. */
    if(!applied && anim>=BOTH_ST_READY_01 && anim<=BOTH_ST_READY_15 &&
       ST_BuildDirectionalPlayback(bgAllAnims[cent->localAnimIndex].anims,
           MAX_TOTALANIMATIONS,BOTH_STAND2,mirrored,
           CG_STCanonicalSpeed(cent,BOTH_STAND2,multiplier),&next)) {
        next.semanticAnim=anim;
        begin=-1;blend=0;
        flags=(next.looping?BONE_ANIM_OVERRIDE_LOOP:BONE_ANIM_OVERRIDE_FREEZE)|(mirrored?BONE_ANIM_MIRROR:0);
        applied=trap->G2API_SetBoneAnim(cent->ghoul2,0,bone,next.poseFirst,next.poseEnd,
            flags,next.poseSpeed,cg.time,begin,blend);
    }
    if (!applied) {''')
        s=once(s,'''        if (mirrored) CG_STPoseFallback(cent,anim,"Ghoul2 mirror rejected");
        return qfalse;
    }''','''        if (mirrored) CG_STPoseFallback(cent,anim,"Ghoul2 mirror rejected");
        return qfalse;
    }
    }''')
        p.write_text(s)
        p=root/'codemp/ui/ui_st_stances.inc';s=p.read_text()
        s=once(s,'} else trap->Cvar_Set("ui_stanceSupported","0");', '''} else {
            animation_t* stock=&bgAllAnims[index].anims[BOTH_STAND2];
            trap->G2API_SetBoneAnim(item->ghoul2,0,"model_root",stock->firstFrame,stock->firstFrame+stock->numFrames,
                BONE_ANIM_OVERRIDE_FREEZE|(hand?BONE_ANIM_MIRROR:0),50.0f/stock->frameLerp,uiInfo.uiDC.realTime,-1,0);
            trap->Cvar_Set("ui_stanceSupported","0");
        }''')
        p.write_text(s)
