#include "st_staff_protocol.h"
#include "check.h"
#include <cstdio>
RUN_TEST(
    st::Request event; event.sequence=1; event.command=17; event.args={"pause","Connection issue"};
    st::Request decodedEvent;
    CHECK(st::ParseRequest(st::Encode(event),decodedEvent));
    CHECK(decodedEvent.args==event.args);
    event.args={"pause"}; CHECK(st::Encode(event).empty());
    event.args={"disqualify","2","Rule violation"}; CHECK(!st::Encode(event).empty());
    event.args={"open","2"}; CHECK(st::Encode(event).empty());
    // The appended aim resolver carries no client-supplied target or arguments.
    st::Request aim; aim.sequence=1; aim.command=ST_CMD_LOGOUT+1;
    st::Request decodedAim;
    CHECK(st::ParseRequest(st::Encode(aim),decodedAim));
    CHECK(decodedAim.command==aim.command);
    aim.target.slot=1; CHECK(st::Encode(aim).empty());
    aim.target={}; aim.args={"#1"}; CHECK(st::Encode(aim).empty());
    std::remove("proto.db"); std::remove("proto-client.key"); std::remove("proto-server.key");
    st::Identity client, server;
    CHECK(client.LoadOrCreate("proto-client.key",true));
    CHECK(server.LoadOrCreate("proto-server.key",true));
    st::Store db; CHECK(db.Open("proto.db")); CHECK(db.BootstrapOwner(client.PublicId(),"Owner"));
    st::Authority auth(db,server);
    st::Generation gen = {}; gen[0] = 42;
    st::Nonce nonce = {}; nonce[0] = 24;
    auto challenge = auth.Begin(0,gen,client.PublicId(),nonce,100);
    CHECK(challenge.ok);
    CHECK(st::Identity::Verify(server.PublicId(),challenge.transcript,challenge.signature));
    CHECK(!auth.Complete(0,client.Sign(challenge.transcript),30100).ok);
    challenge = auth.Begin(0,gen,client.PublicId(),nonce,31100); CHECK(challenge.ok);
    auto session = auth.Complete(0,client.Sign(challenge.transcript),31101); CHECK(session.ok);
    auto retransmit=auth.Complete(0,client.Sign(challenge.transcript),31102);
    CHECK(retransmit.ok&&retransmit.duplicate&&retransmit.id==session.id&&retransmit.transcript==session.transcript);
    st::Request req; req.session = session.id; req.sequence=1; req.command=ST_CMD_LIST;
    auto bytes=st::Encode(req); auto sig=client.Sign(bytes);
    auto verified=auth.Verify(0,gen,bytes,sig,31103); CHECK(verified.ok && !verified.duplicate);
    auth.Remember(0,1,"done");
    verified=auth.Verify(0,gen,bytes,sig,31104); CHECK(verified.ok && verified.duplicate && verified.result=="done");
    retransmit=auth.Complete(0,client.Sign(challenge.transcript),31105);
    CHECK(retransmit.ok&&retransmit.duplicate&&retransmit.id==session.id);
    verified=auth.Verify(0,gen,bytes,sig,31106);CHECK(verified.ok&&verified.duplicate&&verified.result=="done");
    req.command=ST_CMD_GHOST_ON; auto altered=st::Encode(req);
    CHECK(!auth.Verify(0,gen,altered,client.Sign(altered),31105).ok);
    gen[1]=1; CHECK(!auth.Verify(0,gen,bytes,sig,31106).ok); gen[1]=0;
    req.sequence=2; bytes=st::Encode(req); sig=client.Sign(bytes); sig[0]^=1;
    CHECK(!auth.Verify(0,gen,bytes,sig,31107).ok);
    CHECK(!st::ParseRequest(st::Bytes(2000,0),req));
    // Each field is signed; no byte can be changed without invalidating the transcript.
    for(size_t i=0;i<challenge.transcript.size();i++){
        auto changed=challenge.transcript;changed[i]^=1;
        CHECK(!st::Identity::Verify(server.PublicId(),changed,challenge.signature));
    }
    req.session=session.id;req.command=ST_CMD_LIST;req.args.clear();req.target={};
    for(uint64_t seq=2;seq<68;seq++){
        req.sequence=seq;auto b=st::Encode(req);CHECK(auth.Verify(0,gen,b,client.Sign(b),31200+seq).ok);auth.Remember(0,seq,"cached");
    }
    req.sequence=1;bytes=st::Encode(req);CHECK(!auth.Verify(0,gen,bytes,client.Sign(bytes),32000).ok);
    req.sequence=68;bytes=st::Encode(req);
    auto background=auth.Begin(0,gen,client.PublicId(),nonce,32500);
    CHECK(background.ok);
    CHECK(auth.Verify(0,gen,bytes,client.Sign(bytes),32501).ok); // unauthenticated hello must not log out an active staff member
    st::Authority otherServer(db,server);
    auto otherChallenge=otherServer.Begin(0,gen,client.PublicId(),nonce,33000);
    CHECK(otherChallenge.ok);
    CHECK(!otherServer.Complete(0,client.Sign(challenge.transcript),33001).ok);
    auto noRandom=[](void*,size_t)->bool{return false;};
    st::Authority brokenRandom(db,server,noRandom);
    CHECK(!brokenRandom.Begin(0,gen,client.PublicId(),nonce,100).ok);
    CHECK(db.ConsoleChange(client.PublicId(),st::Role::Owner,"Owner",true));
    CHECK(!auth.Verify(0,gen,bytes,client.Sign(bytes),33002).ok); // revision changed
    auth.Reset();
    for(int i=0;i<5;i++){
        auto bad=auth.Begin(0,gen,client.PublicId(),nonce,40000+i*1100);CHECK(bad.ok);
        CHECK(!auth.Complete(0,st::Bytes(64,0),40001+i*1100).ok);
    }
    CHECK(!auth.Begin(0,gen,client.PublicId(),nonce,46000).ok);
    CHECK(auth.Begin(0,gen,client.PublicId(),nonce,76000).ok);
    // Two connections may use the same imported identity; one disconnect cannot revoke the other.
    st::Generation secondGen=gen;secondGen[3]=7;
    challenge=auth.Begin(1,secondGen,client.PublicId(),nonce,76001);CHECK(challenge.ok);
    auto second=auth.Complete(1,client.Sign(challenge.transcript),76002);CHECK(second.ok);
    auth.Disconnect(0);CHECK(auth.Current(1).enabled);
    req=st::Request();req.session=second.id;req.sequence=1;req.command=ST_CMD_LIST;
    bytes=st::Encode(req);CHECK(auth.Verify(1,secondGen,bytes,client.Sign(bytes),76003).ok);
    CHECK(!auth.Complete(1,client.Sign(challenge.transcript),106002).ok); // receipt cache is bounded
    CHECK(db.ConsoleChange(client.PublicId(),st::Role::Owner,"Owner",true));
    CHECK(!auth.Complete(1,client.Sign(challenge.transcript),106003).ok);
    auth.Reset(); CHECK(!auth.Verify(0,gen,bytes,sig,31108).ok);
    db.Close(); std::remove("proto.db"); std::remove("proto-client.key"); std::remove("proto-server.key");
)
