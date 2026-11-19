"""Apply the Enhanced Maps changes to the pinned Saber Trials engine tree."""
from pathlib import Path
import re
import shutil


def apply_bounds(source):
    for name, old, new in (
        ("codemp/qcommon/q_shared.h", "( 64 * 1024 )", "( 128 * 1024 )"),
        ("codemp/qcommon/q_shared.h", "( -64 * 1024 )", "( -128 * 1024 )"),
        ("shared/qcommon/q_math.c", "mins[0] = mins[1] = mins[2] = 100000;",
         "mins[0] = mins[1] = mins[2] = 262144;"),
        ("shared/qcommon/q_math.c", "maxs[0] = maxs[1] = maxs[2] = -100000;",
         "maxs[0] = maxs[1] = maxs[2] = -262144;"),
    ):
        path = source / name
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise ValueError(f"Unexpected bounds definition in {name}: {old}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


def apply(source):
    mp = source / "codemp"
    for name, folder in (("st_bsp_validate.h", "qcommon"), ("st_bsp_read.h", "rd-common")):
        shutil.copyfile(Path(__file__).with_name(name), mp / folder / name)

    def edit(path, before, after):
        target = source / path
        body = target.read_text(encoding="utf-8")
        pattern = "".join(r"[ \t]+" if part and part[0] in " \t" else re.escape(part)
                          for part in re.split(r"([ \t]+)", before))
        result, count = re.subn(pattern, lambda _: after, body)
        if count != 1:
            raise ValueError(f"Unexpected source anchor in {path}: {before[:120]!r}")
        target.write_text(result, encoding="utf-8", newline="\n")

    def mpedit(path, before, after):
        edit("codemp/" + path, before, after)

    # World constants are also used for global fog and NPC ground searches.
    apply_bounds(source)

    mpedit("qcommon/cm_local.h", "typedef struct clipMap_s {",
           "typedef struct clipMap_s {\n\tbool enhancedMap;")
    mpedit("qcommon/cm_public.h", "int\t\t\tCM_NumInlineModels( void );",
           "int\t\t\tCM_NumInlineModels( void );\nqboolean CM_EnhancedMap( void );\n"
           "const char *CM_CheckMap( const char *name );")
    cm = "qcommon/cm_load.cpp"
    mpedit(cm, '#include "qcommon/qfiles.h"',
           '#include "qcommon/qfiles.h"\n#include "cm_patch.h"\n#include "st_bsp_validate.h"')
    mpedit(cm, "int\t\tCM_NumInlineModels( void ) {",
           "qboolean CM_EnhancedMap( void ) {\n\treturn cmg.enhancedMap ? qtrue : qfalse;\n}\n\n"
           "int\t\tCM_NumInlineModels( void ) {")
    mpedit(cm, "\t\tpatch->pc = CM_GeneratePatchCollide( width, height, points );",
           """		// Generate facets in patch-local coordinates to preserve the winding
		// and bevel tolerances when the patch is far from the world origin.
		vec3_t origin;
		VectorCopy(points[0], origin);
		if (cm.enhancedMap) {
			for (j = 0; j < c; ++j)
				VectorSubtract(points[j], origin, points[j]);
		}
		patch->pc = CM_GeneratePatchCollide( width, height, points );
		if (cm.enhancedMap) {
			for (j = 0; j < patch->pc->numPlanes; ++j) {
				float *plane = patch->pc->planes[j].plane;
				plane[3] += DotProduct(plane, origin);
			}
			VectorAdd(patch->pc->bounds[0], origin, patch->pc->bounds[0]);
			VectorAdd(patch->pc->bounds[1], origin, patch->pc->bounds[1]);
		}""")
    mpedit(cm, "static unsigned\tlast_checksum;", "static unsigned\tlast_checksum;\n\tint version = 0;")
    mpedit(cm, "static void CM_LoadMap_Actual(", """#ifndef BSPC
static const char *CM_ReadBSP(const char *name, void *&buffer, int &length, int &version) {
	fileHandle_t file;
	length = FS_FOpenFileRead(name, &file, qfalse);
	if (!file)
		return "BSP file not found";
	if (length < int(sizeof(dheader_t)) || length > st_bsp::maxFileBytes) {
		FS_FCloseFile(file);
		return "invalid BSP file length";
	}
	buffer = Z_Malloc(length, TAG_BSP_DISKIMAGE);
	const int bytes = FS_Read(buffer, length, file);
	FS_FCloseFile(file);
	return bytes == length ? st_bsp::Validate(buffer, length, version) : "short BSP read";
}

const char *CM_CheckMap(const char *name) {
	void *buffer = nullptr;
	int length, version;
	const char *error = CM_ReadBSP(name, buffer, length, version);
	Z_Free(buffer);
	return error;
}
#endif

static void CM_LoadMap_Actual(""")
    mpedit(cm, """	buf = NULL;
	fileHandle_t h;
	const int iBSPLen = FS_FOpenFileRead( name, &h, qfalse );
	if (h)
	{
		newBuff = Z_Malloc( iBSPLen, TAG_BSP_DISKIMAGE );
		FS_Read( newBuff, iBSPLen, h);
		FS_FCloseFile( h );

		buf = (int*) newBuff;	// so the rest of the code works as normal
		if (&cm == &cmg)
		{
			gpvCachedMapDiskImage = newBuff;
			newBuff = 0;
		}

		// carry on as before...
		//
	}""",
           """	int iBSPLen;
	const char *error = CM_ReadBSP(name, newBuff, iBSPLen, version);
	if (error || (version == ST_BSP_VERSION && &cm != &cmg && !cmg.enhancedMap)) {
		Z_Free(newBuff);
		gbUsingCachedMapDataRightNow = qfalse;
		Com_Error(ERR_DROP, "%s: %s", name, error ? error : "enhanced sub-BSP requires an enhanced main map");
	}
	cm.enhancedMap = version == ST_BSP_VERSION;
	buf = static_cast<int *>(newBuff);
	if (&cm == &cmg) {
		gpvCachedMapDiskImage = newBuff;
		newBuff = nullptr;
	}""")
    mpedit(cm, """	if ( header.version != BSP_VERSION ) {
		Z_Free(	gpvCachedMapDiskImage);
				gpvCachedMapDiskImage = NULL;

		Com_Error (ERR_DROP, "CM_LoadMap: %s has wrong version number (%i should be %i)"
		, name, header.version, BSP_VERSION );
	}""", """#ifdef BSPC
	if (const char *error = st_bsp::Validate(buf, iBSPLen, version))
		Com_Error(ERR_DROP, "%s: %s", name, error);
	cm.enhancedMap = version == ST_BSP_VERSION;
#endif""")
    # Inline models used pointer subtraction across separate heap allocations.
    # Keep their synthetic leaf references in the same arrays as disk leaves.
    mpedit(cm, "int\t\t\t\ti, j, count;\n\tint\t\t\t\t*indexes;",
           "int\t\t\t\ti, j, count;\n\tint extraBrush = cm.numLeafBrushes + BOX_BRUSHES;\n"
           "\tint extraSurface = cm.numLeafSurfaces;\n\tint *indexes;")
    mpedit(cm, """		indexes = (int *)Hunk_Alloc( out->leaf.numLeafBrushes * 4, h_high );
		out->leaf.firstLeafBrush = indexes - cm.leafbrushes;""",
           """		out->leaf.firstLeafBrush = extraBrush;
		indexes = cm.leafbrushes + extraBrush;
		extraBrush += out->leaf.numLeafBrushes;""")
    mpedit(cm, """		indexes = (int *)Hunk_Alloc( out->leaf.numLeafSurfaces * 4, h_high );
		out->leaf.firstLeafSurface = indexes - cm.leafsurfaces;""",
           """		out->leaf.firstLeafSurface = extraSurface;
		indexes = cm.leafsurfaces + extraSurface;
		extraSurface += out->leaf.numLeafSurfaces;""")
    mpedit(cm, """	CMod_LoadLeafBrushes (&header.lumps[LUMP_LEAFBRUSHES], cm);
	CMod_LoadLeafSurfaces (&header.lumps[LUMP_LEAFSURFACES], cm);""",
           """	int extraBrushes = 0, extraSurfaces = 0;
	const lump_t &models = header.lumps[LUMP_MODELS];
	const dmodel_t *diskModels = reinterpret_cast<const dmodel_t *>(cmod_base + models.fileofs);
	for (int i = (&cm == &cmg) ? 1 : 0; i < models.filelen / int(sizeof(dmodel_t)); ++i) {
		extraBrushes += LittleLong(diskModels[i].numBrushes);
		extraSurfaces += LittleLong(diskModels[i].numSurfaces);
	}
	CMod_LoadLeafBrushes (&header.lumps[LUMP_LEAFBRUSHES], cm, extraBrushes);
	CMod_LoadLeafSurfaces (&header.lumps[LUMP_LEAFSURFACES], cm, extraSurfaces);""")
    mpedit(cm, "CMod_LoadLeafBrushes (const lump_t *l, clipMap_t &cm)",
           "CMod_LoadLeafBrushes (const lump_t *l, clipMap_t &cm, int extra)")
    mpedit(cm, "(count + BOX_BRUSHES) * sizeof( *cm.leafbrushes )",
           "(count + BOX_BRUSHES + extra) * sizeof( *cm.leafbrushes )")
    mpedit(cm, "CMod_LoadLeafSurfaces( const lump_t *l, clipMap_t &cm )",
           "CMod_LoadLeafSurfaces( const lump_t *l, clipMap_t &cm, int extra )")
    mpedit(cm, "count * sizeof( *cm.leafsurfaces )", "(count + extra + 1) * sizeof( *cm.leafsurfaces )")

    # Use a connect-only capability key and keep protocol 26 on both map types.
    mpedit("client/cl_main.cpp", '#include "client.h"',
           '#include "client.h"\n#include "../qcommon/st_bsp_validate.h"')
    mpedit("client/cl_main.cpp", '\t\tInfo_SetValueForKey( info, "challenge", va("%i", clc.challenge ) );',
           '\t\tInfo_SetValueForKey( info, "challenge", va("%i", clc.challenge ) );\n'
           '\t\tInfo_SetValueForKey( info, ST_BSP_CAPABILITY_KEY, ST_BSP_CAPABILITY );')
    mpedit("server/server.h", "clientState_t\tstate;",
           "clientState_t\tstate;\n\tqboolean supportsEnhancedMaps;")
    for path in ("server/sv_client.cpp", "server/sv_init.cpp"):
        mpedit(path, '#include "server.h"', '#include "server.h"\n#include "../qcommon/st_bsp_validate.h"')
    mpedit("server/sv_client.cpp", '#include "../qcommon/st_bsp_validate.h"',
           '#include "../qcommon/st_bsp_validate.h"\n#include "../qcommon/cm_public.h"')
    mpedit("server/sv_client.cpp", '\tchallenge = atoi( Info_ValueForKey( userinfo, "challenge" ) );',
           """	const qboolean enhanced = !strcmp(Info_ValueForKey(userinfo, ST_BSP_CAPABILITY_KEY),
	                                  ST_BSP_CAPABILITY) ? qtrue : qfalse;
	if (CM_EnhancedMap() && !enhanced && !NET_IsLocalAddress(from)) {
		NET_OutOfBandPrint(NS_SERVER, from, "print\\n%s\\n", ST_BSP_REQUIREMENT);
		return;
	}
	Info_RemoveKey(userinfo, ST_BSP_CAPABILITY_KEY);
	challenge = atoi( Info_ValueForKey( userinfo, "challenge" ) );""")
    mpedit("server/sv_client.cpp", "\t*newcl = temp;",
           "\t*newcl = temp;\n\tnewcl->supportsEnhancedMaps = NET_IsLocalAddress(from) ? qtrue : enhanced;")
    mpedit("server/sv_init.cpp", '\tCvar_Set( "mapname", server );',
           '\tCvar_Set( "mapname", server );\n'
           '\tCvar_Set( "sv_stMap", CM_EnhancedMap() ? ST_BSP_CAPABILITY : "" );')
    mpedit("server/sv_init.cpp", '\tCvar_Get ("protocol", va("%i", PROTOCOL_VERSION), CVAR_SERVERINFO | CVAR_ROM);',
           '\tCvar_Get ("protocol", va("%i", PROTOCOL_VERSION), CVAR_SERVERINFO | CVAR_ROM);\n'
           '\tCvar_Get ("sv_stMap", "", CVAR_SERVERINFO | CVAR_ROM);')
    mpedit("server/sv_init.cpp", """			// connect the client again
			denied = GVM_ClientConnect( i, qfalse, isBot );""",
           """			if (CM_EnhancedMap() && !isBot && !svs.clients[i].supportsEnhancedMaps) {
				SV_DropClient(&svs.clients[i], ST_BSP_REQUIREMENT);
				continue;
			}
			// connect the client again
			denied = GVM_ClientConnect( i, qfalse, isBot );""")
    mpedit("server/sv_ccmds.cpp", """	if ( FS_ReadFile (expanded, NULL) == -1 ) {
		Com_Printf ("Can't find map %s\\n", expanded);
		return;
	}""", """	// Dedicated OpenJK promotes ERR_DROP to fatal. Reject malformed map
	// data here, before tearing down a running match.
	if (const char *error = CM_CheckMap(expanded)) {
		Com_Printf("%s: %s\\n", expanded, error);
		return;
	}""")
    mpedit("server/sv_ccmds.cpp", '#include "server.h"',
           '#include "server.h"\n#include "qcommon/cm_public.h"')

    for renderer in ("rd-vanilla", "rd-rend2"):
        apply_renderer(renderer, mpedit)


def apply_renderer(renderer, edit):
    bsp = renderer + "/tr_bsp.cpp"
    local = renderer + "/tr_local.h"
    main = renderer + "/tr_main.cpp"
    vanilla = renderer == "rd-vanilla"
    edit(bsp, '#include "tr_local.h"', '#include "tr_local.h"\n#include "../qcommon/st_bsp_validate.h"')
    world = "w" if vanilla else "worldData"
    declaration = "vec3_t\tmaxs;\n\tworld_t\t*w;\n\tfloat\t*wMins, *wMaxs;" if vanilla else (
        "vec3_t\tmaxs;\n\tfloat\t*wMins, *wMaxs;")
    edit(bsp, declaration, "world_t *w;" if vanilla else "")
    old = f"""	{world}->lightGridInverseSize[0] = 1.0{' ' if vanilla else 'f '}/ {world}->lightGridSize[0];
	{world}->lightGridInverseSize[1] = 1.0{' ' if vanilla else 'f '}/ {world}->lightGridSize[1];
	{world}->lightGridInverseSize[2] = 1.0{' ' if vanilla else 'f '}/ {world}->lightGridSize[2];

	wMins = {world}->bmodels[0].bounds[0];
	wMaxs = {world}->bmodels[0].bounds[1];

	for ( i = 0 ; i < 3 ; i++ ) {{
		{world}->lightGridOrigin[i] = {world}->lightGridSize[i] * ceil( wMins[i] / {world}->lightGridSize[i] );
		maxs[i] = {world}->lightGridSize[i] * floor( wMaxs[i] / {world}->lightGridSize[i] );
		{world}->lightGridBounds[i] = (maxs[i] - {world}->lightGridOrigin[i])/{world}->lightGridSize[i] + 1;
	}}"""
    edit(bsp, old, f"""	if (!st_bsp::GridLayout({world}->bmodels[0].bounds[0], {world}->bmodels[0].bounds[1],
	                        {world}->lightGridSize, {world}->lightGridOrigin,
	                        {world}->lightGridInverseSize, {world}->lightGridBounds))
		ri.Error(ERR_DROP, "%s: invalid BSP light grid dimensions", {world}->name);""")
    if vanilla:
        edit(local, "typedef struct world_s {", "typedef struct world_s {\n\tbool enhancedMap;")
        edit(local, "typedef struct srfSurfaceFace_s {\n\tsurfaceType_t\tsurfaceType;",
             "typedef struct srfSurfaceFace_s {\n\tsurfaceType_t\tsurfaceType;\n\tvec3_t bounds[2];")
        edit(bsp, "\tc_gridVerts = 0;", "\tc_gridVerts = 0;\n\tworldData.enhancedMap = version == ST_BSP_VERSION;")
        edit(bsp, "\t// take the plane information from the lightmap vector",
             """	if (worldData.enhancedMap) {
		ClearBounds(cv->bounds[0], cv->bounds[1]);
		for (int point = 0; point < numPoints; ++point)
			AddPointToBounds(cv->points[point], cv->bounds[0], cv->bounds[1]);
	}

	// take the plane information from the lightmap vector""")
        edit(renderer + "/tr_world.cpp", "\tif ( shader->cullType == CT_TWO_SIDED ) {",
             """	if (tr.currentEntityNum == REFENTITYNUM_WORLD && tr.world && tr.world->enhancedMap) {
		auto *face = reinterpret_cast<srfSurfaceFace_t *>(surface);
		for (int i = 0; i < 4; ++i) {
			if (BoxOnPlaneSide(face->bounds[0], face->bounds[1], &tr.viewParms.frustum[i]) == 2)
				return qtrue;
		}
	}

	if ( shader->cullType == CT_TWO_SIDED ) {""")
        edit(bsp, """	if (ri.CM_GetCachedMapDiskImage())
	{
		buffer = (byte *)ri.CM_GetCachedMapDiskImage();
	}
	else
	{
		// still needs loading...
		//
		ri.FS_ReadFile( name, (void **)&buffer );
		if ( !buffer ) {
			Com_Error (ERR_DROP, "RE_LoadWorldMap: %s not found", name);
		}
	}""", """	// The engine publishes its main-world cache only after validation.
	const bool cached = !index && ri.CM_GetCachedMapDiskImage();
	int version = 0;
	if (cached) {
		buffer = static_cast<byte *>(ri.CM_GetCachedMapDiskImage());
		version = LittleLong(st_bsp::Record<dheader_t>(buffer, 0).version);
	} else {
		buffer = ST_ReadBSP(name, version);
		if (!buffer)
			ri.Error(ERR_DROP, "RE_LoadWorldMap: %s not found", name);
	}""")
        edit(bsp, """	int i = LittleLong (header->version);
	if ( i != BSP_VERSION ) {
		Com_Error (ERR_DROP, "RE_LoadWorldMap: %s has wrong version number (%i should be %i)",
			name, i, BSP_VERSION);
	}

""", "")
        edit(bsp, "\tif (ri.CM_GetCachedMapDiskImage())", "\tif (cached)")
        edit(bsp, "\t\tri.FS_FreeFile( buffer );", "\t\tri.Hunk_FreeTempMemory(buffer);")
        edit(bsp, "\t\ttr.world = &worldData;", """		R_ReserveMapDrawSurfaces(version == ST_BSP_VERSION ? worldData.numsurfaces : 0);
		tr.world = &worldData;""")
        edit(bsp, """	if (numPoints > MAX_FACE_POINTS) {
		ri.Printf( PRINT_ALL, S_COLOR_YELLOW  "WARNING: MAX_FACE_POINTS exceeded: %i\\n", numPoints);
		numPoints = MAX_FACE_POINTS;
		surf->shader = tr.defaultShader;
	}
""", "")
        edit(bsp, "buf_p = buf + i * LIGHTMAP_SIZE*LIGHTMAP_SIZE * 3;",
             "buf_p = buf + (len == st_bsp::lightmapBytes ? 0 : i) * st_bsp::lightmapBytes;")
    else:
        apply_rend2_pass(edit)
        edit(bsp, "\tif (r_mergeLeafSurfaces->integer)\n\t{\n\t\tR_MergeLeafSurfaces(worldData);",
             """	// Large worlds use the shader-sorted VBOs and backend multidraw.
	// The legacy leaf merge scans surface lists quadratically and assumes
	// all members of a merge group fit in one source VBO.
	if (version == BSP_VERSION && r_mergeLeafSurfaces->integer)
	{
		R_MergeLeafSurfaces(worldData);""")
        edit(bsp, "    ri.FS_ReadFile(name, &buffer.v);",
             "\tint version = 0;\n\tbuffer.b = ST_ReadBSP(name, version);")
        edit(bsp, """	int bspVersion = LittleLong(header->version);
	if (bspVersion != BSP_VERSION)
	{
		ri.Error(
			ERR_DROP,
			"R_LoadBSP: %s has wrong version number (%i should be %i)",
			name,
			bspVersion,
			BSP_VERSION);
	}

""", "")
        edit(bsp, """	ri.FS_FreeFile(buffer.v);

	return worldData;""",
             """	if (bspIndex == nullptr)
		R_ReserveMapDrawSurfaces(version == ST_BSP_VERSION ? worldData->numsurfaces : 0);
	ri.Hunk_FreeTempMemory(buffer.b);

	return worldData;""")
    edit(bsp, '#include "../qcommon/st_bsp_validate.h"',
         '#include "../qcommon/st_bsp_validate.h"\n#include "../rd-common/st_bsp_read.h"')

    # Reserve extra storage per enhanced world. Keep classic capacity and memory.
    edit(local, "#define\tDRAWSURF_MASK\t\t\t(MAX_DRAWSURFS-1)",
         "#define\tST_MAX_DRAWSURFS\t(8 * MAX_DRAWSURFS)")
    edit(local, "drawSurf_t\tdrawSurfs[MAX_DRAWSURFS];",
         """	drawSurf_t	drawSurfs[MAX_DRAWSURFS];
	drawSurf_t *mapDrawSurfs;
	drawSurf_t *mapSortScratch;
	int mapDrawCapacity;
	bool mapDrawOverflow;""")
    edit(local, "} backEndData_t;", """} backEndData_t;

void R_ReserveMapDrawSurfaces(int surfaces);
drawSurf_t *R_MapDrawSurfaces();""")
    edit(main, "static void R_RadixSort( drawSurf_t *source, int size )",
         """void R_ReserveMapDrawSurfaces(int surfaces) {
	backEndData->mapDrawSurfs = nullptr;
	backEndData->mapSortScratch = nullptr;
	backEndData->mapDrawCapacity = MAX_DRAWSURFS;
	backEndData->mapDrawOverflow = false;
	if (surfaces > MAX_DRAWSURFS / 2) {
		const int capacity = Q_min(ST_MAX_DRAWSURFS, MAX_DRAWSURFS + 2 * surfaces);
		backEndData->mapDrawSurfs = static_cast<drawSurf_t *>(ri.Hunk_Alloc(capacity * sizeof(drawSurf_t), h_low));
		backEndData->mapSortScratch = static_cast<drawSurf_t *>(ri.Hunk_Alloc(capacity * sizeof(drawSurf_t), h_low));
		backEndData->mapDrawCapacity = capacity;
	}
}

drawSurf_t *R_MapDrawSurfaces() {
	return backEndData->mapDrawSurfs ? backEndData->mapDrawSurfs : backEndData->drawSurfs;
}

static void R_RadixSort( drawSurf_t *source, int size )""")
    edit(main, "  static drawSurf_t scratch[ MAX_DRAWSURFS ];",
         "  static drawSurf_t classicScratch[MAX_DRAWSURFS];\n"
         "  drawSurf_t *scratch = backEndData->mapSortScratch ? backEndData->mapSortScratch : classicScratch;")
    edit(main, """	// instead of checking for overflow, we just mask the index
	// so it wraps around
	index = tr.refdef.numDrawSurfs & DRAWSURF_MASK;""",
         """	const int capacity = backEndData->mapDrawCapacity ? backEndData->mapDrawCapacity : MAX_DRAWSURFS;
	if (tr.refdef.numDrawSurfs >= capacity) {
		if (!backEndData->mapDrawOverflow) {
			backEndData->mapDrawOverflow = true;
			ri.Printf(PRINT_WARNING, "Draw surface capacity exceeded (%i)\\n", capacity);
		}
		return;
	}
	index = tr.refdef.numDrawSurfs;""")
    edit(main, """	// if we overflowed MAX_DRAWSURFS, the drawsurfs
	// wrapped around in the buffer and we will be missing
	// the first surfaces, not the last ones
""" + ("""	if ( numDrawSurfs > MAX_DRAWSURFS ) {
		numDrawSurfs = MAX_DRAWSURFS;
	}
""" if vanilla else """	if ( numDrawSurfs > MAX_DRAWSURFS )
			numDrawSurfs = MAX_DRAWSURFS;
"""), "")
    for filename in ("tr_scene.cpp",) if vanilla else ("tr_scene.cpp", "tr_weather.cpp"):
        edit(renderer + "/" + filename, "tr.refdef.drawSurfs = backEndData->drawSurfs;",
             "tr.refdef.drawSurfs = R_MapDrawSurfaces();")


def apply_rend2_pass(edit):
    backend = "rd-rend2/tr_backend.cpp"
    edit(backend, "#include <algorithm>", "#include <algorithm>\n#include <vector>")
    edit(backend, """struct Pass
{
	int maxDrawItems;
	int numDrawItems;
	DrawItem *drawItems;
	uint32_t *sortKeys;
};""", """struct Pass
{
	size_t maxDrawItems;
	std::vector<DrawItem> drawItems;
	std::vector<uint32_t> sortKeys;
	std::vector<uint32_t> drawOrder;
};

// One backend pass is active at a time. Reuse the storage across views but
// grow it only for draw items that survive culling and batching.
static Pass renderPass;

void RB_ClearDrawPass()
{
	renderPass = {};
}""")
    edit(backend, """		if ( pass->numDrawItems >= pass->maxDrawItems )
		{
			assert(!"Ran out of space for pass");
			return;
		}

		pass->sortKeys[pass->numDrawItems] = sortKey;
		pass->drawItems[pass->numDrawItems++] = drawItem;""",
         """		if (pass->drawItems.size() >= pass->maxDrawItems)
			return;

		pass->sortKeys.push_back(sortKey);
		pass->drawItems.push_back(drawItem);""")
    edit(backend, """static Pass *RB_CreatePass( Allocator& allocator, int capacity )
{
	Pass *pass = ojkAlloc<Pass>(*backEndData->perFrameMemory);
	*pass = {};
	pass->maxDrawItems = capacity;
	pass->drawItems = ojkAllocArray<DrawItem>(allocator, pass->maxDrawItems);
	pass->sortKeys = ojkAllocArray<uint32_t>(allocator, pass->maxDrawItems);
	return pass;
}""", """static Pass *RB_CreatePass(int capacity)
{
	renderPass.maxDrawItems = capacity;
	renderPass.drawItems.clear();
	renderPass.sortKeys.clear();
	return &renderPass;
}""")
    edit(backend, """static void RB_SubmitRenderPass(
	Pass& renderPass,
	Allocator& allocator )
{
	uint32_t *drawOrder = ojkAllocArray<uint32_t>(
		allocator, renderPass.numDrawItems);

	uint32_t numDrawItems = renderPass.numDrawItems;
	for ( uint32_t i = 0; i < numDrawItems; ++i )
		drawOrder[i] = i;

	uint32_t *sortKeys = renderPass.sortKeys;
	std::sort(drawOrder, drawOrder + numDrawItems, [sortKeys]( uint32_t a, uint32_t b )
	{
		return sortKeys[a] < sortKeys[b];
	});

	RB_DrawItems(renderPass.numDrawItems, renderPass.drawItems, drawOrder);
}""", """static void RB_SubmitRenderPass(Pass& pass)
{
	const auto count = static_cast<uint32_t>(pass.drawItems.size());
	pass.drawOrder.resize(count);
	for (uint32_t i = 0; i < count; ++i)
		pass.drawOrder[i] = i;

	std::sort(pass.drawOrder.begin(), pass.drawOrder.end(), [&pass](uint32_t a, uint32_t b) {
		return pass.sortKeys[a] < pass.sortKeys[b];
	});
	RB_DrawItems(count, pass.drawItems.data(), pass.drawOrder.data());
}""")
    edit(backend, """	backEndData->currentPass = RB_CreatePass(
		*backEndData->perFrameMemory, numDrawSurfs * estimatedNumShaderStages);""",
         """	backEndData->currentPass = RB_CreatePass(numDrawSurfs * estimatedNumShaderStages);""")
    edit(backend, """	RB_SubmitRenderPass(
		*backEndData->currentPass,
		*backEndData->perFrameMemory);""",
         """	RB_SubmitRenderPass(*backEndData->currentPass);""")
    edit("rd-rend2/tr_local.h", "struct Pass;", "struct Pass;\nvoid RB_ClearDrawPass();")
    edit("rd-rend2/tr_init.cpp", "\tbackEndData = NULL;", "\tRB_ClearDrawPass();\n\tbackEndData = NULL;")
    edit("rd-rend2/tr_allocator.cpp",
         """	if ( (size_t)((char *)end - (char *)mark) < allocSize )
	{
		assert(!"Allocator is out of memory");
		return nullptr;
	}

	void *result = mark;
	size_t alignedSize = PAD(allocSize, alignment);""",
         """	const size_t available = (char *)end - (char *)mark;
	const size_t alignedSize = PAD(allocSize, alignment);
	if (alignedSize < allocSize || alignedSize > available)
	{
#if !defined(GLSL_BUILDTOOL)
		ri.Error(ERR_DROP, "Rend2 render scratch capacity exceeded");
#endif
		assert(!"Allocator is out of memory");
		return nullptr;
	}

	void *result = mark;""")
