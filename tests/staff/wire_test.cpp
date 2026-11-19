#include "st_staff_wire.h"
#include "check.h"
RUN_TEST(
 CHECK(st::NumericAddress("127.0.0.1:27960"));
 CHECK(st::NumericAddress("[::1]:27960"));
 for(const char* s:{"example.com:27960","1.2.3.4:0","1.2.3.4:65536","1.2.3.4:27960;quit","1.2.3.4:27960\nquit","999.2.3.4:22","[::1]","[::1]:-1","1.2.3.4:abc"})CHECK(!st::NumericAddress(s));
 st::Nonce session={};session[0]=1;st::Bytes transcript(148,42);
 auto message=st::SessionMessage(transcript,session);st::Nonce parsed={};CHECK(st::ReadSessionMessage(message,transcript,parsed));CHECK(parsed==session);
 transcript[0]++;CHECK(!st::ReadSessionMessage(message,transcript,parsed));
 bool ok;std::string result;auto reply=st::ResultMessage(session,5,true,"completed");
 CHECK(st::ReadResultMessage(reply,session,5,ok,result)&&ok&&result=="completed");
 CHECK(!st::ReadResultMessage(reply,session,6,ok,result));
 session[0]++;CHECK(!st::ReadResultMessage(reply,session,5,ok,result));
)
