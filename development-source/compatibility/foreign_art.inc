// These are built-in client widgets. All mod content still uses the normal filesystem.
#define STB_IMAGE_STATIC
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_ONLY_TGA
#define STBI_NO_STDIO
#include "../rd-rend2/stb_image.h"
#include "foreign_menu_language.inc"

static const struct {const char *name; int resource;} personalArt[] = {
#include "foreign_art_ids.inc"
};
static_assert(ARRAY_LEN(personalArt) <= 64, "reserved personal UI texture slots");
static qhandle_t artHandles[ARRAY_LEN(personalArt)];
void CL_ResetPersonalArt() { memset(artHandles,0,sizeof(artHandles)); }

qhandle_t CL_PersonalArt(const char *name) {
#ifdef _WIN32
    if (!re || !re->ST_ChatUpload) return 0;
    for (int i=0; i<(int)ARRAY_LEN(personalArt); ++i) {
        if (strcmp(name,personalArt[i].name)) continue;
        if (artHandles[i]) return artHandles[i];
        const auto exe=GetModuleHandleW(nullptr);
        const auto resource=FindResourceW(exe,MAKEINTRESOURCEW(personalArt[i].resource),MAKEINTRESOURCEW(10));
        if (!resource) return 0;
        const auto bytes=static_cast<const byte*>(LockResource(LoadResource(exe,resource)));
        int w=0,h=0,channels=0;
        auto rgba=stbi_load_from_memory(bytes,SizeofResource(exe,resource),&w,&h,&channels,4);
        if (rgba) {
            artHandles[i]=re->ST_ChatUpload(160+i,w,h,rgba);
            stbi_image_free(rgba);
        }
        return artHandles[i];
    }
#endif
    return 0;
}

void CL_PersonalPic(const char *name,float x,float y,float w,float h) {
    const auto shader=CL_PersonalArt(name);
    if (shader) { re->SetColor(nullptr); re->DrawStretchPic(x,y,w,h,0,0,1,1,shader); }
}

float CL_PersonalText(const char *text,float size,float x,float y,const float *color,bool centered) {
    text=STML_Translate(text);
    const float width=STML_MenuText(text,size,0,0,nullptr);
    if (width>0) {
        if (color) STML_MenuText(text,size,x-(centered?width/2:0),y,color);
        return width;
    }
    const int font=re->RegisterFont("ocr_a");
    const float scale=size*.55f;
    const float fallback=re->Font_StrLenPixels(text,font,scale);
    if (color) re->Font_DrawString(x-(centered?fallback/2:0),y,text,color,font,-1,scale);
    return fallback;
}
