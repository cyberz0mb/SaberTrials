/* Saber Trials shared ready-pose preferences. No attack/damage policy lives here. */
#ifndef ST_STANCE_POLICY_H
#define ST_STANCE_POLICY_H
#define ST_STANCE_SLOTS 12
#define ST_STANCE_WORDS 3
#define ST_STANCE_VERSION "1"
#define ST_STANCE_ACTIVE_MARKER 0x5311
/* Single B/Y/R/G/P/O, dual B/Y/R, staff B/Y/R. Only current styles activate. */
static int ST_StanceAllowed(int slot,int id) {
    if(slot<0 || slot>=ST_STANCE_SLOTS || id<0 || id>14)return 0;
    if(!id)return 1;
    if(slot<6)return id>=1 && id<=10;
    if(slot<9)return id==11 || id==12;
    return id==13 || id==14;
}
static int ST_StanceParse(const char* text,int out[ST_STANCE_SLOTS]) {
    int i, v, length=0;
    for(i=0;i<ST_STANCE_SLOTS;i++)out[i]=0;
    if(!text)return 0;
    while(length<=ST_STANCE_SLOTS && text[length])length++;
    if(length!=ST_STANCE_SLOTS)return 0;
    for(i=0;i<ST_STANCE_SLOTS;i++) {
        char c=text[i];
        if(c>='0' && c<='9')v=c-'0';
        else if(c>='a' && c<='f')v=c-'a'+10;
        else if(c>='A' && c<='F')v=c-'A'+10;
        else {int j;for(j=0;j<ST_STANCE_SLOTS;j++)out[j]=0;return 0;}
        out[i]=ST_StanceAllowed(i,v)?v:0;
    }
    return 1;
}
static void ST_StanceFormat(const int in[ST_STANCE_SLOTS],char out[ST_STANCE_SLOTS+1]) {
    int i;for(i=0;i<ST_STANCE_SLOTS;i++)out[i]="0123456789abcdef"[ST_StanceAllowed(i,in[i])?in[i]:0];
    out[ST_STANCE_SLOTS]=0;
}
static void ST_StancePack(const int in[ST_STANCE_SLOTS],int words[ST_STANCE_WORDS]) {
    int i;for(i=0;i<ST_STANCE_WORDS;i++)words[i]=0;
    for(i=0;i<ST_STANCE_SLOTS;i++)if(ST_StanceAllowed(i,in[i]))words[i/4]|=in[i]<<((i%4)*4);
}
static void ST_StanceUnpack(const int words[ST_STANCE_WORDS],int out[ST_STANCE_SLOTS]) {
    int i;for(i=0;i<ST_STANCE_SLOTS;i++) {
        int id=((unsigned int)words[i/4]>>((i%4)*4))&15;
        out[i]=ST_StanceAllowed(i,id)?id:0;
    }
}
static int ST_StanceChoice(const int words[ST_STANCE_WORDS],int slot,int libraryOK) {
    int id;
    if(!libraryOK || slot<0 || slot>=ST_STANCE_SLOTS)return 0;
    id=((unsigned int)words[slot/4]>>((slot%4)*4))&15;
    return ST_StanceAllowed(slot,id)?id:0;
}
#endif
