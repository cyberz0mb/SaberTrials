"""Independent model safety overlay; compatible with the map overlay."""
from pathlib import Path
import shutil

def apply(source):
    source=Path(source)
    for name in ('st_glm_validate.h','st_glm_read.h','st_cosmetic_spec.h','st_cosmetic_load.h','st_cosmetic_render.inc','st_surface_pool.h'):
        shutil.copyfile(Path(__file__).with_name(name),source/'codemp/rd-common'/name)
    def edit(rel,old,new):
        path=source/'codemp'/rel
        body=path.read_text(encoding='utf-8')
        if body.count(old)!=1:
            raise ValueError(f'Unexpected anchor in {rel}: {old[:70]}')
        path.write_text(body.replace(old,new),encoding='utf-8',newline='\n')
    for renderer in ('rd-vanilla','rd-dedicated'):
        rel=renderer+'/tr_model.cpp'
        edit(rel,'#include "../ghoul2/st_gla_compat.h"','#include "../ghoul2/st_gla_compat.h"\n#include "../rd-common/st_glm_read.h"')
        edit(rel,'ST_GLA_CompatRead(sModelName, ppvBuffer, stFileBytes);','ST_GLM_Preflight(sModelName, ppvBuffer, stFileBytes);\n\t\tST_GLA_CompatRead(sModelName, ppvBuffer, stFileBytes);')
    edit('rd-rend2/tr_cache.cpp','#include "../ghoul2/st_gla_compat.h"','#include "../ghoul2/st_gla_compat.h"\n#include "../rd-common/st_glm_read.h"')
    edit('rd-rend2/tr_cache.cpp','ST_GLA_CompatRead(path, ppFileBuffer, len);','ST_GLM_Preflight(path, ppFileBuffer, len, MAX_G2_BONES);\n\tST_GLA_CompatRead(path, ppFileBuffer, len);')
    edit('rd-vanilla/tr_ghoul2.cpp','RB_CheckOverflow( surface->numVerts, surface->numTriangles );','RB_CheckOverflow( surface->numVerts, surface->numTriangles * 3 );')
    # Rend2 queued pointers previously wrapped at 2048 while still in use.
    # Retain stable pages until RB_SwapBuffers resets the frame, never wrap.
    pool=(source/'codemp/rd-rend2/tr_ghoul2.cpp').read_text(encoding='utf-8')
    start=pool.index('static const int MAX_RENDERABLE_SURFACES = 2048;')
    end=pool.index('bool HackadelicOnClient',start)
    edit('rd-rend2/tr_ghoul2.cpp',pool[start:end],'''#include "../rd-common/st_surface_pool.h"
static st_models::SurfacePool<CRenderableSurface,256,256> stSurfacePool;
static CRenderableSurface *AllocGhoul2RenderableSurface()
{
    CRenderableSurface* rs=stSurfacePool.allocate();
    if(!rs) {
        ri.Error(ERR_DROP,"Saber Trials: Ghoul2 frame surface budget exceeded (65536)");
        return nullptr;
    }
    static bool reported=false;
    if(!reported && stSurfacePool.size()>2048) {
        reported=true;
        ri.Printf(PRINT_DEVELOPER,"ST_MODEL_SURFACE_POOL passed legacy 2048 surface capacity without wrap\\n");
    }
    rs->Init();
    return rs;
}
void ResetGhoul2RenderableSurfaceHeap()
{
    stSurfacePool.reset();
}

''')
    # Detailed GLMs already split into bounded draw surfaces still need every
    # surface's skin assignment. Keep this renderer-owned table off the wire.
    edit('rd-common/tr_types.h','*surfaces[128];','*surfaces[1024]; // Saber Trials: matches the validated GLM surface budget')
    edit('rd-common/tr_types.h','} skin_t;',
         '    int stCosmeticModel, stCosmeticSkin;\n    unsigned stCosmeticReported;\n    char stCosmeticClassic[MAX_QPATH];\n} skin_t;')
    for renderer in ('rd-vanilla','rd-rend2'):
        rel=renderer+'/tr_skin.cpp'
        edit(rel,'qhandle_t RE_RegisterSkin( const char *name ) {',
             '#include "../rd-common/st_cosmetic_load.h"\n\nqhandle_t RE_RegisterSkin( const char *name ) {')
        edit(rel,'return(hSkin);','if (hSkin) ST_RegisterCosmetic(skin);\n\treturn(hSkin);')
        edit(rel,'skin->numSurfaces = 0;',
             'skin->numSurfaces = 0;\n    skin->stCosmeticModel=skin->stCosmeticSkin=0;\n    skin->stCosmeticReported=0;\n    skin->stCosmeticClassic[0]=0;')
    for renderer in ('rd-vanilla','rd-rend2'):
        rel=renderer+'/tr_ghoul2.cpp'
        sig='void R_AddGhoulSurfaces( trRefEntity_t *ent ) {' if renderer=='rd-vanilla' else 'void R_AddGhoulSurfaces( trRefEntity_t *ent, int entityNum )'
        define='' if renderer=='rd-vanilla' else '#define ST_COSMETIC_REND2\n'
        edit(rel,sig,define+'#include "../rd-common/st_cosmetic_render.inc"\n\n'+sig)
        tail='\n\t}\n\n\tHackadelicOnClient = false;'
        call='\t\t\tRenderSurfaces(RS);' if renderer=='rd-vanilla' else '\t\tRenderSurfaces(RS, ent, entityNum);'+tail
        replacement='\t\t\tif (!ST_RenderCosmetic(RS,ghoul2[i],ent)) RenderSurfaces(RS);' if renderer=='rd-vanilla' else '\t\tif (!ST_RenderCosmetic(RS,g2Info,ent,entityNum)) RenderSurfaces(RS,ent,entityNum);'+tail
        edit(rel,call,replacement)
    for renderer in ('rd-vanilla','rd-rend2','rd-dedicated'):
        edit(renderer+'/tr_skin.cpp',
             '!strcmp( &surfName[strlen(surfName)-4], "_off")',
             'strlen(surfName) >= 4 && !strcmp( &surfName[strlen(surfName)-4], "_off")')
    # Empty/short names are legal; avoid reading before the string.
    for renderer in ('rd-vanilla','rd-rend2','rd-dedicated'):
        rel=renderer+'/tr_ghoul2.cpp'
        p=source/'codemp'/rel
        if not p.exists():
            rel=renderer+'/tr_model.cpp'
        body=(source/'codemp'/rel).read_text(encoding='utf-8')
        old='!strcmp( &surfInfo->name[strlen(surfInfo->name)-4],"_off")'
        if old in body:
            edit(rel,old,'strlen(surfInfo->name) >= 4 && '+old)
