"""Apply Windows package discovery and implicit PK3 model directory support."""
from pathlib import Path
from shutil import copyfile
from beta_release import BUILD_LABEL


def stage(tree):
    common = tree / "codemp/qcommon"
    (common / "st_beta_version.h").write_text(f'#define ST_BETA_BUILD_LABEL "{BUILD_LABEL}"\n')
    startup = common / "common.cpp"
    init = startup.read_text()
    marker = 'Com_Printf ("--- Common Initialization Complete ---\\n");'
    if "ST_BETA_BUILD_LABEL" not in init:
        if init.count(marker) != 1:
            raise ValueError("Unexpected engine initialization")
        startup.write_text(init.replace(marker, marker + '''
#if defined(_WIN32) && !defined(DEDICATED)
#include "st_beta_version.h"
        Com_Printf(ST_BETA_BUILD_LABEL "\\n");
#endif'''))
    copyfile(Path(__file__).with_name("package_paths.inc"), common / "st_package_paths.inc")
    target = common / "files.cpp"
    source = target.read_text()
    copyfile(Path(__file__).with_name("base_texture_order.inc"), common / "st_base_texture_order.inc")
    if '#include "st_base_texture_order.inc"' not in source:
        edits = [
            ("static void FS_AddGameDirectory( const char *path, const char *dir ) {",
             '''#if defined(_WIN32) && !defined(DEDICATED)
#include "st_base_texture_order.inc"
#endif
static void FS_AddGameDirectory( const char *path, const char *dir ) {
#if defined(_WIN32) && !defined(DEDICATED)
    const searchpath_t *previousPaths = fs_searchpaths;
#endif'''),
            ("\t// done\n\tSys_FreeFileList( pakfiles );", '''#if defined(_WIN32) && !defined(DEDICATED)
    if (!fs_numServerPaks && !Q_stricmp(dir, BASEGAME)) {
        // Loose directory placement still follows fs_dirbeforepak.
        searchpath_t **first = fs_searchpaths == thedir ? &thedir->next : &fs_searchpaths;
        FS_PrioritizeBaseTextures(first, previousPaths);
    }
#endif
\t// done
\tSys_FreeFileList( pakfiles );'''),
        ]
        for old, new in edits:
            if source.count(old) != 1:
                raise ValueError("Unexpected filesystem package mount sequence")
            source = source.replace(old, new)
        target.write_text(source)
    if '#include "st_package_paths.inc"' in source:
        return
    edits = [
        ("void FS_InitFilesystem( void ) {", '#include "st_package_paths.inc"\n\nvoid FS_InitFilesystem( void ) {'),
        ('Com_StartupVariable( "fs_forcegame" );',
         'Com_StartupVariable( "fs_forcegame" );\n#if defined(_WIN32) && !defined(DEDICATED)\n\tFS_SetPackagedClientDefaults();\n#endif'),
        ("FS_ReturnPath(path, zpath, &pathDepth);", """FS_ReturnPath(path, zpath, &pathDepth);
    const bool listPlayerDirs = !filter && !strcmp(extension, "/") &&
        pathLength == sizeof("models/players") - 1 && !Q_stricmpn(path, "models/players", pathLength);"""),
        ("name = buildBuffer[i].name;\n\t\t\t\t//", """name = buildBuffer[i].name;
                // ZIP directory records are optional. Give the picker the same
                // folder name for a packed model.glm as for an explicit folder.
                if (listPlayerDirs && !Q_stricmpn(name, "models/players/", sizeof("models/players/") - 1)) {
                    const char *folder = name + sizeof("models/players/") - 1;
                    const char *slash = strchr(folder, '/');
                    if (slash && slash > folder && !Q_stricmp(slash + 1, "model.glm")) {
                        char entry[MAX_QPATH];
                        size_t length = slash - folder + 1;
                        if (length < sizeof(entry)) {
                            memcpy(entry, folder, length);
                            entry[length] = 0;
                            nfiles = FS_AddFileToList(entry, list, nfiles);
                        }
                        continue;
                    }
                }
                //"""),
    ]
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f"Unexpected filesystem source around {old}")
        source = source.replace(old, new)
    target.write_text(source)
