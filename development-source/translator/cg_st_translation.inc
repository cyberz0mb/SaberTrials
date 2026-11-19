/* Submit only chat already delivered and accepted by this client's filters. */
#include "qcommon/st_utf8.h"
#include "qcommon/st_translation_languages.h"
static int STTR_Cvar(const char *name) {
    char value[16];trap->Cvar_VariableStringBuffer(name,value,sizeof(value));return atoi(value);
}
void STTR_ReceivedChat(const char *text,int sender,int team,const char *locationBody) {
    stTranslationRequest_t request;
    char publicPrefix[128],teamPrefix[128],privatePrefix[128],prefix[512];
    int channel=0;size_t prefixLength=0;
    if(!STTR_Cvar("st_translate") || cg_chatBox.integer<=0 ||
       sender<0 || sender>=MAX_CLIENTS || !cgs.clientinfo[sender].infoValid)return;
    const char *name=cgs.clientinfo[sender].name;
    Com_sprintf(publicPrefix,sizeof(publicPrefix),"%s^7: %s",name,locationBody?"":"^2");
    Com_sprintf(teamPrefix,sizeof(teamPrefix),"(%s^7): %s",name,locationBody?"":"^5");
    Com_sprintf(privatePrefix,sizeof(privatePrefix),"[%s^7]: %s",name,locationBody?"":"^6");
    if(team && !strncmp(text,teamPrefix,strlen(teamPrefix))){channel=2;prefixLength=strlen(teamPrefix);}
    else if(!team && !strncmp(text,privatePrefix,strlen(privatePrefix))){channel=3;prefixLength=strlen(privatePrefix);}
    else if(!team && !locationBody && !strncmp(text,publicPrefix,strlen(publicPrefix))){channel=1;prefixLength=strlen(publicPrefix);}
    if(!channel)return;
    if(locationBody) {
        size_t bodyLength=strlen(locationBody),textLength=strlen(text);
        if(!bodyLength || textLength<bodyLength || strcmp(text+textLength-bodyLength,locationBody))return;
        prefixLength=textLength-bodyLength;
    }
    if(prefixLength>=sizeof(prefix) || !text[prefixLength])return;
    chatBoxItem_t *chat=&cg.chatItems[(cg.chatItemActive+MAX_CHATBOX_ITEMS-1)%MAX_CHATBOX_ITEMS];
    if(strcmp(chat->string,text))return;
    memcpy(prefix,text,prefixLength);prefix[prefixLength]=0;
    memset(&request,0,sizeof(request));
    request.source=STTR_Cvar("st_translateSource");request.target=STTR_Cvar("st_translateTarget");
    ST_UTF8Sanitize(text+prefixLength,request.text,sizeof(request.text));
    for(int i=0;i<MAX_CLIENTS;++i)if(cgs.clientinfo[i].infoValid) {
        char clean[MAX_NETNAME],utf8[MAX_NETNAME*3];
        Q_strncpyz(clean,cgs.clientinfo[i].name,sizeof(clean));Q_CleanStr(clean);
        ST_UTF8Sanitize(clean,utf8,sizeof(utf8));
        if(strlen(request.names)+strlen(utf8)+2<sizeof(request.names)) {
            Q_strcat(request.names,sizeof(request.names),utf8);Q_strcat(request.names,sizeof(request.names),"\n");
        }
    }
    chat->translationTicket=trap->ST_TranslateSubmit(&request);
    chat->translationTarget=request.target;chat->translationSource=request.source;
    chat->translationChannel=channel;chat->translationTime=cg.time;
    ST_UTF8Sanitize(prefix,chat->translationPrefix,sizeof(chat->translationPrefix));
}

static void STTR_ChatPoll(void) {
    stTranslationResult_t result;
    int count=0;
    int enabled=STTR_Cvar("st_translate"),source=STTR_Cvar("st_translateSource"),target=STTR_Cvar("st_translateTarget");
    for(int i=0;i<MAX_CHATBOX_ITEMS;++i) {
        chatBoxItem_t *chat=&cg.chatItems[i];
        if(chat->translationTicket && (!enabled || chat->translationSource!=source || chat->translationTarget!=target ||
           cg.time-chat->translationTime>9000))chat->translationTicket=0;
    }
    while(count++<16 && trap->ST_TranslatePoll(&result)) {
        for(int i=0;i<MAX_CHATBOX_ITEMS;++i) {
            chatBoxItem_t *chat=&cg.chatItems[i];
            if(chat->translationTicket && chat->translationTicket==result.ticket && chat->translationTarget==result.target) {
                Com_sprintf(chat->translated,sizeof(chat->translated),"^5[%s] ^7%s%s",
                    ST_LanguageTag(result.target),chat->translationPrefix,result.text);
                chat->translationTicket=0;
                break;
            }
        }
    }
}

static const char *STTR_ChatText(const chatBoxItem_t *chat,char *buffer,int size) {
    if(!chat->translated[0] || !STTR_Cvar("st_translate") ||
       chat->translationTarget!=STTR_Cvar("st_translateTarget"))return chat->string;
    if(STTR_Cvar("st_translateOriginal")) {
        Com_sprintf(buffer,size,"%s\n%s",chat->string,chat->translated);return buffer;
    }
    return chat->translated;
}

void STTR_Inspect(void) {
    char status[128];int translated=0,pending=0,channels[4]={0};
    trap->Cvar_VariableStringBuffer("st_translationStatus",status,sizeof(status));
    for(int i=0;i<MAX_CHATBOX_ITEMS;++i) {if(cg.chatItems[i].translated[0]){++translated;++channels[Com_Clampi(0,3,cg.chatItems[i].translationChannel)];}if(cg.chatItems[i].translationTicket)++pending;}
    Com_Printf("ST_TRANSLATOR enabled=%d source=%d target=%d translated=%d pending=%d public=%d team=%d private=%d status=%s\n",
        STTR_Cvar("st_translate"),STTR_Cvar("st_translateSource"),STTR_Cvar("st_translateTarget"),translated,pending,channels[1],channels[2],channels[3],status);
}
