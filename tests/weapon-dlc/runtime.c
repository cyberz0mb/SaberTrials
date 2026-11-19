#include "qcommon/q_shared.h"
#include "game/bg_public.h"
#include <assert.h>

static char fixture[64][8192];
static int fixtureCount;
static int files(const char *folder,const char *extension,char *buffer,int size) {
    int i,used=0;
    (void)folder;(void)extension;
    for(i=0;i<fixtureCount;++i) {
        int n=snprintf(buffer+used,size-used,"%02d.weapon",i)+1;
        used+=n;
    }
    return fixtureCount;
}
static int openFile(const char *path,fileHandle_t *handle,fsMode_t mode) {
    const char *name=strrchr(path,'/');
    int i=atoi(name+1);
    (void)mode;
    *handle=i+1;
    return (int)strlen(fixture[i]);
}
static void readFile(void *buffer,int length,fileHandle_t handle) { memcpy(buffer,fixture[handle-1],length); }
static void closeFile(fileHandle_t handle) { (void)handle; }
static struct {
    int (*FS_GetFileList)(const char*,const char*,char*,int);
    int (*FS_Open)(const char*,fileHandle_t*,fsMode_t);
    void (*FS_Read)(void*,int,fileHandle_t);
    void (*FS_Close)(fileHandle_t);
} fakeTrap={files,openFile,readFile,closeFile}, *trap=&fakeTrap;
void QDECL Com_Printf(const char *format,...) { (void)format; }
NORETURN void QDECL Com_Error(int code,const char *format,...) { (void)code;(void)format;abort(); }
#define ST_DLC_TEST
#include "bg_st_dlc.inc"

static const char *families[]={"bryar","blaster","disruptor","bowcaster","repeater","demp2","flechette","rocket","concussion","bryar_old"};
static int baseIds[]={4,5,6,7,8,9,10,11,15,16};
static int pmCalls,pmCommand,pmInventory,pmAmmo;
void PmoveSingle(pmove_t *move) {
    int ammo=weaponData[move->cmd.weapon].ammoIndex;
    ++pmCalls;pmCommand=move->cmd.weapon;pmInventory=move->ps->stats[STAT_WEAPONS];
    pmAmmo=move->ps->ammo[ammo];
    if(pmAmmo>0) --move->ps->ammo[ammo];
    /* Model an unrelated stock inventory mutation; the wrapper must preserve it. */
    move->ps->stats[STAT_WEAPONS]&=~(1<<WP_THERMAL);
}
static void definition(char *dest,const char *id,const char *base) {
    sprintf(dest,"weapon { version 1 id %s name \"Test gun\" baseWeapon %s "
        "viewModel models/test/view.md3 worldModel models/test/world.glm }",id,base);
}
static void parser(void) {
    stDlcWeapon_t a,b;
    char text[8192],bad[8192];
    int i;
    for(i=0;i<ARRAY_LEN(families);++i) {
        definition(text,"author_gun",families[i]);
        assert(ST_DLCParse(text,&a));assert(a.base==baseIds[i]);
        sprintf(bad,"// comment\n%s // comment\n",text);
        assert(ST_DLCParse(bad,&b));assert(a.checksum==b.checksum);
    }
    definition(text,"author_gun","blaster");
    sprintf(bad,"%s trailing",text);assert(!ST_DLCParse(bad,&a));
    definition(bad,"../bad","blaster");assert(!ST_DLCParse(bad,&a));
    definition(bad,"UpperCase","blaster");assert(!ST_DLCParse(bad,&a));
    definition(bad,"okay","saber");assert(!ST_DLCParse(bad,&a));
    strcpy(bad,"weapon { version 2 id okay }");assert(!ST_DLCParse(bad,&a));
    strcpy(bad,"weapon { version 1 id okay name Test baseWeapon blaster }");assert(!ST_DLCParse(bad,&a));
    definition(bad,"okay","rocket");strcpy(strrchr(bad,'}'),"damage 999 }");assert(!ST_DLCParse(bad,&a));
    definition(bad,"okay","rocket");strcpy(strrchr(bad,'}'),"version 1 }");assert(!ST_DLCParse(bad,&a));
    definition(bad,"okay","rocket");strcpy(strrchr(bad,'}'),"shotEffect ../bad }");assert(!ST_DLCParse(bad,&a));
}
static void manifest(void) {
    char first[4096],second[4096],temp[8192];
    fixtureCount=3;
    definition(fixture[0],"zeta","blaster");definition(fixture[1],"alpha","rocket");definition(fixture[2],"middle","bryar");
    ST_DLCLoad();assert(st_dlcCount==3);ST_DLCManifest(first,sizeof(first));
    strcpy(temp,fixture[0]);strcpy(fixture[0],fixture[2]);strcpy(fixture[2],temp);
    ST_DLCLoad();ST_DLCManifest(second,sizeof(second));assert(!strcmp(first,second));
    fixtureCount=2;ST_DLCLoad();assert(ST_DLCMatchManifest(first));
    assert(st_dlcCount==3 && st_dlcWeapons[1].available && st_dlcWeapons[2].available && !st_dlcWeapons[3].available);
    assert(ST_DLCBase(3)==WP_BLASTER);
    strcpy(fixture[1],fixture[0]);ST_DLCLoad();assert(st_dlcCount==0);
    fixtureCount=63;
    for(int i=0;i<63;++i) definition(fixture[i],va("author_weapon_%02d",i),"blaster");
    ST_DLCLoad();assert(st_dlcCount==63);ST_DLCManifest(first,sizeof(first));
    assert(ST_DLCMatchManifest(first) && st_dlcCount==63);
    assert(!ST_DLCMatchManifest("1 bad 500 12345678"));assert(!st_dlcCount);
    assert(!ST_DLCMatchManifest("1 bad 5 garbage"));assert(!st_dlcCount);
    assert(!ST_DLCMatchManifest(""));assert(!st_dlcCount);
}
static void movement(void) {
    playerState_t ps;
    pmove_t move;
    entityState_t entity;
    fixtureCount=1;definition(fixture[0],"test_gun","blaster");ST_DLCLoad();
    memset(&ps,0,sizeof(ps));memset(&move,0,sizeof(move));memset(&entity,0,sizeof(entity));
    move.ps=&ps;move.cmd.weapon=ST_DLC_COMMAND+1;
    ps.weapon=WP_BLASTER;ps.weaponstate=WEAPON_READY;ps.pm_type=PM_NORMAL;
    ps.stats[STAT_HEALTH]=100;ps.stats[ST_DLC_ALLOWED_STAT]=1<<WP_BLASTER;
    ps.stats[STAT_WEAPONS]=(1<<WP_SABER)|(1<<WP_THERMAL);
    ps.ammo[AMMO_BLASTER]=20;
    assert(ST_DLCAllowed(&ps,1));assert(!ST_DLCAllowed(&ps,0));assert(!ST_DLCAllowed(&ps,64));
    ST_DLCPmove(&move);
    assert(pmCalls==1 && pmCommand==WP_BLASTER && (pmInventory&(1<<WP_BLASTER)));
    assert(ps.stats[STAT_WEAPONS]==(1<<WP_SABER));assert(ps.stats[ST_DLC_STAT]==1);
    assert(ps.ammo[AMMO_BLASTER]==19 && move.cmd.weapon==ST_DLC_COMMAND+1);
    ps.stats[ST_DLC_ALLOWED_STAT]|=ST_DLC_INFINITE;
    ST_DLCPmove(&move);assert(pmAmmo==ammoData[AMMO_BLASTER].max && ps.ammo[AMMO_BLASTER]==19);
    ps.weaponTime=100;move.cmd.weapon=WP_BLASTER;ST_DLCPmove(&move);assert(ps.stats[ST_DLC_STAT]==1);
    ps.weaponTime=0;ST_DLCPmove(&move);assert(ps.stats[ST_DLC_STAT]==0);
    /* Unlimited gun ammo must not restore explosives consumed by stock movement. */
    ps.weapon=WP_THERMAL;move.cmd.weapon=WP_THERMAL;ps.ammo[AMMO_THERMAL]=5;
    ST_DLCPmove(&move);assert(pmAmmo==5 && ps.ammo[AMMO_THERMAL]==4);
    ps.duelInProgress=qtrue;assert(!ST_DLCAllowed(&ps,1));
    ps.duelInProgress=qfalse;ps.m_iVehicleNum=1;assert(!ST_DLCAllowed(&ps,1));
    ps.m_iVehicleNum=0;ps.pm_type=PM_SPECTATOR;assert(!ST_DLCAllowed(&ps,1));
    entity.weapon=WP_BLASTER;entity.time2=(1<<ST_DLC_ENTITY_SHIFT)|((1<<18)-1);
    assert(ST_DLCEntityId(&entity)==1 && (entity.time2&((1<<18)-1))==((1<<18)-1));
    entity.weapon=WP_ROCKET_LAUNCHER;assert(!ST_DLCEntityId(&entity));
}
int main(void) { parser();manifest();movement();puts("Weapon DLC parser, catalogue and movement contracts passed.");return 0; }
