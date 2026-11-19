#include "st_translation_core.h"
static sttr::Worker stTranslator;
static cvar_t *stTranslate,*stTranslateSource,*stTranslateTarget;

void STTR_Init() {
    stTranslate=Cvar_Get("st_translate","0",CVAR_ARCHIVE);
    stTranslateSource=Cvar_Get("st_translateSource","0",CVAR_ARCHIVE);
    stTranslateTarget=Cvar_Get("st_translateTarget","1",CVAR_ARCHIVE);
    Cvar_Get("st_translateOriginal","1",CVAR_ARCHIVE);
    Cvar_Get("st_translationStatus","Off",CVAR_ROM|CVAR_TEMP|CVAR_INTERNAL);
}
void STTR_Reset() {stTranslator.reset();}
void STTR_Shutdown() {stTranslator.shutdown();}
void STTR_Frame() {
    static int lastEnabled=-1,lastSource=-1,lastTarget=-1,lastStatus=-1;
    if(!stTranslate)return;
    if(lastEnabled!=stTranslate->integer || lastSource!=stTranslateSource->integer || lastTarget!=stTranslateTarget->integer) {
        STTR_Reset();lastEnabled=stTranslate->integer;lastSource=stTranslateSource->integer;lastTarget=stTranslateTarget->integer;
        lastStatus=-1;
    }
    int status=stTranslator.status.load();
    if(lastStatus!=status) {
        const char *message=!lastEnabled?"Off":status==2?"Translator unavailable; showing original chat":
            status==3?"Language pack unavailable; showing original chat":status==4?"Translating - offline":
            status==1?"Ready - offline":"Ready for chat - offline";
        Cvar_Set("st_translationStatus",message);lastStatus=status;
    }
}
static unsigned STTR_Submit(const stTranslationRequest_t *request) {
    if(!request || !stTranslate || !stTranslate->integer || cls.state!=CA_ACTIVE)return 0;
    if(request->source!=stTranslateSource->integer || request->target!=stTranslateTarget->integer)return 0;
#ifdef _WIN32
    wchar_t executable[32768];DWORD count=GetModuleFileNameW(nullptr,executable,32768);
    if(!count || count==32768)return 0;
    std::wstring path(executable,count);size_t slash=path.find_last_of(L"\\/");
    if(slash==std::wstring::npos)return 0;
    return stTranslator.submit(*request,path.substr(0,slash)+L"\\translator");
#else
    return 0;
#endif
}
static qboolean STTR_Poll(stTranslationResult_t *result) {
    return result && stTranslate && stTranslate->integer && stTranslator.poll(*result)?qtrue:qfalse;
}
