/* Only the chat field changes encoding; console and menu fields keep their ABI. */
#include "qcommon/st_utf8.h"
static void ST_ChatInsert(unsigned cp) {
    if(cp<32 || cp==127 || (cp>=0x202a&&cp<=0x202e) || (cp>=0x2066&&cp<=0x2069))return;
    char bytes[4];int count=ST_UTF8Write(cp,bytes);if(!count)return;
    int length=(int)strlen(chatField.buffer),cursor=chatField.cursor,remove=0;
    if(kg.key_overstrikeMode && cursor<length)ST_UTF8Read(chatField.buffer+cursor,&remove);
    if(length-remove+count>=MAX_SAY_TEXT)return;
    memmove(chatField.buffer+cursor+count,chatField.buffer+cursor+remove,length-cursor-remove+1);
    memcpy(chatField.buffer+cursor,bytes,count);chatField.cursor+=count;
}
static void ST_ChatPaste() {
    char *text=Sys_GetClipboardData();if(!text)return;
    for(const char *p=text;*p;){int n;unsigned c=ST_UTF8Read(p,&n);ST_ChatInsert(c);p+=n;}
    Z_Free(text);
}
static void ST_ChatChar(int ch) {
    if(ch==22){ST_ChatPaste();return;}
    if(ch==3){Field_Clear(&chatField);return;}
    if(ch==1){chatField.cursor=0;return;}
    if(ch==5){chatField.cursor=(int)strlen(chatField.buffer);return;}
    if(ch==8){int previous=ST_UTF8Previous(chatField.buffer,chatField.cursor);
        memmove(chatField.buffer+previous,chatField.buffer+chatField.cursor,strlen(chatField.buffer+chatField.cursor)+1);
        chatField.cursor=previous;return;}
    ST_ChatInsert((unsigned)ch);
}
static void ST_ChatKey(int key) {
    int length=(int)strlen(chatField.buffer),cursor=chatField.cursor,n;
    if(((key==A_INSERT)||(key==A_KP_0)) && kg.keys[A_SHIFT].down){ST_ChatPaste();return;}
    switch(key) {
    case A_DELETE:if(cursor<length){ST_UTF8Read(chatField.buffer+cursor,&n);memmove(chatField.buffer+cursor,chatField.buffer+cursor+n,length-cursor-n+1);}break;
    case A_CURSOR_LEFT:chatField.cursor=ST_UTF8Previous(chatField.buffer,cursor);break;
    case A_CURSOR_RIGHT:if(cursor<length){ST_UTF8Read(chatField.buffer+cursor,&n);chatField.cursor+=n;}break;
    case A_HOME:chatField.cursor=0;break;
    case A_END:chatField.cursor=length;break;
    case A_INSERT:kg.key_overstrikeMode=(qboolean)!kg.key_overstrikeMode;break;
    default:break;
    }
}
