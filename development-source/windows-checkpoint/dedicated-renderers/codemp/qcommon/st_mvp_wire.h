/* Bounded, pointer-free replay encoding. GPL-2.0-or-later. */
#ifndef ST_MVP_WIRE_H
#define ST_MVP_WIRE_H
#include <stdint.h>
#include <string.h>
#define ST_MVP_WIRE_VERSION 1
#define ST_MVP_WIRE_LIMIT (8*1024*1024)
#define ST_MVP_POSE_LIMIT (128*1024)
#define ST_MVP_CHUNK 540
typedef struct { unsigned char *data; int size,pos,ok; } stMvpWire_t;
static void ST_WInit(stMvpWire_t *w,void *data,int size) {
    w->data=(unsigned char *)data; w->size=size; w->pos=0; w->ok=size>=0;
}
static void ST_WBytes(stMvpWire_t *w,const void *data,int size) {
    if (!w->ok || size<0 || size>w->size-w->pos) { w->ok=0; return; }
    memcpy(w->data+w->pos,data,size); w->pos+=size;
}
static const unsigned char *ST_RBytes(stMvpWire_t *w,int size) {
    const unsigned char *p;
    if (!w->ok || size<0 || size>w->size-w->pos) { w->ok=0; return NULL; }
    p=w->data+w->pos; w->pos+=size; return p;
}
static void ST_WInt(stMvpWire_t *w,int value) {
    uint32_t v=(uint32_t)value;
    unsigned char b[4]={(unsigned char)v,(unsigned char)(v>>8),(unsigned char)(v>>16),(unsigned char)(v>>24)};
    ST_WBytes(w,b,4);
}
static int ST_RInt(stMvpWire_t *w) {
    const unsigned char *b=ST_RBytes(w,4);
    if (!b) return 0;
    return (int)((uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24));
}
static void ST_WFloat(stMvpWire_t *w,float value) {
    int bits;
    if (!(value>=-1e9f && value<=1e9f)) { w->ok=0; return; }
    memcpy(&bits,&value,4); ST_WInt(w,bits);
}
static float ST_RFloat(stMvpWire_t *w) {
    int bits=ST_RInt(w); float value;
    memcpy(&value,&bits,4);
    if (!(value>=-1e9f && value<=1e9f)) { w->ok=0; return 0; }
    return value;
}
static void ST_WVec(stMvpWire_t *w,const float *v) { int i; for(i=0;i<3;++i) ST_WFloat(w,v[i]); }
static void ST_RVec(stMvpWire_t *w,float *v) { int i; for(i=0;i<3;++i) v[i]=ST_RFloat(w); }
static void ST_WText(stMvpWire_t *w,const char *s,int limit) {
    int n=0; while(n<limit && s[n]) ++n;
    if(n==limit) { w->ok=0; return; }
    ST_WInt(w,n); ST_WBytes(w,s,n);
}
static void ST_RText(stMvpWire_t *w,char *s,int limit) {
    int n=ST_RInt(w); const unsigned char *p;
    s[0]=0;
    if(n<0 || n>=limit) { w->ok=0; return; }
    p=ST_RBytes(w,n); if(!p) return;
    if(memchr(p,0,n)) { w->ok=0; return; }
    memcpy(s,p,n); s[n]=0;
}
static const char stMvpAlphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
static int ST_MvpEncode(const unsigned char *data,int size,char *out,int cap) {
    unsigned int bits=0; int held=0,i,n=0;
    if(size<0 || size>(cap-1)*3/4) return -1;
    for(i=0;i<size;++i) {
        bits=(bits<<8)|data[i]; held+=8;
        while(held>=6) { held-=6; if(n>=cap-1) return -1; out[n++]=stMvpAlphabet[(bits>>held)&63]; }
    }
    if(held) { if(n>=cap-1)return -1; out[n++]=stMvpAlphabet[(bits<<(6-held))&63]; }
    out[n]=0; return n;
}
static int ST_MvpDecode(const char *text,unsigned char *out,int cap) {
    unsigned int bits=0; int held=0,n=0,i;
    for(i=0;text[i];++i) {
        const char *p=strchr(stMvpAlphabet,text[i]);
        if(!p) return -1;
        bits=(bits<<6)|(unsigned int)(p-stMvpAlphabet); held+=6;
        if(held>=8) { held-=8; if(n>=cap)return -1; out[n++]=(unsigned char)(bits>>held); }
    }
    if(held>=6 || (held && (bits&((1u<<held)-1u)))) return -1;
    return n;
}
#endif
