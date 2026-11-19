#include "st_chat_raster.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdlib>

// Exercise the exact chat-field editing code with a small engine-state fixture.
typedef int qboolean;
#define MAX_SAY_TEXT 150
enum {A_INSERT,A_KP_0,A_SHIFT,A_DELETE,A_CURSOR_LEFT,A_CURSOR_RIGHT,A_HOME,A_END};
struct field_t {char buffer[256];int cursor;} chatField={};
struct {qboolean key_overstrikeMode;struct {bool down;} keys[16];} kg={};
static std::string clipboard;
char *Sys_GetClipboardData(){return _strdup(clipboard.c_str());}
void Z_Free(void *p){free(p);}
void Field_Clear(field_t *p){memset(p,0,sizeof(*p));}
#include "cl_st_chat_input.inc"

int wmain(int argc,wchar_t **argv) {
    assert(argc==2);
    assert(ST_UTF8Valid(u8"日本語 한국어 العربية हिन्दी Україна"));
    for(auto bad:{"\xc0\xaf","\xed\xa0\x80","\xf4\x90\x80\x80","\xef","\xe6\x97"})assert(!ST_UTF8Valid(bad));
    char bounded[5];ST_UTF8Sanitize(u8"日本",bounded,sizeof(bounded));assert(!strcmp(bounded,u8"日"));
    clipboard=u8"日한é";ST_ChatPaste();assert(!strcmp(chatField.buffer,u8"日한é"));
    ST_ChatKey(A_CURSOR_LEFT);ST_ChatChar(8);assert(!strcmp(chatField.buffer,u8"日é"));
    ST_ChatKey(A_DELETE);assert(!strcmp(chatField.buffer,u8"日"));
    ST_ChatKey(A_HOME);kg.key_overstrikeMode=1;ST_ChatInsert(0x1f600);
    assert(!strcmp(chatField.buffer,u8"😀"));kg.key_overstrikeMode=0;
    Field_Clear(&chatField);
    for(int i=0;i<70;++i)ST_ChatInsert(0x65e5);
    assert(strlen(chatField.buffer)==147 && ST_UTF8Valid(chatField.buffer));
    ST_ChatInsert('a');ST_ChatInsert('b');ST_ChatInsert('c');
    assert(strlen(chatField.buffer)==149 && ST_UTF8Valid(chatField.buffer));
    ST_ChatInsert(0x202e);assert(strlen(chatField.buffer)==149);
    stchat::Rasterizer raster;assert(raster.init(argv[1]));
    const char *texts[]={u8"^2日本語のチーム",u8"^5我的队伍在哪里？",u8"^6我的隊伍在哪裡？",
        u8"^7우리 팀은 어디에 있나요?",u8"^5[AR] Tester: أين فريقي؟ أحتاج إلى المساعدة.",
        u8"^2मेरी टीम कहाँ है? मुझे मदद चाहिए।",u8"^5Где моя команда? Українська",u8"^2Gdzie jest mój zespół?"};
    for(auto text:texts){
        stchat::Bitmap bitmap;assert(raster.render(text,400,22,36,0,bitmap));
        assert(bitmap.lines>0 && bitmap.lines<=16 && bitmap.rgba.size()==bitmap.width*bitmap.height*4);
        unsigned visible=0;for(size_t i=3;i<bitmap.rgba.size();i+=4)visible+=bitmap.rgba[i]>0;
        assert(visible>100);
    }
    stchat::Bitmap bitmap;assert(!raster.render("x",4096,22,36,0,bitmap));
    puts("UTF-8 boundaries, editing, paste, byte limits and bundled-script rasterization passed.");
}
