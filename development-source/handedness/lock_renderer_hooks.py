"""Native renderer lock-pose API and shared pose sampling hooks.

Called after the handedness sampler hooks on a freshly prepared source tree.
Does not touch game/cgame/UI gameplay callers or installed binaries.
"""
from pathlib import Path
import re

def _function_end(text, start):
    """Locate a C++ function's closing brace, ignoring comments and literals."""
    pos=text.index('{',start);depth=0;mode='code';escape=False;i=pos
    while i<len(text):
        c=text[i];n=text[i+1] if i+1<len(text) else ''
        if mode=='line':
            if c=='\n':mode='code'
        elif mode=='block':
            if c=='*' and n=='/':mode='code';i+=1
        elif mode in ('"',"'"):
            if escape:escape=False
            elif c=='\\':escape=True
            elif c==mode:mode='code'
        elif c=='/' and n=='/':mode='line';i+=1
        elif c=='/' and n=='*':mode='block';i+=1
        elif c in ('"',"'"):mode=c
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return i+1
        i+=1
    raise RuntimeError('Lock hook: unterminated source function')

def apply(source,change):
    source=Path(source)
    if '(*G2API_STLockPose)' in (source/'codemp/rd-common/tr_public.h').read_text():
        raise RuntimeError('Lock renderer hooks already applied; prepare a fresh source tree')
    # Public C contract has no C++ types. Native APIs append fields and bump
    # their explicit version rather than silently reinterpreting old DLL tables.
    for rel,version,struct in (
        ('codemp/rd-common/tr_public.h','REF_API_VERSION','refexport_t'),
        ('codemp/game/g_public.h','GAME_API_VERSION','gameImport_t'),
        ('codemp/cgame/cg_public.h','CGAME_API_VERSION','cgameImport_t'),
        ('codemp/ui/ui_public.h','UI_API_VERSION','uiImport_t'),
    ):
        p=source/rel;s=p.read_text();pattern=rf'(#define\s+{version}\s+)(\d+)'
        s,n=re.subn(pattern,lambda m:m[1]+str(int(m[2])+1),s)
        if n!=1:raise RuntimeError(f'Lock hook: {version} version anchor changed')
        s='#include "ghoul2/st_lock_pose.h"\n'+s
        signature='CGhoul2Info_v &ghoul2' if struct=='refexport_t' else 'void *ghoul2'
        marker='} '+struct+';'
        if s.count(marker)!=1:raise RuntimeError(f'Lock hook: {struct} append anchor changed')
        addition=f'\tqboolean (*G2API_STLockPose)({signature}, const stLockPoseParams_t *params);\n'
        if struct=='gameImport_t':addition+='\tqboolean (*G2API_GetBoneFrame)(void *ghoul2, const char *boneName, const int currentTime, float *currentFrame, int *modelList, const int modelIndex);\n'
        s=s.replace(marker,addition+marker);p.write_text(s,newline='\n')

    rel='codemp/ghoul2/ghoul2_shared.h'
    change(source,rel,'#include <vector>','#include "ghoul2/st_lock_pose.h"\n#include <vector>')
    change(source,rel,'\tconst mdxaHeader_t\t*aHeader;',
        '\tconst mdxaHeader_t\t*aHeader;\n\tbool mSTLockActive;\n\tint mSTLockOwner;\n\tstLockPoseParams_t mSTLockParams;\n\tmdxaBone_t mSTLockLocal[53];')
    change(source,rel,'\taHeader(0)','\taHeader(0),\n\tmSTLockActive(false),\n\tmSTLockOwner(-1)')
    change(source,rel,'\t\tmFileName[0] = 0;',
        '\t\tmFileName[0] = 0;\n\t\tmemset(&mSTLockParams,0,sizeof(mSTLockParams));\n\t\tmemset(mSTLockLocal,0,sizeof(mSTLockLocal));')
    # These fields are outside the existing raw save range. Value copies own
    # independent pose arrays. Bone-cache runtime is rebuilt after DeepCopy.
    change(source,'codemp/ghoul2/g2_local.h','class CGhoul2Info_v\n{',
        'class CGhoul2Info_v\n{') # Assert the expected lifecycle implementation.
    change(source,'codemp/ghoul2/g2_local.h','\t\t\t\tArray()[i].mMeshFrameNum=0;',
        '\t\t\t\tArray()[i].mMeshFrameNum=0;\n\t\t\t\tArray()[i].mSTLockActive=false;\n\t\t\t\tArray()[i].mSTLockOwner=-1;')
    rel='codemp/ghoul2/g2_local.h';s=(source/rel).read_text()
    anchor='qboolean\tG2API_AttachG2Model('
    if s.count(anchor)!=1:raise RuntimeError('Lock hook: native G2 declaration anchor changed')
    s=s.replace(anchor,'qboolean G2API_STLockPose(CGhoul2Info_v &ghoul2,const stLockPoseParams_t *params);\n'+anchor)
    (source/rel).write_text(s,newline='\n')

    for renderer in ('rd-vanilla','rd-rend2','rd-dedicated'):
        rel=f'codemp/{renderer}/tr_ghoul2.cpp';p=source/rel;s=p.read_text()
        anchor='#include "../ghoul2/st_mirror_gla.h"'
        if s.count(anchor)!=1:raise RuntimeError('Lock hook: expected handedness sampler first')
        s=s.replace(anchor,anchor+'\n#include <memory>\nstruct STLockRuntime;')
        anchor='std::vector<SBoneCalc> mBones;'
        s=s.replace(anchor,anchor+'\n const mdxaBone_t *stLockLocal;\n float stLockWeight;\n std::shared_ptr<STLockRuntime> stLockRuntime;\n std::shared_ptr<STLockRuntime> stLockValidatedRuntime;')
        # Both renderer implementations initialize mSmoothingActive in the
        # CBoneCache constructor; replace only its first occurrence after class.
        start=s.index('class CBoneCache\n{');at=s.index('mSmoothingActive',s.index('CBoneCache(',start))
        assignment_end=s.index(';',at)+1
        s=s[:assignment_end]+'\n        stLockLocal=NULL;stLockWeight=0;'+s[assignment_end:]
        signature='static void G2_TransformBone( int child, CBoneCache& BC )' if renderer=='rd-rend2' else 'void G2_TransformBone (int child,CBoneCache &BC)'
        if s.count(signature)!=1:raise RuntimeError(f'Lock hook: transform anchor changed: {renderer}')
        begin=s.index(signature);end=_function_end(s,begin)
        original=s[begin:end].replace('G2_TransformBone','G2_TransformBoneNormal',1)
        wrapper=signature+''' {
    if(!BC.stLockLocal || BC.stLockWeight<1.0f)G2_TransformBoneNormal(child,BC);
    ST_LockApplyFinal(child,BC);
}
'''
        s=s[:begin]+'static void ST_LockApplyFinal(int child,CBoneCache& cache);\n'+original+'\n'+wrapper+s[end:]
        root='SBoneCalc &TB = ghoul2.mBoneCache->Root();' if renderer=='rd-rend2' else 'SBoneCalc &TB=ghoul2.mBoneCache->Root();'
        if s.count(root)!=1:raise RuntimeError(f'Lock hook: cache root anchor changed: {renderer}')
        setup='''ghoul2.mBoneCache->stLockLocal=ghoul2.mSTLockActive?ghoul2.mSTLockLocal:NULL;
    ghoul2.mBoneCache->stLockWeight=ghoul2.mSTLockActive?ghoul2.mSTLockParams.weight:0;
    if(ghoul2.mSTLockActive)ghoul2.mBoneCache->mSmoothingActive=false;
    '''
        s=s.replace(root,setup+root)
        # A raw CBoneCache memcpy would copy std::vector and shared_ptr ownership.
        # This optional listen-server path must use ordinary C++ value copying.
        if 'memcpy(to, from, sizeof(CBoneCache));' in s:s=s.replace('memcpy(to, from, sizeof(CBoneCache));','*to = *from;')
        accessor='((m)->data.glm->header)' if renderer=='rd-rend2' else '((m)->mdxm)'
        s+=f'\n#define ST_LOCK_MODEL_HEADER(m) {accessor}\n#include "../ghoul2/st_lock_renderer.inc"\n#undef ST_LOCK_MODEL_HEADER\n';p.write_text(s,newline='\n')
        # CopySpecific historically retained source cache pointers after value
        # assignment. Explicitly detach transient caches for independently owned
        # copies, as DeepCopy already does. The pose array itself copies by value.
        change(source,f'codemp/{renderer}/G2_API.cpp',
            '\t\tghoul2To[modelTo] = ghoul2From[modelFrom];',
            '\t\tghoul2To[modelTo] = ghoul2From[modelFrom];\n\t\tghoul2To[modelTo].mBoneCache=0;\n\t\tghoul2To[modelTo].mTransformedVertsArray=0;\n\t\tghoul2To[modelTo].mSkelFrameNum=-1;\n\t\tghoul2To[modelTo].mMeshFrameNum=-1;\n\t\tghoul2To[modelTo].mSTLockActive=false;\n\t\tghoul2To[modelTo].mSTLockOwner=-1;')
        api=source/f'codemp/{renderer}/G2_API.cpp';a=api.read_text()
        a=a.replace('CGhoul2Info *serverInstance = &ghoul2[modelIndex];','CGhoul2Info *serverInstance = &ghoul2[modelIndex];\n\tif(serverInstance->mSTLockActive)return qfalse;')
        a=a.replace('clientInstance = &g2Ref[0];','clientInstance = &g2Ref[0];\n\tif(clientInstance->mSTLockActive)return qfalse;')
        api.write_text(a,newline='\n')
        rel=f'codemp/{renderer}/tr_init.cpp'
        if renderer=='rd-dedicated':
            # Dedicated exports are registered in tr_init.cpp too in this pin.
            if not (source/rel).exists():raise RuntimeError('Lock hook: dedicated export file changed')
        p=source/rel;s=p.read_text();anchor='re.G2API_SetBoneAnim'
        at=s.index(anchor);s=s[:at]+'re.G2API_STLockPose = G2API_STLockPose;\n\t'+s[at:];p.write_text(s,newline='\n')

    for rel,prefix,table in (
        ('codemp/client/cl_cgameapi.cpp','CL','cgi'),
        ('codemp/client/cl_uiapi.cpp','CL','uii'),
        ('codemp/server/sv_gameapi.cpp','SV','gi'),
    ):
        p=source/rel;s=p.read_text();anchor=f'static qboolean {prefix}_G2API_SetBoneAnim'
        at=s.index(anchor);wrapper=f'''static qboolean {prefix}_G2API_STLockPose(void *ghoul2,const stLockPoseParams_t *params) {{
    if(!ghoul2)return qfalse;
    return re->G2API_STLockPose(*((CGhoul2Info_v*)ghoul2),params);
}}

'''
        if prefix=='SV':wrapper+='''static qboolean SV_G2API_GetBoneFrame(void *ghoul2,const char *boneName,const int currentTime,float *currentFrame,int *modelList,const int modelIndex) {
    if(!ghoul2)return qfalse;int first=0,last=0,flags=0;float speed=0;
    return re->G2API_GetBoneAnim(*((CGhoul2Info_v*)ghoul2),modelIndex,boneName,currentTime,currentFrame,&first,&last,&flags,&speed,modelList);
}

'''
        s=s[:at]+wrapper+s[at:];at=s.index(f'{table}.G2API_SetBoneAnim')
        assignments=f'{table}.G2API_STLockPose = {prefix}_G2API_STLockPose;\n\t\t'
        if prefix=='SV':assignments+=f'{table}.G2API_GetBoneFrame = SV_G2API_GetBoneFrame;\n\t\t'
        s=s[:at]+assignments+s[at:];p.write_text(s,newline='\n')
