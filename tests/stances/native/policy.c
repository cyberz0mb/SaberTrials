#include <stdio.h>
#include <string.h>
#include "st_stance_policy.h"
#define CHECK(x) do { if(!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); return 1; } } while(0)
int main(void) {
    int p[12], q[12], words[3], i, id, slot, tests=0;
    char text[13];
    for(slot=0;slot<12;slot++)for(id=-1;id<=17;id++) {
        int family=slot<6?0:slot<9?1:2;
        int expected=id==0 || (family==0 && id>=1 && id<=10) ||
            (family==1 && id>=11 && id<=12) || (family==2 && id>=13 && id<=14);
        CHECK(ST_StanceAllowed(slot,id)==expected); tests++;
    }
    CHECK(!ST_StanceAllowed(-1,1)); CHECK(!ST_StanceAllowed(12,1));
    CHECK(ST_StanceParse("123456bccdee",p));
    ST_StancePack(p,words);
    for(i=0;i<3;i++) words[i]=(short)words[i]; /* network ReadShort sign extension */
    ST_StanceUnpack(words,q);
    for(i=0;i<12;i++) CHECK(p[i]==q[i]);
    ST_StanceFormat(q,text); CHECK(!strcmp(text,"123456bccdee"));
    CHECK(ST_StanceParse("123456BCCDEE",p));
    CHECK(!ST_StanceParse("123456bccdeex",p));
    for(i=0;i<12;i++)CHECK(p[i]==0);
    CHECK(!ST_StanceParse("123456bccde",p));
    CHECK(!ST_StanceParse("123456bccde!",p));
    CHECK(ST_StanceParse("ffffffffffff",p));
    for(i=0;i<12;i++) CHECK(p[i]==0); /* preview-only and foreign family cannot activate */
    CHECK(ST_StanceParse("123456bccdee",p));
    ST_StancePack(p,words);
    for(i=0;i<12;i++) {
        CHECK(ST_StanceChoice(words,i,1)==p[i]);
        CHECK(ST_StanceChoice(words,i,0)==0);
    }
    CHECK(ST_StanceChoice(words,-1,1)==0);
    CHECK(ST_StanceChoice(words,12,1)==0);
    printf("PASS: %d compatibility cases; parse, corrupt input, signed snapshot round trip, missing library\n",tests);
    return 0;
}
