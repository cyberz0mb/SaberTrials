#include "st_translation_core.h"
#include <cassert>
#include <cstdio>
using Clock=std::chrono::steady_clock;

int wmain(int argc,wchar_t **argv) {
    assert(argc==2);
    stTranslationResult_t result={};
    assert(sttr::parse("STTR2 7 ok 68656c6c6f\n",7,1,result) && !strcmp(result.text,"hello"));
    assert(!sttr::parse("STTR2 8 ok 6869\n",7,1,result));
    assert(!sttr::parse("STTR2 7 ok 68690a71756974\n",7,1,result));
    assert(!sttr::parse("STTR2 7 ok 5e31\n",7,1,result));
    assert(!sttr::parse("STTR2 7 missing -\n",7,1,result));
    assert(!sttr::parse("STTR2 7 ok f0808080\n",7,1,result));
    assert(sttr::parse("STTR2 7 ok e697a5e69cace8aa9e\n",7,1,result));
    sttr::Worker worker;
    stTranslationRequest_t request={};request.source=0;request.target=1;
    strcpy(request.text,"\xBF" "D\xF3nde est\xE1 mi equipo? Necesito ayuda.");
    auto before=Clock::now();unsigned ticket=worker.submit(request,argv[1]);
    assert(ticket && Clock::now()-before<std::chrono::milliseconds(100));
    auto deadline=Clock::now()+std::chrono::seconds(15);
    while(!worker.poll(result) && Clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(10));
    assert(result.ticket==ticket && strstr(result.text,"team") && strstr(result.text,"help"));
    const char *incoming[]={u8"Где моя команда? Мне нужна помощь.",u8"私のチームはどこですか？助けが必要です。",
        u8"我的队伍在哪里？我需要帮助。",u8"أين فريقي؟ أحتاج إلى المساعدة.",
        u8"Wo ist mein Team? Ich brauche Hilfe.",u8"मेरी टीम कहाँ है? मुझे मदद चाहिए।"};
    for(auto text:incoming) {
        strcpy(request.text,text);ticket=worker.submit(request,argv[1]);result={};
        deadline=Clock::now()+std::chrono::seconds(10);
        while(!worker.poll(result) && Clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(10));
        assert(result.ticket==ticket && result.text[0] && ST_UTF8Valid(result.text));
    }
    request.source=7;request.target=14;strcpy(request.text,incoming[3]);
    ticket=worker.submit(request,argv[1]);result={};deadline=Clock::now()+std::chrono::seconds(10);
    while(!worker.poll(result) && Clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(10));
    assert(result.ticket==ticket && ST_UTF8Valid(result.text));
    int accepted=0;
    for(int i=0;i<200;++i)if(worker.submit(request,argv[1]))++accepted;
    assert(accepted<=18);
    before=Clock::now();worker.reset();
    assert(Clock::now()-before<std::chrono::milliseconds(100));
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    assert(!worker.poll(result));
    worker.shutdown();
    sttr::Worker missing;assert(missing.submit(request,L"Z:\\nonexistent-saber-trials-translator"));
    deadline=Clock::now()+std::chrono::seconds(3);
    while(missing.status!=2 && Clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(10));
    assert(missing.status==2 && !missing.poll(result));missing.shutdown();
    puts("Native pipe protocol, real translation, bounded queue, cancellation and missing-helper checks passed.");
}
