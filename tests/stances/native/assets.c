/* Exercise production file validation with the actual GLA and a mocked VFS. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int fileHandle_t;
#define FS_READ 0
static unsigned char* data;
static int length, position, absent, reported;
static int fs_open(const char* name,fileHandle_t* f,int mode) {
    (void)name;(void)mode;position=0;*f=absent?0:1;return absent?-1:reported;
}
static void fs_read(void* b,int n,fileHandle_t f) {
    (void)f;memcpy(b,data+position,n);position+=n;
}
static void fs_close(fileHandle_t f) {(void)f;}
static struct {int(*FS_Open)(const char*,fileHandle_t*,int);void(*FS_Read)(void*,int,fileHandle_t);void(*FS_Close)(fileHandle_t);} api={fs_open,fs_read,fs_close},*trap=&api;
#include "st_stance_assets.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char** argv) {
    FILE* f;
    CHECK(argc==2);f=fopen(argv[1],"rb");CHECK(f);
    fseek(f,0,SEEK_END);length=(int)ftell(f);rewind(f);
    data=(unsigned char*)malloc(length);CHECK(data);CHECK(fread(data,1,length,f)==length);fclose(f);
    reported=length;CHECK(ST_StanceAssetsCheck());
    absent=1;CHECK(!ST_StanceAssetsCheck());absent=0;
    reported=length-100;CHECK(!ST_StanceAssetsCheck());reported=length;
    data[length-1]^=1;CHECK(!ST_StanceAssetsCheck());data[length-1]^=1;
    /* Same size, old frame count: matching config must not enable an older GLA. */
    data[76]^=1;CHECK(!ST_StanceAssetsCheck());data[76]^=1;
    CHECK(ST_StanceAssetsCheck());free(data);
    puts("PASS: actual resolved GLA identity; absent, truncated and same-size corrupt libraries rejected");return 0;
}
