#include "st_chat_raster.h"
#ifdef _WIN32
static stchat::Rasterizer stChatRaster;
struct stChatCache_t {std::string text;float width=0,font=0,row=0,scale=0,widthScale=0;int language=0,lines=0,pixelWidth=0,pixelHeight=0; qhandle_t shader=0;};
static stChatCache_t stChatCache[32];
#endif
void STCT_Reset() {
#ifdef _WIN32
    for(auto& cache:stChatCache)cache=stChatCache_t();
#endif
}
static qboolean STCT_Layout(const stChatLayoutRequest_t *request,stChatLayoutResult_t *result) {
    if(!request || !result || !request->text || request->slot<0 || request->slot>=32 ||
        request->width<8 || request->width>640 || request->fontSize<4 || request->fontSize>32 ||
        request->lineHeight<request->fontSize || request->lineHeight>40 || strlen(request->text)>4095)return qfalse;
#ifdef _WIN32
    auto& cache=stChatCache[request->slot];
    float scale=std::max(1.0f,std::min(2.0f,cls.glconfig.vidHeight/480.0f));
    float widthScale=scale*(cls.glconfig.vidWidth/640.0f)/(cls.glconfig.vidHeight/480.0f);
    float fit=std::min(1.0f,1024.0f/(request->width*widthScale));scale*=fit;widthScale*=fit;
    if(cache.text!=request->text || cache.width!=request->width || cache.font!=request->fontSize ||
        cache.row!=request->lineHeight || cache.language!=request->language || cache.scale!=scale || cache.widthScale!=widthScale || !cache.shader) {
        wchar_t path[32768];DWORD length=GetModuleFileNameW(nullptr,path,32768);
        if(!length || length==32768)return qfalse;
        std::wstring folder(path,length);auto slash=folder.find_last_of(L"\\/");
        if(slash==std::wstring::npos || !stChatRaster.init(folder.substr(0,slash)+L"\\translator\\fonts"))return qfalse;
        stchat::Bitmap bitmap;
        if(!stChatRaster.render(request->text,std::min(1024,(int)std::ceil(request->width*widthScale)),
            request->fontSize*scale,request->lineHeight*scale,request->language,bitmap))return qfalse;
        qhandle_t shader=re->ST_ChatUpload(request->slot,bitmap.width,bitmap.height,bitmap.rgba.data());
        if(!shader)return qfalse;
        cache.text=request->text;cache.width=request->width;cache.font=request->fontSize;cache.row=request->lineHeight;
        cache.language=request->language;cache.scale=scale;cache.widthScale=widthScale;cache.lines=bitmap.lines;cache.shader=shader;
        cache.pixelWidth=bitmap.width;cache.pixelHeight=bitmap.height;
    }
    result->lines=cache.lines;result->height=cache.lines*cache.row;return qtrue;
#else
    return qfalse;
#endif
}
static void STCT_Draw(int slot,float x,float y,int firstLine,int lineCount) {
#ifdef _WIN32
    if(slot<0 || slot>=32 || firstLine<0 || lineCount<1)return;
    const auto& cache=stChatCache[slot];
    if(!cache.shader || firstLine>=cache.lines)return;
    int count=std::min(lineCount,cache.lines-firstLine);
    float top=firstLine*cache.row*cache.scale,span=count*cache.row*cache.scale;
    re->SetColor(nullptr);
    re->DrawStretchPic(x,y,cache.width,count*cache.row,0,top/cache.pixelHeight,
        cache.width*cache.widthScale/cache.pixelWidth,(top+span)/cache.pixelHeight,cache.shader);
#endif
}
qboolean STCT_DrawInput(const char *text,int cursor,float x,float y) {
#ifdef _WIN32
    char shown[1024];size_t length=strlen(text);cursor=std::max(0,std::min((int)length,cursor));
    // Keep the editing position visible without slicing a UTF-8 character.
    int start=cursor;
    int visible=std::max(1,(int)((620-x)/15)-2);
    for(int i=0;i<visible&&start>0;++i)start=ST_UTF8Previous(text,start);
    int used=0;
    for(int p=start;p<=(int)length && used<(int)sizeof(shown)-8;) {
        if(p==cursor && !((cls.realtime>>8)&1)){shown[used++]='|';}
        if(p==(int)length)break;
        int n;ST_UTF8Read(text+p,&n);memcpy(shown+used,text+p,n);used+=n;p+=n;
    }
    shown[used]=0;
    stChatLayoutRequest_t request={31,shown,std::max(50.0f,620-x),14,24,0};stChatLayoutResult_t result;
    if(STCT_Layout(&request,&result)){STCT_Draw(31,x,y,0,1);return qtrue;}
#endif
    return qfalse;
}
