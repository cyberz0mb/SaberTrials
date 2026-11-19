/* Resolved-file compatibility check; not a cryptographic trust claim. */
#ifndef ST_STANCE_ASSETS_H
#define ST_STANCE_ASSETS_H
static int ST_StanceAssetsCheck(void) {
    fileHandle_t file=0;
    unsigned char buffer[8192];
    unsigned int hash=2166136261U;
    int remaining=trap->FS_Open("models/players/_humanoid/_humanoid.gla",&file,FS_READ),count,i;
    if(!file)return 0;
    if(remaining!=12201009) {trap->FS_Close(file);return 0;}
    while(remaining>0) {
        count=remaining>(int)sizeof(buffer)?(int)sizeof(buffer):remaining;
        trap->FS_Read(buffer,count,file);
        for(i=0;i<count;i++)hash=(hash^buffer[i])*16777619U;
        remaining-=count;
    }
    trap->FS_Close(file);
    return hash==1847057037U;
}
static int ST_StanceAssetsAvailable(void) {
    static int available=-1;
    if(available<0)available=ST_StanceAssetsCheck();
    return available;
}
#endif
