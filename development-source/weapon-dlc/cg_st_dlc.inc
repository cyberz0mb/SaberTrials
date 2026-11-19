/* Included by cg_weapons.c. One media instance per additive gun. */
#include "game/st_dlc_weapons.h"
typedef struct {
    qboolean loaded;
    weaponInfo_t info;
    void *world;
    fxHandle_t shot[2],impact[2];
} stDlcMedia_t;
static stDlcMedia_t st_dlcMedia[ST_DLC_MAX+1];
static int st_dlcSelect;
static int st_dlcSpawn;
static qboolean CG_WeaponSelectable(int weapon);
extern int ST_HudSelectLift(void);

static void ST_DLCTrail(centity_t *cent,const weaponInfo_t *unused) {
    int id=ST_DLCEntityId(&cent->currentState),alt=(cent->currentState.eFlags&EF_ALT_FIRING)!=0;
    vec3_t direction;
    (void)unused;
    if(!id || !st_dlcMedia[id].shot[alt]) return;
    if(!VectorNormalize2(cent->currentState.pos.trDelta,direction)) VectorSet(direction,0,0,1);
    trap->FX_PlayEffectID(st_dlcMedia[id].shot[alt],cent->lerpOrigin,direction,-1,-1,qfalse);
}

weaponInfo_t *ST_DLCWeaponInfo(int id,int base) {
    stDlcMedia_t *m;
    stDlcWeapon_t *w;
    int i,handle;
    if(base<0 || base>=WP_NUM_WEAPONS) base=WP_NONE;
    CG_RegisterWeapon(base);
    if(!id || ST_DLCBase(id)!=base || !st_dlcWeapons[id].available) return &cg_weapons[base];
    w=&st_dlcWeapons[id]; m=&st_dlcMedia[id];
    if(m->loaded) return &m->info;
    m->loaded=qtrue;
    m->info=cg_weapons[base];
    handle=trap->R_RegisterModel(w->asset[ST_DLC_VIEW]);
    if(handle) { m->info.viewModel=handle; m->info.barrelModel=0; }
    trap->G2API_InitGhoul2Model(&m->world,w->asset[ST_DLC_WORLD],0,0,0,0,0);
    if(!handle || !m->world) {
        Com_Printf("Saber Trials DLC: %s has missing models; stock visuals used.\n",w->id);
        w->available=qfalse;
        return &cg_weapons[base];
    }
    trap->G2API_SetBoltInfo(m->world,0,0);
    trap->G2API_AddBolt(m->world,0,"*flash");
    if(w->asset[ST_DLC_HANDS][0] && (handle=trap->R_RegisterModel(w->asset[ST_DLC_HANDS]))) m->info.handsModel=handle;
    if(w->asset[ST_DLC_ICON][0] && (handle=trap->R_RegisterShaderNoMip(w->asset[ST_DLC_ICON]))) m->info.weaponIcon=handle;
    for(i=0;i<2;++i) {
        if(w->asset[ST_DLC_MUZZLE+i][0] && (handle=trap->FX_RegisterEffect(w->asset[ST_DLC_MUZZLE+i]))) {
            if(i) m->info.altMuzzleEffect=handle; else m->info.muzzleEffect=handle;
        }
        if(w->asset[ST_DLC_FIRE_SOUND+i][0] && (handle=trap->S_RegisterSound(w->asset[ST_DLC_FIRE_SOUND+i]))) {
            int *sounds=i ? m->info.altFlashSound : m->info.flashSound;
            memset(sounds,0,sizeof(m->info.flashSound)); sounds[0]=handle;
        }
        if(w->asset[ST_DLC_SHOT+i][0]) m->shot[i]=trap->FX_RegisterEffect(w->asset[ST_DLC_SHOT+i]);
        if(w->asset[ST_DLC_IMPACT+i][0]) m->impact[i]=trap->FX_RegisterEffect(w->asset[ST_DLC_IMPACT+i]);
        if(m->shot[i]) {
            if(i) { m->info.altMissileTrailFunc=ST_DLCTrail; m->info.altMissileModel=0; }
            else { m->info.missileTrailFunc=ST_DLCTrail; m->info.missileModel=0; }
        }
        if(w->asset[ST_DLC_PROJECTILE+i][0] && (handle=trap->R_RegisterModel(w->asset[ST_DLC_PROJECTILE+i]))) {
            if(i) m->info.altMissileModel=handle; else m->info.missileModel=handle;
        }
    }
    return &m->info;
}

void ST_DLCCleanup(void) {
    int i;
    for(i=1;i<=ST_DLC_MAX;++i) if(st_dlcMedia[i].world) trap->G2API_CleanGhoul2Models(&st_dlcMedia[i].world);
    memset(st_dlcMedia,0,sizeof(st_dlcMedia));
    st_dlcSelect=0;
}
void ST_DLCClientInit(void) {
    int i;
    ST_DLCCleanup();
    for(i=0;i<MAX_GENTITIES;++i) cg_entities[i].ghoul2weapon=NULL;
    ST_DLCLoad();
    ST_DLCMatchManifest(CG_ConfigString(ST_DLC_CONFIGSTRING));
    st_dlcSpawn=-1;
}

static int ST_DLCPlayerId(centity_t *cent) {
    if(cent->currentState.number==cg.predictedPlayerState.clientNum && !cg.demoPlayback &&
       !(cg.predictedPlayerState.pm_flags&PMF_FOLLOW))
        return cg.predictedPlayerState.stats[ST_DLC_STAT];
    return ST_DLCEntityId(&cent->currentState);
}
static void *ST_DLCWorld(centity_t *cent,int base) {
    int id=ST_DLCPlayerId(cent);
    if(!id || ST_DLCBase(id)!=base) return NULL;
    ST_DLCWeaponInfo(id,base);
    return st_dlcWeapons[id].available ? st_dlcMedia[id].world : NULL;
}

qboolean ST_DLCImpact(const entityState_t *state,vec3_t origin,vec3_t dir) {
    int id=ST_DLCEntityId(state),alt=(state->eFlags&EF_ALT_FIRING)!=0;
    if(!id) return qfalse;
    ST_DLCWeaponInfo(id,state->weapon);
    if(!st_dlcWeapons[id].available || !st_dlcMedia[id].impact[alt]) return qfalse;
    trap->FX_PlayEffectID(st_dlcMedia[id].impact[alt],origin,dir,-1,-1,qfalse);
    return qtrue;
}

qboolean ST_DLCHitscanImpact(const entityState_t *state,int base,vec3_t origin,vec3_t dir) {
    entityState_t copy=*state;
    copy.weapon=base;
    return ST_DLCImpact(&copy,origin,dir);
}
qboolean ST_DLCBeam(const entityState_t *state,int base,int alt,vec3_t start,vec3_t end) {
    entityState_t copy=*state;
    int id,step,steps;
    float length;
    vec3_t dir,point;
    copy.weapon=base;
    id=ST_DLCEntityId(&copy);
    if(!id) return qfalse;
    ST_DLCWeaponInfo(id,base);
    if(!st_dlcWeapons[id].available || !st_dlcMedia[id].shot[alt]) return qfalse;
    VectorSubtract(end,start,dir);
    length=VectorNormalize(dir);
    steps=(int)(length/64)+1;
    if(steps>128) steps=128;
    for(step=0;step<steps;++step) {
        VectorMA(start,length*step/steps,dir,point);
        trap->FX_PlayEffectID(st_dlcMedia[id].shot[alt],point,dir,-1,-1,qfalse);
    }
    return qtrue;
}

int ST_DLCCommandWeapon(int base) {
    if(cg.snap && st_dlcSpawn!=cg.snap->ps.persistant[PERS_SPAWN_COUNT]) {
        st_dlcSpawn=cg.snap->ps.persistant[PERS_SPAWN_COUNT];
        st_dlcSelect=0;
    }
    if(ST_DLCBase(st_dlcSelect)!=base || !ST_DLCAllowed(&cg.predictedPlayerState,st_dlcSelect)) st_dlcSelect=0;
    return st_dlcSelect ? ST_DLC_COMMAND+st_dlcSelect : base;
}

typedef struct { int base,id; } stDlcChoice_t;
static int ST_DLCChoices(stDlcChoice_t *choices) {
    static const int order[]={ WP_STUN_BATON,WP_MELEE,WP_SABER,WP_BRYAR_PISTOL,WP_BLASTER,
        WP_DISRUPTOR,WP_BOWCASTER,WP_REPEATER,WP_DEMP2,WP_FLECHETTE,WP_CONCUSSION,
        WP_ROCKET_LAUNCHER,WP_THERMAL,WP_TRIP_MINE,WP_DET_PACK,WP_BRYAR_OLD };
    int i,j,n=0;
    for(i=0;i<ARRAY_LEN(order);++i) {
        if(CG_WeaponSelectable(order[i])) { choices[n].base=order[i]; choices[n++].id=0; }
        for(j=1;j<=st_dlcCount;++j) if(ST_DLCBase(j)==order[i] && st_dlcWeapons[j].available &&
            ST_DLCAllowed(&cg.predictedPlayerState,j)) {
            choices[n].base=order[i]; choices[n++].id=j;
        }
    }
    return n;
}

static qboolean ST_DLCCycle(int direction) {
    stDlcChoice_t choices[WP_NUM_WEAPONS+ST_DLC_MAX];
    int count,i,index=-1;
    if(!st_dlcCount) return qfalse;
    if(!cg.snap || (cg.snap->ps.pm_flags&PMF_FOLLOW) || cg.predictedPlayerState.pm_type!=PM_NORMAL ||
       cg.predictedPlayerState.stats[STAT_HEALTH]<=0 || cg.snap->ps.emplacedIndex || cg.predictedPlayerState.m_iVehicleNum) return qtrue;
    ST_DLCCommandWeapon(cg.weaponSelect);
    count=ST_DLCChoices(choices);
    for(i=0;i<count;++i) if(choices[i].base==cg.weaponSelect && choices[i].id==st_dlcSelect) index=i;
    if(!count) return qtrue;
    if(index<0) index=direction>0 ? count-1 : 0;
    index=(index+count+direction)%count;
    st_dlcSelect=choices[index].id;
    cg.weaponSelect=choices[index].base;
    cg.weaponSelectTime=cg.time;
    trap->S_MuteSound(cg.snap->ps.clientNum,CHAN_WEAPON);
    return qtrue;
}

static qboolean ST_DLCCarousel(void) {
    stDlcChoice_t choices[WP_NUM_WEAPONS+ST_DLC_MAX];
    int count,i,index=-1,offset,shown;
    float y=410-ST_HudSelectLift();
    vec4_t color={.875f,.718f,.121f,1};
    if(!st_dlcCount) return qfalse;
    if(!cg.snap || cg.predictedPlayerState.stats[STAT_HEALTH]<=0 ||
       cg.predictedPlayerState.emplacedIndex || cg.time>cg.weaponSelectTime+WEAPON_SELECT_TIME) return qtrue;
    count=ST_DLCChoices(choices);
    for(i=0;i<count;++i) if(choices[i].base==cg.weaponSelect && choices[i].id==st_dlcSelect) index=i;
    if(index<0) return qfalse;
    shown=count<7 ? count : 7;
    for(i=0;i<shown;++i) {
        int slot=(index+count+i-shown/2)%count;
        weaponInfo_t *info=ST_DLCWeaponInfo(choices[slot].id,choices[slot].base);
        float size=slot==index ? 44 : 28;
        offset=i-shown/2;
        CG_DrawPic(320+offset*46-size/2,y-size/2,size,size,info->weaponIcon);
    }
    if(st_dlcSelect) CG_DrawProportionalString(320,y+30,st_dlcWeapons[st_dlcSelect].name,UI_CENTER|UI_SMALLFONT,color);
    else if(cg_weapons[cg.weaponSelect].item) {
        char key[128],name[128];
        Q_strncpyz(key,cg_weapons[cg.weaponSelect].item->classname,sizeof(key));
        if(!trap->SE_GetStringTextString(va("SP_INGAME_%s",Q_strupr(key)),name,sizeof(name)))
            Q_strncpyz(name,cg_weapons[cg.weaponSelect].item->classname,sizeof(name));
        CG_DrawProportionalString(320,y+30,name,UI_CENTER|UI_SMALLFONT,color);
    }
    trap->R_SetColor(NULL);
    return qtrue;
}

/* Read-only author diagnostic. Values come from the authoritative snapshot. */
void ST_DLCInspect(void) {
    int i,id,base;
    if(!cg.snap) { Com_Printf("Weapon DLC: join a match first.\n"); return; }
    id=cg.snap->ps.stats[ST_DLC_STAT]; base=cg.snap->ps.weapon;
    if(!ST_DLCBase(id)) id=0;
    ST_DLCWeaponInfo(id,base);
    Com_Printf("ST_DLC_STATE base=%d id=%d name=%s ammo=%d inventory=%d allowed=%d predicted=%d selected=%d models=%d/%d fx=%d/%d/%d/%d\n",
        base,id,id ? st_dlcWeapons[id].id : "stock",
        cg.snap->ps.ammo[weaponData[base].ammoIndex],cg.snap->ps.stats[STAT_WEAPONS],
        cg.snap->ps.stats[ST_DLC_ALLOWED_STAT],cg.predictedPlayerState.stats[ST_DLC_STAT],st_dlcSelect,
        id && st_dlcMedia[id].world!=NULL,id && st_dlcMedia[id].info.viewModel!=0,
        id && st_dlcMedia[id].shot[0]!=0,id && st_dlcMedia[id].shot[1]!=0,
        id && st_dlcMedia[id].impact[0]!=0,id && st_dlcMedia[id].impact[1]!=0);
    for(i=1;i<=st_dlcCount;++i) Com_Printf("ST_DLC_ENTRY %d %s base=%d installed=%d selectable=%d\n",i,
        st_dlcWeapons[i].id,st_dlcWeapons[i].base,st_dlcWeapons[i].available,ST_DLCAllowed(&cg.snap->ps,i));
    for(i=0;i<MAX_CLIENTS;++i) if((cg_entities[i].currentValid || i==cg.predictedPlayerState.clientNum) && cg_entities[i].currentState.eType==ET_PLAYER) {
        centity_t *cent=&cg_entities[i];
        int other=ST_DLCEntityId(&cent->currentState);
        void *world=other ? ST_DLCWorld(cent,cent->currentState.weapon) : NULL;
        Com_Printf("ST_DLC_REMOTE client=%d base=%d id=%d installed=%d attached=%d\n",i,
            cent->currentState.weapon,other,other && st_dlcWeapons[other].available,
            world && cent->ghoul2weapon==world);
    }
}
