// Fixed slot count shared with the Unicode text service. Images remain renderer-owned.
static image_t *stChatImages[224];
static qhandle_t stChatShaders[224];
static void ST_ChatResetImages() {
    memset(stChatImages, 0, sizeof(stChatImages));
    memset(stChatShaders, 0, sizeof(stChatShaders));
}
qhandle_t RE_STChatUpload(int slot, int width, int height, const byte *rgba) {
    if (slot < 0 || slot >= 224 || width < 1 || height < 1 || width > 1024 || height > 1024 || !rgba)
        return 0;
    R_IssueRenderCommands(qfalse);
    image_t *image = stChatImages[slot];
    if (!image) {
        char name[32];
        Com_sprintf(name, sizeof(name), "*stchat%d", slot);
        image = R_CreateImage(name, const_cast<byte *>(rgba), width, height,
            IMGFLAG_CLAMPTOEDGE | IMGFLAG_NOSCALE | IMGFLAG_NOLIGHTSCALE | IMGFLAG_NO_COMPRESSION);
        if (!image) return 0;
        stChatImages[slot] = image;
        InitShader(name, lightmaps2d, stylesDefault);
        stages[0].active = qtrue;
        stages[0].bundle[0].image[0] = image;
        stages[0].bundle[0].rgbGen = CGEN_VERTEX;
        stages[0].bundle[0].alphaGen = AGEN_VERTEX;
        stages[0].stateBits = GLS_DEPTHTEST_DISABLE | GLS_SRCBLEND_SRC_ALPHA | GLS_DSTBLEND_ONE_MINUS_SRC_ALPHA;
        stChatShaders[slot] = FinishShader()->index;
    } else {
        vk_bind(image);
        const bool resize = image->width != width || image->height != height;
        if (resize) {
            image->width = image->uploadWidth = width;
            image->height = image->uploadHeight = height;
            vk_create_image(image, width, height, 1);
        }
        vk_upload_image_data(image, 0, 0, width, height, 1, const_cast<byte *>(rgba), width * height * 4,
            resize ? qfalse : qtrue);
    }
    return stChatShaders[slot];
}
