// Geometry substitution at draw submission only. Never edits CGhoul2Info,
// its cache, bolts, surface overrides, collision model, or server state.
#include "../rd-common/st_cosmetic_spec.h"
static mdxmHeader_t* ST_CosmeticHeader(model_t* m) {
    if(!m || m->type!=MOD_MDXM) return nullptr;
#ifdef ST_COSMETIC_REND2
    return m->data.glm->header;
#else
    return m->mdxm;
#endif
}
static const mdxmSurfHierarchy_t* ST_CosmeticSurface(const mdxmHeader_t* h,int index) {
    const auto* offsets=reinterpret_cast<const mdxmHierarchyOffsets_t*>(h+1);
    return reinterpret_cast<const mdxmSurfHierarchy_t*>(reinterpret_cast<const byte*>(offsets)+offsets->offsets[index]);
}
static bool ST_CosmeticOverrides(const CGhoul2Info& g,const skin_t* skin,const mdxmHeader_t* h) {
    // Only accept the exact on/off state specified by this canonical skin.
    // Dismemberment, generated surfaces and ad-hoc visibility changes fall back.
    for(const auto& state:g.mSlist) {
        if(state.surface==-1) continue; // unused override slot
        if(state.surface<0 || state.surface>=h->numSurfaces) return false;
        const auto* surface=ST_CosmeticSurface(h,state.surface);
        int expected=surface->flags;
        for(int i=0;i<skin->numSurfaces;++i) if(!strcmp(surface->name,skin->surfaces[i]->name)) {
            expected=!strcmp(static_cast<const shader_t*>(skin->surfaces[i]->shader)->name,"*off")?G2SURFACEFLAG_OFF:0;
            break;
        }
        if(state.offFlags!=expected) return false;
    }
    return true;
}
static bool ST_RenderCosmetic(CRenderSurface& original,CGhoul2Info& g,trRefEntity_t* ent
#ifdef ST_COSMETIC_REND2
    ,int entityNum
#endif
) {
    static cvar_t* enabled=ri.Cvar_Get("r_enhancedModels","0",CVAR_ARCHIVE,"Enable validated cosmetic character meshes");
    skin_t* skin=original.skin;
    if(!skin || !skin->stCosmeticModel) return false;
    model_t* visual=R_GetModelByHandle(skin->stCosmeticModel);
    unsigned reason=st_cosmetic::reject(enabled->integer!=0,
        !Q_stricmp(original.currentModel->name,skin->stCosmeticClassic),g.mSurfaceRoot,
        g.mGoreSetTag!=0,r_shadows->integer,original.lod,original.cust_shader!=nullptr,visual?visual->numLods:0);
// ST_VANILLA_COMPAT_BEGIN
#ifndef ST_COSMETIC_REND2
    // Dense cosmetic meshes require Rend2 GPU skinning. The tested twelve-NPC
    // CPU path falls below 60 FPS even at the coarsest authored LOD. Keep the
    // canonical mesh here without changing collision, bolts or user settings.
    if(!reason) {
        reason=1u<<17; // outside policy bits 0..8 and LOD diagnostic bits 9..16
        if(!(skin->stCosmeticReported&reason))
            ri.Printf(PRINT_ALL,"Saber Trials: enhanced character geometry requires Rend2; using classic model %s.\n",skin->stCosmeticClassic);
    }
#endif
// ST_VANILLA_COMPAT_END
    mdxmHeader_t* a=ST_CosmeticHeader(original.currentModel);
    mdxmHeader_t* b=ST_CosmeticHeader(visual);
    if(!reason && (!a || !b || a->animIndex!=b->animIndex || a->numBones!=b->numBones ||
        ST_CosmeticSurface(b,0)->parentIndex!=-1)) reason=st_cosmetic::skeleton;
    if(!reason && !ST_CosmeticOverrides(g,skin,a)) reason=st_cosmetic::overrides;
    if(reason) {
        if(!(skin->stCosmeticReported&reason)) {
            skin->stCosmeticReported|=reason;
            ri.Printf(PRINT_DEVELOPER,"ST_COSMETIC fallback classic=%s reason=%u\n",skin->stCosmeticClassic,reason);
        }
        return false;
    }
    surfaceInfo_v empty;
    G2_FindOverrideSurface(-1,empty);
    const int visualLod=G2_ComputeLOD(ent,visual,g.mLodBias);
    CRenderSurface draw(0,empty,original.cust_shader,original.fogNum,original.personalModel,
        original.boneCache,original.renderfx,R_GetSkinByHandle(skin->stCosmeticSkin),visual,visualLod,original.boltList
#ifdef _G2_GORE
        ,nullptr,nullptr
#endif
    );
#ifdef ST_COSMETIC_REND2
    RenderSurfaces(draw,ent,entityNum);
#else
    RenderSurfaces(draw);
#endif
    const unsigned reportedBit=512u<<visualLod; // validated maximum: eight LODs
    if(!(skin->stCosmeticReported&reportedBit)) {
        skin->stCosmeticReported|=reportedBit;
        ri.Printf(PRINT_ALL,"ST_COSMETIC draw classic=%s visual=%s surfaces=%d lod=%d collision=classic bolts=classic\n",
            original.currentModel->name,visual->name,b->numSurfaces,visualLod);
    }
    return true;
}
