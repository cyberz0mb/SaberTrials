"""Use the map's baked entity lighting on the installed optional renderers."""
from pathlib import Path
import runpy
import shutil

from full_client_ui import change


def stage_texture_decoding(tree):
    png = tree / "codemp/rd-common/tr_image_png.cpp"
    anchor = "\tPNGFileReader reader (buf);"
    if "LoadJPG(filename, data, width, height);" in png.read_text():
        return
    change(png, anchor, '''    // Some retexture PK3s store JPEG data under the original .png name.
    // Both decoders read the same virtual path selected by the engine.
    if (len >= 3 && !memcmp(buf, "\\xff\\xd8\\xff", 3)) {
        ri.FS_FreeFile(buf);
        LoadJPG(filename, data, width, height);
        return;
    }
    if (len < 8) {
        ri.FS_FreeFile(buf);
        return;
    }
''' + anchor)


def stage_material_overrides(tree):
    client=tree/"codemp/client"
    shutil.copyfile(Path(__file__).resolve().parents[1]/"development-source/compatibility/material_overrides.inc",
                    client/"st_material_overrides.inc")
    main=client/"cl_main.cpp"
    if '#include "st_material_overrides.inc"' not in main.read_text():
        anchor='void CL_InitRef( void ) {'
        change(main,anchor,'#include "st_material_overrides.inc"\n'+anchor)
        change(main,'ri.FS_ListFiles = FS_ListFiles;', 'ri.FS_ListFiles = ST_RendererListFiles;')
    shader=tree/"codemp/rd-rend2/tr_shader.cpp"
    # A sibling Rend2 .mtr may substitute for an ordinary .shader. An
    # explicitly selected .oshader must keep its own filename.
    condition="if ( (ext = strrchr(filename, '.')) )"
    if 'Q_stricmp(ext,".oshader")' not in shader.read_text():
        change(shader,condition,'if ( (ext = strrchr(filename, \'.\')) && Q_stricmp(ext,".oshader") )')


def patch(tree):
    stage_texture_decoding(tree)
    overlays=Path(__file__).resolve().parents[1]/"development-source"
    runpy.run_path(str(overlays / "vulkan/enhanced_content.py"))["apply"](tree)
    source=overlays/"compatibility/st_grid_ambient.h"
    shutil.copyfile(overlays/"vulkan/tr_st_chat.inc",tree/"codemp/rd-vulkan/tr_st_chat.inc")
    for backend in ("rd-rend2","rd-vulkan"):
        root=tree/"codemp"/backend
        shutil.copyfile(source,root/source.name)
        header=root/"tr_local.h"
        mark="vec3_t\t\tlightGridSize;"
        change(header,mark,mark+"\n\tvec3_t gridMinimum;")
        bsp=root/"tr_bsp.cpp"
        change(bsp,'#include "tr_local.h"','#include "tr_local.h"\n#include "st_grid_ambient.h"')
        mark="w->lightGridSize[0] = 64;"
        change(bsp,mark,"VectorClear(w->gridMinimum);\n\t"+mark)
        mark='if (!Q_stricmp(keyname, "gridsize"))'
        change(bsp,mark,'''if (!Q_stricmp(keyname, "_mingridlight")) {
            ST_ParseGridMinimum(value,w->gridMinimum);
            continue;
        }
        '''+mark)
        mark="i < numGridDataElements ; i++ )\n\t{"
        world="w" if backend=="rd-vulkan" else "worldData"
        change(bsp,mark,mark+f"\n        ST_ApplyGridMinimum({world}->lightGridData[i],{world}->gridMinimum);")
        if backend=="rd-vulkan":
            # vs is the second member of "source;target". s names the key.
            data=bsp.read_text()
            mark='R_RemapShader(value, s, "0");'
            if data.count(mark)!=2: raise ValueError("Vulkan worldspawn remap changed")
            bsp.write_text(data.replace(mark,'R_RemapShader(value, vs, "0");'))
        lighting=root/"tr_light.cpp"
        old=f"""pos[i] = floor( v );
		frac[i] = v - pos[i];
		if ( pos[i] < 0 ) {{
			pos[i] = 0;
		}} else if ( pos[i] >= {('tr.world' if backend=='rd-vulkan' else 'world')}->lightGridBounds[i] - 1 ) {{
			pos[i] = {('tr.world' if backend=='rd-vulkan' else 'world')}->lightGridBounds[i] - 1;
		}}"""
        bounds=("tr.world" if backend=="rd-vulkan" else "world")+"->lightGridBounds[i]"
        change(lighting,old,f"""v = Com_Clamp(0.f, (float)({bounds}-1), v);
        pos[i] = (int)floor(v);
        frac[i] = v-pos[i];""")
        mark="gridPos += gridStep[j];"
        change(lighting,mark,"if (frac[j] > 0.f) "+mark)
