/* The menu cache uses slots separate from the translated chat panel. */
const char *STML_MenuCatalog(int language, int *size) {
    *size = 0;
#ifdef _WIN32
    if (language < 2 || language > 17)
        return nullptr;
    const HMODULE module = GetModuleHandleW(nullptr);
    const HRSRC resource = FindResourceW(module, MAKEINTRESOURCEW(4100 + language), MAKEINTRESOURCEW(10));
    if (resource) {
        const DWORD length = SizeofResource(module, resource);
        const HGLOBAL loaded = LoadResource(module, resource);
        if (loaded && length > 0 && length <= 1024 * 1024) {
            const char *catalog = static_cast<const char *>(LockResource(loaded));
            if (catalog) {
                *size = static_cast<int>(length);
                return catalog;
            }
        }
    }
#endif
    return nullptr;
}

static constexpr int ST_MenuTextureCount = 192;
static unsigned stMenuFontClock;
#ifdef _WIN32
struct stMenuFontEntry {
    std::string text;
    unsigned used = 0;
    int language = 0;
    int textureWidth = 0;
    int textureHeight = 0;
    float pixels = 0;
    qhandle_t shader = 0;
};
static stMenuFontEntry stMenuFonts[ST_MenuTextureCount];
#endif

void STML_ResetFont() {
#ifdef _WIN32
    for (auto& entry : stMenuFonts)
        entry = stMenuFontEntry();
    stMenuFontClock = 0;
#endif
}

float STML_MenuText(const char *text,float scale,float x,float y,const float *color) {
#ifdef _WIN32
    if (!re || !re->ST_ChatUpload || !text || !*text || scale <= 0 ||
        cls.glconfig.vidWidth <= 0 || cls.glconfig.vidHeight <= 0)
        return 0;
    const int language = Cvar_VariableIntegerValue("st_menuLanguage");
    const float aspect = (cls.glconfig.vidHeight / 480.f) / (cls.glconfig.vidWidth / 640.f);
    constexpr float fontSize = 30, rowHeight = 44, pixelScale = .5f;
    int slot = 0;
    for (int i = 0; i < ST_MenuTextureCount; ++i) {
        if (stMenuFonts[i].language == language && stMenuFonts[i].text == text) {
            slot = i;
            break;
        }
        if (stMenuFonts[i].used < stMenuFonts[slot].used)
            slot = i;
    }
    auto& entry = stMenuFonts[slot];
    const bool miss = entry.text != text || entry.language != language;
    if (miss || (color && !entry.shader)) {
        wchar_t executable[32768];
        const DWORD length = GetModuleFileNameW(nullptr, executable, 32768);
        if (!length || length == 32768)
            return 0;
        std::wstring folder(executable, length);
        const auto slash = folder.find_last_of(L"\\/");
        if (slash == std::wstring::npos || !stChatRaster.init(folder.substr(0,slash)+L"\\translator\\fonts"))
            return 0;
        stchat::Bitmap bitmap;
        if (!stChatRaster.render(text,1024,fontSize,rowHeight,language,bitmap,true,!color))
            return 0;
        entry.text = text;
        entry.language = language;
        entry.pixels = bitmap.inkWidth;
        entry.shader = color ? re->ST_ChatUpload(32+slot,bitmap.width,bitmap.height,bitmap.rgba.data()) : 0;
        if (color && entry.shader) {
            entry.textureWidth = bitmap.width;
            entry.textureHeight = bitmap.height;
        }
    }
    entry.used = ++stMenuFontClock;
    if (color) {
        if (!entry.shader)
            return 0;
        const float span = std::min(1024.f,entry.pixels+4);
        re->SetColor(color);
        re->DrawStretchPic(x-2*scale*aspect*pixelScale,y-3*scale,span*scale*aspect*pixelScale,
            (rowHeight+4)*scale*pixelScale,0,0,span/entry.textureWidth,(rowHeight+4)/entry.textureHeight,entry.shader);
        re->SetColor(nullptr);
    }
    return entry.pixels*scale*aspect*pixelScale;
#else
    return 0;
#endif
}
