// All three Windows renderers concatenate their shader files in reverse list
// order, then use the first definition. Keep ordinary materials in their
// original order and pass both extensions through the normal pure-aware VFS.
static char **ST_RendererListFiles(const char *path, const char *extension, int *count) {
    char **regular = FS_ListFiles(path, extension, count);
    if (!regular || *count >= 4096 || Q_stricmp(path, "shaders") || !extension || Q_stricmp(extension, ".shader")) return regular;

    int extraCount = 0;
    char **extra = FS_ListFiles(path, ".oshader", &extraCount);
    const char builtin[] = "st_community_huds.shader";
    bool addBuiltin = true;
    for (int i=0; i<*count; ++i)
        if (!Q_stricmp(regular[i], builtin)) { addBuiltin = false; break; }
    // The renderer can read 4096 files. Preserve all ordinary entries that
    // fit, even when a pack supplies more overrides than the spare capacity.
    const int used = Q_min(extraCount, 4096 - *count - (int)addBuiltin);
    char **merged = (char **)Z_Malloc((*count + used + (int)addBuiltin + 1) * sizeof(char *), TAG_FILESYS);
    // Built-in HUD materials only address st_huds/jk2. Put them last in the
    // parser's priority order so any installed material can customize them.
    if (addBuiltin) {
        merged[0]=(char *)Z_Malloc(sizeof(builtin), TAG_FILESYS);
        memcpy(merged[0], builtin, sizeof(builtin));
    }
    memcpy(merged + (int)addBuiltin, regular, *count * sizeof(char *));
    *count += (int)addBuiltin;
    if (used) memcpy(merged + *count, extra, used * sizeof(char *));
    *count += used;
    merged[*count] = NULL;
    Z_Free(regular);
    for (int i = used; i < extraCount; ++i) Z_Free(extra[i]);
    if (extra) Z_Free(extra);
    return merged;
}
