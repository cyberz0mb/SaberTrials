#include <cassert>
#include <cstring>
#include <cstdio>
#include <string>
#define MAX_CHAT_LINE_SIZE 128
#define MAX_CHAT_BUFFER_SIZE 8192
#define ARRAY_LEN(x) (sizeof(x)/sizeof((x)[0]))
#define SAY_ALL 0
struct Client { struct { char netname[64]; } pers; };
struct gentity_t { Client *client; };
struct bot_state_t {
    int client, canChat, doChat, chatFrequency, chatTeam, chatTime_stored, chatTime, stNextChat;
    gentity_t *chatObject, *chatAltObject, *currentEnemy;
    char currentChat[MAX_CHAT_LINE_SIZE];
};
struct { int time; } level;
struct { int integer; } st_botTricksterChat;
char gBotChatBuffer[4][MAX_CHAT_BUFFER_SIZE];
gentity_t g_entities[4];
static int randomOffset, sent;
static std::string spoken;
int Q_irand(int lo, int hi) { return lo + randomOffset % (hi-lo+1); }
int Com_Clampi(int lo, int hi, int x) { return x < lo ? lo : x > hi ? hi : x; }
void G_Say(gentity_t *, gentity_t *, int, const char *s) { spoken=s; ++sent; }
#include "../../development-source/bot-chat/ai_st_chat.inc"
#include "../../development-source/bot-chat/st_bot_profile.h"

static bot_state_t setup(const char *text) {
    bot_state_t bs={}; bs.canChat=1; bs.chatFrequency=10;
    strcpy(gBotChatBuffer[0],text); level.time=20000; st_botTricksterChat.integer=12000;
    randomOffset=0; sent=0; spoken.clear(); return bs;
}
int main() {
    char group[1024], value[64];
    for (auto newline : {"\n","\r\n","\r\r\n"}) {
        std::string profile=std::string("// note { ignored }")+newline+"GeneralBotInfo"+newline+newline+
            "{"+newline+"chatability 1 // enabled"+newline+"chatfrequency 7"+newline+"}";
        assert(ST_ProfileGroup(profile.c_str(),"GeneralBotInfo",group,sizeof(group)));
        assert(ST_ProfileValue(group,"chatability",value,sizeof(value)) && !strcmp(value,"1"));
        assert(ST_ProfileValue(group,"chatfrequency",value,sizeof(value)) && !strcmp(value,"7"));
        assert(!ST_ProfileValue(group,"chat",value,sizeof(value)));
    }
    assert(ST_ProfileGroup("EmotionalAttachments { Luke { 1 } } GeneralBotInfo { chatability 1 }",
        "GeneralBotInfo",group,sizeof(group)));
    assert(ST_ProfileValue(group,"chatability",value,sizeof(value)) && !strcmp(value,"1"));
    assert(!ST_ProfileGroup("GeneralBotInfo {", "GeneralBotInfo",group,sizeof(group)));
    assert(!ST_ProfileGroup("GeneralBotInfo { long value }", "GeneralBotInfo",group,3));
    assert(!ST_ProfileValue("chatability", "chatability",value,sizeof(value)));
    assert(!ST_ProfileValue("// comment without newline", "chatability",value,sizeof(value)));
    const char *events[]={"GeneralGreetings","ResponseGreetings","Killed","Died","Hatred",
        "KilledHatedOne","OrderAccepted","BelovedKilled","KilledOnPurposeByLove","LovedOneKilledLovedOne"};
    // Every event uses its own profile group, on LF/CRLF/CRCRLF, with blanks/comments.
    for (auto newline : {"\n","\r\n","\r\r\n"}) for (auto event : events) {
        std::string profile=std::string("// header")+newline+event+newline+"{"+newline+
            "   // ignored"+newline+"   "+newline+"   Character line."+newline+"}";
        auto bs=setup(profile.c_str());
        assert(BotDoChat(&bs,(char*)event,1));
        assert(!strcmp(bs.currentChat,"Character line."));
        assert(bs.doChat==(!strcmp(event,"GeneralGreetings")?2:1));
        assert(bs.chatTime>level.time);
        assert(!BotDoChat(&bs,(char*)event,1)); // queued message is never overwritten
    }
    // Correct first/last selection without relying on trailing newlines.
    auto bs=setup("Killed {\nfirst\nlast}"); randomOffset=1;
    assert(BotDoChat(&bs,(char*)"Killed",1)); assert(!strcmp(bs.currentChat,"last"));
    bs=setup("Killed {\nfirst\nlast}"); assert(BotDoChat(&bs,(char*)"Killed",1));
    assert(!strcmp(bs.currentChat,"first"));
    assert(!ST_ChatLines(gBotChatBuffer[0],"Kill",-1,nullptr,0));
    assert(!ST_ChatLines("Killed {\nincomplete",nullptr,-1,nullptr,0));
    assert(!ST_ChatLines("Killed {\n// comment\n \n}",nullptr,-1,nullptr,0));
    assert(ST_ChatLines("Killed {\n// comment with } brace\nStill here.\n}","Killed",-1,nullptr,0)==1);

    Client target={},alt={}; strcpy(target.pers.netname,"Player"); strcpy(alt.pers.netname,"Teammate");
    gentity_t t={&target},a={&alt}; char line[128];
    assert(ST_ChatExpand("100%% ready, %s and %a! %x",&t,&a,line,sizeof(line)));
    assert(!strcmp(line,"100% ready, Player and Teammate! %x"));
    assert(ST_ChatExpand("Hello %s",nullptr,nullptr,line,sizeof(line)));
    assert(!strcmp(line,"Hello opponent"));
    memset(target.pers.netname,'x',63); target.pers.netname[63]=0;
    assert(!ST_ChatExpand("%s%s%s",&t,nullptr,line,sizeof(line)) && !line[0]);
    assert(ST_ChatExpand("Olá, 世界!",nullptr,nullptr,line,sizeof(line)));
    assert(!strcmp(line,"Olá, 世界!"));
    assert(!ST_ChatLines(("Killed {"+std::string(128,'x')+"}").c_str(),nullptr,-1,nullptr,0));

    bs=setup("CombatChat {\nCharacter combat line.\n}\nHatred {\nLegacy combat line.\n}");
    ST_BotTricksterChat(&bs); assert(sent==1 && spoken=="Character combat line.");
    ST_BotTricksterChat(&bs); assert(sent==1); // cooldown
    level.time+=12000; ST_BotTricksterChat(&bs); assert(sent==2);
    bs=setup("Hatred {\nLegacy character line.\n}");
    ST_BotTricksterChat(&bs); assert(sent==1 && spoken=="Legacy character line.");
    bs=setup("Killed {\nVictory only.\n}");
    ST_BotTricksterChat(&bs); assert(!sent); // no out-of-context or generic remarks
    bs=setup("CombatChat {\nCustom.\n}"); bs.canChat=0;
    ST_BotTricksterChat(&bs); assert(!sent); // profile silence respected
    bs=setup("CombatChat {\nCustom.\n}"); bs.chatFrequency=0;
    ST_BotTricksterChat(&bs); assert(!sent); // frequency failure must not trigger fallback
    bs=setup("CombatChat {\nCustom.\n}"); bs.doChat=1;
    ST_BotTricksterChat(&bs); assert(!sent); // scheduled character line takes priority
    bs=setup(""); ST_BotTricksterChat(&bs);
    assert(sent==1 && spoken=="Relax. I am only passing through.");
    bs=setup("Killed {\n// no authored remarks\n}"); ST_BotTricksterChat(&bs);
    assert(sent==1); // empty profile gets the existing fallback
    bs=setup("Killed {\nCustom.\n}"); bs.canChat=0;
    assert(!BotDoChat(&bs,(char*)"Killed",1));
    bs=setup("Killed {\nCustom.\n}"); bs.chatFrequency=0;
    assert(!BotDoChat(&bs,(char*)"Killed",0));
    assert(BotDoChat(&bs,(char*)"Killed",1));
    puts("Bot profile priority and dialogue safety passed.");
}
