#include "../ui/st_chat_layout.h"
#include "qcommon/st_translation_languages.h"

namespace foreignChat {
struct Line {
    std::string original,prefix,translated;
    unsigned ticket=0;
    int time=0,source=0,target=0;
    char stamp[8]={};
};
static Line history[16];
static int next,chatHandle=-1;
static bool painting,expanded,hidden;

static bool enabled() {
    return Cvar_Get("st_personalChat","1",CVAR_ARCHIVE)->integer!=0;
}

static void reset() {
    for (auto &line:history) line=Line();
    next=0; chatHandle=-1; painting=expanded=hidden=false;
}

static void mask(vmCvar_t *v) {
    if (v && v->handle==chatHandle && painting && enabled()) {
        // Hide the stock duplicate locally. Keep its real duration and archive intact.
        v->integer=0; v->value=0; v->string[0]='0'; v->string[1]=0; v->modificationCount=-1;
    }
}
static void reg(vmCvar_t *v,const char *name,const char *value,uint32_t flags) {
    Cvar_Register(v,name,value,flags);
    personalCamera::remember(v,name);
    personalHud::remember(v,name);
    if (v && !Q_stricmp(name,"cg_chatBox")) {chatHandle=v->handle; mask(v);}
}
static void update(vmCvar_t *v) { Cvar_Update(v); mask(v); personalCamera::apply(v); personalHud::mask(v); }

// Stock OpenJK marks accepted chat prints with '*', after team/ignore and mod filters.
// Leave unfamiliar formats and ordinary console/server prints with the owning module.
static void accept(const char *printed) {
    if (*printed!='*' || cls.state!=CA_ACTIVE || !enabled() || Cvar_VariableIntegerValue("cg_chatBox")<=0) return;
    const char *cmd=Cmd_Argv(0);
    const bool location=!strcmp(cmd,"lchat") || !strcmp(cmd,"ltchat");
    if (!location && strcmp(cmd,"chat") && strcmp(cmd,"tchat")) return;
    char utf8[MAX_STRING_CHARS*3];
    ST_UTF8Sanitize(printed+1,utf8,sizeof(utf8));
    std::string message=utf8;
    auto last=message.find_last_not_of("\r\n");
    if (last==std::string::npos) return;
    message.resize(last+1);
    Line &line=history[next]; next=(next+1)%ARRAY_LEN(history);
    line=Line(); line.original=message; line.time=cls.realtime;
    qtime_t now; Com_RealTime(&now); Com_sprintf(line.stamp,sizeof(line.stamp),"%02d:%02d",now.tm_hour,now.tm_min);
    if (!stTranslate->integer) return;
    size_t body=std::string::npos;
    if (location) {
        char clean[MAX_STRING_CHARS*3];
        ST_UTF8Sanitize(Cmd_Argv(4),clean,sizeof(clean));
        const auto length=strlen(clean);
        if (length && length<=message.size() && message.compare(message.size()-length,length,clean)==0)
            body=message.size()-length;
    } else {
        // Bound the name separately. Keep display names, channel marks and location in the original.
        for (const char *sep : { "^7: ", "^7): ", "^7]: ", ": " }) {
            auto pos=message.find(sep);
            if (pos!=std::string::npos && pos<2*MAX_NETNAME) {body=pos+strlen(sep); break;}
        }
    }
    if (body==std::string::npos || body>=message.size()) return;
    while (body+1<message.size() && Q_IsColorString(message.c_str()+body)) body+=2;
    if (body==message.size()) return;
    line.prefix=message.substr(0,body);
    stTranslationRequest_t req={};
    req.target=line.target=stTranslateTarget->integer;
    req.source=line.source=stTranslateSource->integer;
    Q_strncpyz(req.text,message.c_str()+body,sizeof(req.text));
    for (int i=0;i<MAX_CLIENTS;i++) {
        const char *info=cl.gameState.stringData+cl.gameState.stringOffsets[CS_PLAYERS+i];
        char clean[MAX_NETNAME],name[MAX_NETNAME*3];
        Q_strncpyz(clean,Info_ValueForKey(info,"n"),sizeof(clean)); Q_CleanStr(clean);
        ST_UTF8Sanitize(clean,name,sizeof(name));
        if (*name && strlen(req.names)+strlen(name)+2<sizeof(req.names)) {
            Q_strcat(req.names,sizeof(req.names),name); Q_strcat(req.names,sizeof(req.names),"\n");
        }
    }
    line.ticket=STTR_Submit(&req);
}
static void print(const char *fmt,...) {
    va_list args; va_start(args,fmt);
    char text[MAXPRINTMSG]; Q_vsnprintf(text,sizeof(text),fmt,args); va_end(args);
    Com_Printf("%s",text);
    accept(text);
}
static void picture(float x,float y,float w,float h,float u,float v,float s,float t,qhandle_t shader,const float *tint) {
    if (shader) { re->SetColor(tint); re->DrawStretchPic(x,y,w,h,u,v,s,t,shader); re->SetColor(nullptr); }
}
}

void CL_ForeignChatStatus() {
    int count=0,translated=0;
    for(const auto &line:foreignChat::history) {
        count+=!line.original.empty(); translated+=!line.translated.empty();
    }
    Com_Printf("PERSONAL_UI chat=%d translated=%d drawing=%d\n",count,translated,foreignChat::painting);
}

void CL_DrawForeignChat() {
    using namespace foreignChat;
    if (!enabled()) {painting=false;return;}
    const int duration=Cvar_VariableIntegerValue("cg_chatBox");
    if (duration<=0 || !Cvar_VariableIntegerValue("cg_draw2D")) return;
    stTranslationResult_t result;
    while (STTR_Poll(&result)) for (auto &line:history) {
        if (!line.ticket || result.ticket!=line.ticket) continue;
        line.ticket=0;
        if (result.target==line.target && cls.realtime-line.time<9000)
            line.translated=std::string("^5[")+ST_LanguageTag(line.target)+"] ^7"+line.prefix+result.text;
    }
    if (hidden) return;
    auto layout=ST_ChatLayout(Cvar_Get("st_chatSize","100",CVAR_ARCHIVE)->value,Cvar_Get("st_chatWidth","42",CVAR_ARCHIVE)->value,
        Cvar_Get("st_chatHeight","20",CVAR_ARCHIVE)->value,Cvar_Get("st_chatOpacity","65",CVAR_ARCHIVE)->value);
    struct Visible {int slot,first,count;};
    Visible visible[ARRAY_LEN(history)];
    int n=0;
    const float s=layout.size,row=16*s;
    const float bottom=Com_Clampi(190,400,Cvar_VariableIntegerValue("cg_chatBoxHeight")+33);
    const float height=std::min(layout.height,bottom-25*s),top=bottom-height;
    int room=int((height-16*s)/row);
    for (int i=1; i<=(int)ARRAY_LEN(history) && room>0; ++i) {
        int slot=(next+ARRAY_LEN(history)-i)%ARRAY_LEN(history);
        const auto &line=history[slot];
        if (line.original.empty() || (!expanded && cls.realtime-line.time>=duration)) continue;
        bool translated=stTranslate->integer && line.source==stTranslateSource->integer && line.target==stTranslateTarget->integer && !line.translated.empty();
        std::string shown=!translated ? line.original : Cvar_VariableIntegerValue("st_translateOriginal") ?
            line.original+"\n"+line.translated : line.translated;
        stChatLayoutRequest_t request={slot,shown.c_str(),layout.width-45*s,11*s,row,translated?line.target:0};
        stChatLayoutResult_t lines;
        if (!STCT_Layout(&request,&lines)) {painting=false;return;}
        painting=true;
        int count=std::min(lines.lines,room);
        visible[n++]={slot,lines.lines-count,count}; room-=count;
    }
    if (!n && !expanded) return;
    ST_ChatDrawFrame(picture,CL_PersonalArt("chat_frame_fill"),CL_PersonalArt("chat_frame"),10,top,layout.width,height,s,s,layout.opacity);
    const float aspect=(cls.glconfig.vidHeight/480.f)/(cls.glconfig.vidWidth/640.f);
    CL_PersonalPic("chat_header",10,top-11*s,102*s*aspect,26*s);
    const float white[]={.86f,.95f,1,1},blue[]={.51f,.77f,.89f,1};
    CL_PersonalText("CHAT",.48f*s,10+32*s*aspect,top-5*s,white,false);
    float y=top+10*s;
    for (int i=n-1;i>=0;--i) {
        const auto &v=visible[i];
        if (!v.first) CL_PersonalText(history[v.slot].stamp,.46f*s,16,y+2*s,blue,false);
        STCT_Draw(v.slot,10+36*s,y,v.first,v.count); y+=v.count*row;
    }
}
