// Included only by client renderer skin loaders. Dedicated never reads sidecars.
#pragma once
#include "st_cosmetic_spec.h"
static void ST_RegisterCosmetic(skin_t* skin) {
    static bool nested=false;
    // A listen server registers skins after Hunk_Clear and before the client
    // renderer is initialized again. Its old shader pointers/text are invalid.
    // Never invoke the client-only visual model loader from that server phase.
    // R_InitSkins rebuilds client skin handles during BeginRegistration.
    if(!tr.registered || nested || !skin || !skin->numSurfaces) return;
    char filename[MAX_QPATH+16];
    Com_sprintf(filename,sizeof(filename),"%s.cosmetic",skin->name);
    void* data=nullptr; const int bytes=ri.FS_ReadFile(filename,&data);
    if(!data) return;
    st_cosmetic::Spec spec={}; const bool valid=st_cosmetic::parse(data,bytes<0?0:size_t(bytes),spec);
    ri.FS_FreeFile(data);
    if(!valid) { ri.Printf(PRINT_WARNING,"ST_COSMETIC rejected sidecar %s\n",filename); return; }
    nested=true;
    const qhandle_t visual=RE_RegisterModel(spec.visual);
    const qhandle_t appearance=visual?RE_RegisterSkin(spec.skin):0;
    nested=false;
    if(!visual || !appearance) { ri.Printf(PRINT_WARNING,"ST_COSMETIC missing dependency %s\n",filename); return; }
    Q_strncpyz(skin->stCosmeticClassic,spec.classic,sizeof(skin->stCosmeticClassic));
    skin->stCosmeticModel=visual;skin->stCosmeticSkin=appearance;
    ri.Printf(PRINT_ALL,"ST_COSMETIC loaded classic=%s visual=%s skin=%s\n",spec.classic,spec.visual,spec.skin);
}
