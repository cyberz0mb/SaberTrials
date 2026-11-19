"""Apply the isolated handedness overlay to freshly prepared, pinned sources."""
from pathlib import Path
import re, shutil, importlib.util

def change(source,relative,old,new,count=1):
    path=source/relative;s=path.read_text()
    if s.count(old)!=count:
        raise RuntimeError(f'Handedness hook changed: {relative}: {old[:90]!r}: {s.count(old)} != {count}')
    path.write_text(s.replace(old,new),newline='\n')

def apply(source):
    source=Path(source)
    shutil.copytree(Path(__file__).parent/'codemp',source/'codemp',dirs_exist_ok=True)
    header='codemp/ghoul2/G2.h'
    change(source,header,'#define BONE_ANIM_OVERRIDE\t',
           '#define BONE_ANIM_MIRROR 0x40000000 // Saber Trials anatomical pose reflection\n#define BONE_ANIM_OVERRIDE\t')
    change(source,header,'BONE_ANIM_OVERRIDE_FREEZE | BONE_ANIM_BLEND)',
           'BONE_ANIM_OVERRIDE_FREEZE | BONE_ANIM_BLEND | BONE_ANIM_MIRROR)')
    for renderer in ('rd-vanilla','rd-rend2','rd-dedicated'):
        rel=f'codemp/{renderer}/tr_ghoul2.cpp'
        change(source,rel,'struct SBoneCalc\n{','#include "../ghoul2/st_mirror_gla.h"\n\nstruct SBoneCalc\n{\n bool mirrored;')
        optimized=renderer=='rd-rend2'
        change(source,rel,'bone.blendLerp = par.blendLerp;' if optimized else 'mBones[index].blendLerp=par.blendLerp;',
               'bone.blendLerp = par.blendLerp;\n bone.mirrored=par.mirrored;' if optimized else 'mBones[index].blendLerp=par.blendLerp;\n mBones[index].mirrored=par.mirrored;')
        change(source,rel,'std::vector<SBoneCalc> mBones;',
               'std::vector<SBoneCalc> mBones;\n int mirrorMap[53];\n bool mirrorValid;')
        setup='\n        mirrorValid=ST_MirrorGLAMap(header,mirrorMap);\n'
        if optimized:
            change(source,rel,'\t\t\tmFinalBones[i].parent = skel->parent;\n\t\t}\n',
                   '\t\t\tmFinalBones[i].parent = skel->parent;\n\t\t}\n'+setup)
        else:change(source,rel,'\t\tmCurrentTouch=3;',setup+'\t\tmCurrentTouch=3;')
        root='SBoneCalc &TB = ghoul2.mBoneCache->Root();' if optimized else 'SBoneCalc &TB=ghoul2.mBoneCache->Root();'
        change(source,rel,root,root+'\n TB.mirrored=false;')
        transform='static void G2_TransformBone( int child, CBoneCache& BC )' if optimized else 'void G2_TransformBone (int child,CBoneCache &BC)'
        change(source,rel,transform, '''
static void ST_SampleBone(float matrix[3][4],int bone,CBoneCache& cache,int frame,bool mirror) {
    const bool enabled=mirror && cache.mirrorValid;
    UnCompressBone(matrix,enabled?cache.mirrorMap[bone]:bone,cache.header,frame);
    if(enabled) ST_MirrorMatrix(matrix,matrix);
}

'''+transform)
        if optimized:
            change(source,rel,'\t\t\tG2_TimingModel(\n\t\t\t\tbone,','\t\t\tTB.mirrored=(boneFlags & BONE_ANIM_MIRROR)!=0;\n\t\t\tG2_TimingModel(\n\t\t\t\tbone,')
        else:change(source,rel,'G2_TimingModel(boneList[boneListIndex],BC.incomingTime,BC.header->numFrames,TB.currentFrame,TB.newFrame,TB.backlerp);',
               'TB.mirrored=(boneList[boneListIndex].flags & BONE_ANIM_MIRROR)!=0;\n\t\t\tG2_TimingModel(boneList[boneListIndex],BC.incomingTime,BC.header->numFrames,TB.currentFrame,TB.newFrame,TB.backlerp);')
        path=source/rel;s=path.read_text()
        s,n=re.subn(r'UnCompressBone\(((?:tbone\[\d\]|\w+)\.matrix), child, BC\.header, (TB\.\w+)\);',r'ST_SampleBone(\1, child, BC, \2, TB.mirrored);',s)
        if n!=5:raise RuntimeError(f'Handedness sample hooks changed: {renderer}: {n}')
        path.write_text(s,newline='\n')
        api=f'codemp/{renderer}/G2_API.cpp'
        change(source,api,'qboolean G2API_SetBoneAnim(CGhoul2Info_v &ghoul2,',
               '#include "../ghoul2/st_mirror_gla.h"\n\nqboolean G2API_SetBoneAnim(CGhoul2Info_v &ghoul2,')
        change(source,api,'return G2_Set_Bone_Anim(ghlInfo, ghlInfo->mBlist, boneName, startFrame, endFrame, flags, animSpeed, currentTime, setFrame, blendTime);',
               '''if(flags & BONE_ANIM_MIRROR) {
                int map[53];
                if(!ST_MirrorGLAMap((const mdxaHeader_t*)ghlInfo->aHeader,map))return qfalse;
            }
            int appliedFlags=flags,appliedBlend=blendTime,oldFirst=0,oldEnd=0,oldFlags=0;
            float oldFrame=0,oldSpeed=0;
            if(G2_Get_Bone_Anim(ghlInfo,ghlInfo->mBlist,boneName,currentTime,
                &oldFrame,&oldFirst,&oldEnd,&oldFlags,&oldSpeed,NULL,modelIndex) &&
                ((oldFlags^flags)&BONE_ANIM_MIRROR)) {
                appliedFlags &= ~BONE_ANIM_BLEND;appliedBlend=0;
            }
            return G2_Set_Bone_Anim(ghlInfo, ghlInfo->mBlist, boneName, startFrame, endFrame, appliedFlags, animSpeed, currentTime, setFrame, appliedBlend);''')
    change(source,'codemp/ui/ui_sabertrials_menu.inc','#include "ui_sabertrials_profile.inc"',
           '#include "ui_sabertrials_profile.inc"\n#include "ui_st_handedness.inc"')
    change(source,'codemp/ui/ui_sabertrials_menu.inc','ST_UIProfilePreview( menu );',
           'ST_UIProfilePreview( menu );\n ST_UIHandPreview(menu);')
    change(source,'codemp/ui/ui_shared.c','trap->G2API_SetBoneAnim(item->ghoul2, 0, "model_root", sFrame, eFrame, flags, animSpeed, time, -1, blendTime);',
           '''if(item->window.name && !Q_stricmp(item->window.name,"st_hand_preview")) {
                                if(trap->Cvar_VariableValue("ui_saberHand")==1)flags|=BONE_ANIM_MIRROR;
                                flags|=BONE_ANIM_OVERRIDE_LOOP;
                                blendTime=0;
                            }
                            {
                                qboolean applied=trap->G2API_SetBoneAnim(item->ghoul2, 0, "model_root", sFrame, eFrame, flags, animSpeed, time, -1, blendTime);
                                if(item->window.name && !Q_stricmp(item->window.name,"st_hand_preview"))
                                    trap->Cvar_Set("ui_handSupported",applied?"1":"0");
                                if(!applied && (flags & BONE_ANIM_MIRROR))
                                    trap->G2API_SetBoneAnim(item->ghoul2, 0, "model_root", sFrame, eFrame, flags & ~BONE_ANIM_MIRROR, animSpeed, time, -1, 0);
                            }''')
    change(source,'codemp/ui/ui_shared.c','!Q_stricmp(item->window.name, "st_profile_preview") ) {',
           '(!Q_stricmp(item->window.name, "st_profile_preview") || !Q_stricmp(item->window.name,"st_hand_preview")) ) {')
    path=source/'codemp/ui/ui_saber.c';s=path.read_text();start=s.index('void UI_SaberDrawBlades(');end=s.index('void UI_SaberAttachToChar(',start)
    part=s[start:end]
    part=part.replace('&& uiInfo.movesTitleIndex == 4 /*MD_DUAL_SABERS*/','&& ((!Q_stricmp(item->window.name,"st_hand_preview")) ? !Q_stricmp(UI_Cvar_VariableString("ui_saber_type"),"dual") : uiInfo.movesTitleIndex == 4)')
    part=part.replace('UI_GetSaberForMenu( saber, saberNum );','if(!Q_stricmp(item->window.name,"st_hand_preview"))\n                trap->Cvar_VariableStringBuffer(saberNum?"ui_saber2":"ui_saber",saber,sizeof(saber));\n            else UI_GetSaberForMenu( saber, saberNum );')
    path.write_text(s[:start]+part+s[end:],newline='\n')
    spec=importlib.util.spec_from_file_location('hand_state',Path(__file__).with_name('state_hooks.py'))
    state=importlib.util.module_from_spec(spec);spec.loader.exec_module(state)
    state.apply(source,change)
    spec=importlib.util.spec_from_file_location('hand_animation',Path(__file__).with_name('animation_hooks.py'))
    animation=importlib.util.module_from_spec(spec);spec.loader.exec_module(animation)
    animation.apply(source,change)
    for name in ('lock_renderer_hooks','lock_game_hooks','integration_hooks'):
        spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
        hooks=importlib.util.module_from_spec(spec);spec.loader.exec_module(hooks)
        hooks.apply(source,change)
