/* UTF-8 chat boundaries, with legacy Windows-1252 fallback for received text. */
#ifndef ST_UTF8_H
#define ST_UTF8_H
#include <stddef.h>
#include <string.h>
static unsigned ST_UTF8Read(const char *text,int *bytes) {
    const unsigned char *p=(const unsigned char *)text;
    unsigned c=p[0],value;int n,i;
    *bytes=1;if(c<128)return c;
    n=c>=0xc2&&c<=0xdf?2:c>=0xe0&&c<=0xef?3:c>=0xf0&&c<=0xf4?4:0;
    if(!n)return 0xfffd;
    value=c&((1u<<(7-n))-1);
    for(i=1;i<n;++i){if(!p[i] || (p[i]&0xc0)!=0x80)return 0xfffd;value=(value<<6)|(p[i]&63);}
    if((n==3&&value<0x800)||(n==4&&value<0x10000)||value>0x10ffff||(value>=0xd800&&value<=0xdfff))return 0xfffd;
    *bytes=n;return value;
}
static int ST_UTF8Write(unsigned c,char *out) {
    if(c>0x10ffff || (c>=0xd800&&c<=0xdfff))return 0;
    if(c<128){out[0]=(char)c;return 1;}
    if(c<0x800){out[0]=(char)(0xc0|(c>>6));out[1]=(char)(0x80|(c&63));return 2;}
    if(c<0x10000){out[0]=(char)(0xe0|(c>>12));out[1]=(char)(0x80|((c>>6)&63));out[2]=(char)(0x80|(c&63));return 3;}
    out[0]=(char)(0xf0|(c>>18));out[1]=(char)(0x80|((c>>12)&63));out[2]=(char)(0x80|((c>>6)&63));out[3]=(char)(0x80|(c&63));return 4;
}
static int ST_UTF8Previous(const char *s,int position) {
    if(position<=0)return 0;
    --position;while(position>0&&((unsigned char)s[position]&0xc0)==0x80)--position;
    return position;
}
static int ST_UTF8Valid(const char *s) {
    while(*s){int n;unsigned c=ST_UTF8Read(s,&n);if(c==0xfffd && n==1)return 0;s+=n;}
    return 1;
}
static int ST_UTF8Sanitize(const char *s,char *out,int capacity) {
    static const unsigned cp1252[32]={0x20ac,0xfffd,0x201a,0x192,0x201e,0x2026,0x2020,0x2021,0x2c6,0x2030,0x160,0x2039,0x152,0xfffd,0x17d,0xfffd,
        0xfffd,0x2018,0x2019,0x201c,0x201d,0x2022,0x2013,0x2014,0x2dc,0x2122,0x161,0x203a,0x153,0xfffd,0x17e,0x178};
    int used=0;
    while(*s && used<capacity-1){int n;char encoded[4];unsigned c=ST_UTF8Read(s,&n);
        if(c==0xfffd&&n==1){c=(unsigned char)*s;if(c>=128&&c<160)c=cp1252[c-128];}
        int size=ST_UTF8Write(c,encoded);if(used+size>=capacity)break;
        memcpy(out+used,encoded,size);used+=size;s+=n;
    }
    out[used]=0;return used;
}
#endif
