#include <assert.h>
#include <math.h>
#include "st_mvp_wire.h"
int main(void) {
    unsigned char source[1024],decoded[1024],bytes[1024]; char text[1400],name[20];
    stMvpWire_t w,r; int i,n;
    for(i=0;i<1024;++i)source[i]=(unsigned char)(i*73);
    for(i=0;i<=1024;++i) {
        n=ST_MvpEncode(source,i,text,sizeof(text)); assert(n>=0);
        assert(ST_MvpDecode(text,decoded,i)==i && !memcmp(source,decoded,i));
        if(i)assert(ST_MvpDecode(text,decoded,i-1)==-1);
    }
    assert(ST_MvpDecode("A",decoded,1024)==-1);
    assert(ST_MvpDecode("AB",decoded,1024)==-1);
    assert(ST_MvpDecode("a b",decoded,1024)==-1);
    ST_WInit(&w,bytes,sizeof(bytes)); ST_WInt(&w,-1234); ST_WFloat(&w,1.25f); ST_WText(&w,"Player ^1Name",20);
    ST_WInit(&r,bytes,w.pos); assert(ST_RInt(&r)==-1234);assert(ST_RFloat(&r)==1.25f);
    ST_RText(&r,name,sizeof(name));assert(r.ok && !strcmp(name,"Player ^1Name"));
    ST_RInt(&r);assert(!r.ok);
    for(i=0;i<w.pos;++i){ST_WInit(&r,bytes,i);ST_RInt(&r);ST_RFloat(&r);ST_RText(&r,name,sizeof(name));assert(!r.ok);}
    ST_WInit(&w,bytes,4);ST_WInt(&w,-1);ST_WInit(&r,bytes,4);ST_RText(&r,name,sizeof(name));assert(!r.ok);
    ST_WInit(&w,bytes,4);ST_WInt(&w,0x7f800000);ST_WInit(&r,bytes,4);ST_RFloat(&r);assert(!r.ok);
    ST_WInit(&w,bytes,3);ST_WInt(&w,1);assert(!w.ok);
    return 0;
}
