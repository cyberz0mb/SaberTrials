// Standalone base retextures can share image paths with retail and map PK3s.
// Keep filename precedence among retextures and leave each mod/root independent.
static bool FS_IsWorldTexturePack(const pack_t *pack) {
    bool hasWorldImage = false;
    for (int i = 0; i < pack->numfiles; ++i) {
        const char *name = pack->buildBuffer[i].name;
        if (!name) return false;
        const size_t length = strlen(name);
        if (!length || name[length - 1] == '/') continue;
        const char *ext = COM_GetExtension(name);
        if (!Q_stricmp(ext, "txt") || !Q_stricmp(ext, "md") || !Q_stricmp(ext, "psd")) continue;
        const bool world = !Q_stricmpn(name, "textures/", 9);
        if (!world && Q_stricmpn(name, "models/", 7)) return false;
        if (Q_stricmp(ext, "jpg") && Q_stricmp(ext, "png") &&
            Q_stricmp(ext, "tga") && Q_stricmp(ext, "dds")) return false;
        hasWorldImage |= world;
    }
    return hasWorldImage;
}

static void FS_PrioritizeBaseTextures(searchpath_t **first, const searchpath_t *end) {
    // Downloads referenced by the server already have first place.
    while (*first != end && (*first)->pack && !Q_stricmpn((*first)->pack->pakBasename, "dl_", 3))
        first = &(*first)->next;
    searchpath_t *textures = nullptr;
    searchpath_t **tail = &textures;
    searchpath_t **link = first;
    while (*link != end && (*link)->pack) {
        searchpath_t *node = *link;
        if (!FS_IsWorldTexturePack(node->pack)) {
            link = &node->next;
            continue;
        }
        *link = node->next;
        *tail = node;
        tail = &node->next;
    }
    *tail = *first;
    *first = textures;
}
