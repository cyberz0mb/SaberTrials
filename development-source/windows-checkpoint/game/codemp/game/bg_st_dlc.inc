/* Included by bg_misc.c, shared by server and prediction. */
#include "st_dlc_weapons.h"

stDlcWeapon_t st_dlcWeapons[ST_DLC_MAX+1];
int st_dlcCount;

static const char *st_dlcKeys[ST_DLC_ASSET_COUNT] = {
    "viewModel", "worldModel", "icon", "handsModel",
    "muzzleEffect", "altMuzzleEffect", "shotEffect", "altShotEffect",
    "impactEffect", "altImpactEffect", "fireSound", "altFireSound",
    "projectileModel", "altProjectileModel"
};

static int ST_DLCBaseName(const char *name) {
    static const struct { const char *name; int base; } families[] = {
        {"bryar",WP_BRYAR_PISTOL}, {"blaster",WP_BLASTER},
        {"disruptor",WP_DISRUPTOR}, {"bowcaster",WP_BOWCASTER},
        {"repeater",WP_REPEATER}, {"demp2",WP_DEMP2},
        {"flechette",WP_FLECHETTE}, {"rocket",WP_ROCKET_LAUNCHER},
        {"concussion",WP_CONCUSSION}, {"bryar_old",WP_BRYAR_OLD}
    };
    int i;
    for(i=0;i<ARRAY_LEN(families);++i)
        if(!strcmp(name,families[i].name)) return families[i].base;
    return 0;
}

static qboolean ST_DLCSafe(const char *s, qboolean path) {
    const char *p;
    if(!s[0] || strstr(s,"..") || s[0]=='/') return qfalse;
    for(p=s;*p;++p)
        if(!((*p>='a'&&*p<='z') || (*p>='0'&&*p<='9') || *p=='_' || *p=='-' ||
             (path && (*p=='/' || *p=='.')))) return qfalse;
    return qtrue;
}

qboolean ST_DLCParse(char *text, stDlcWeapon_t *w) {
    char *cursor=text, key[64], value[MAX_TOKEN_CHARS];
    unsigned seen=0, hash=2166136261u;
    const unsigned char *bytes;
    int i, field, version=0;
    memset(w,0,sizeof(*w));
    if(strcmp(COM_ParseExt(&cursor,qtrue),"weapon")) return qfalse;
    if(strcmp(COM_ParseExt(&cursor,qtrue),"{")) return qfalse;
    for(;;) {
        Q_strncpyz(key,COM_ParseExt(&cursor,qtrue),sizeof(key));
        if(!key[0]) return qfalse;
        if(!strcmp(key,"}")) break;
        Q_strncpyz(value,COM_ParseExt(&cursor,qtrue),sizeof(value));
        if(!value[0] || !strcmp(value,"}")) return qfalse;
        field=-1;
        if(!strcmp(key,"version")) { field=0; version=!strcmp(value,"1"); }
        else if(!strcmp(key,"id")) {
            field=1;
            if(strlen(value)>=sizeof(w->id) || !ST_DLCSafe(value,qfalse)) return qfalse;
            Q_strncpyz(w->id,value,sizeof(w->id));
        } else if(!strcmp(key,"name")) {
            field=2;
            if(strlen(value)>=sizeof(w->name)) return qfalse;
            for(i=0;value[i];++i) if((unsigned char)value[i]<32 || value[i]=='^') return qfalse;
            Q_strncpyz(w->name,value,sizeof(w->name));
        } else if(!strcmp(key,"baseWeapon")) { field=3; w->base=ST_DLCBaseName(value); }
        else for(i=0;i<ST_DLC_ASSET_COUNT;++i) if(!strcmp(key,st_dlcKeys[i])) {
            field=4+i;
            if(strlen(value)>=MAX_QPATH || !ST_DLCSafe(value,qtrue)) return qfalse;
            Q_strncpyz(w->asset[i],value,MAX_QPATH);
            break;
        }
        if(field<0 || (seen & (1u<<field))) return qfalse;
        seen|=1u<<field;
    }
    if(COM_ParseExt(&cursor,qtrue)[0] || !version || !w->id[0] || !w->name[0] || !w->base ||
       !w->asset[ST_DLC_VIEW][0] || !w->asset[ST_DLC_WORLD][0]) return qfalse;
    /* Hash canonical, zero-filled data, not comments/whitespace or file order. */
    bytes=(const unsigned char*)w->id;
    for(i=0;i<sizeof(w->id)+sizeof(w->name);++i) hash=(hash^bytes[i])*16777619u;
    hash=(hash^(unsigned)w->base)*16777619u;
    bytes=(const unsigned char*)w->asset;
    for(i=0;i<sizeof(w->asset);++i) hash=(hash^bytes[i])*16777619u;
    w->checksum=hash;
    w->available=qtrue;
    return qtrue;
}

static int QDECL ST_DLCCompare(const void *a,const void *b) {
    return strcmp(((const stDlcWeapon_t*)a)->id,((const stDlcWeapon_t*)b)->id);
}

void ST_DLCLoad(void) {
    char files[8192], text[8192], *file;
    fileHandle_t handle;
    int count, i, j, length, n=0;
    static stDlcWeapon_t found[ST_DLC_MAX+1];
    memset(st_dlcWeapons,0,sizeof(st_dlcWeapons));
    st_dlcCount=0;
    count=trap->FS_GetFileList("ext_data/st_weapons",".weapon",files,sizeof(files));
    if(count>ST_DLC_MAX) {
        Com_Printf("Saber Trials DLC: more than %d definitions; catalogue disabled.\n",ST_DLC_MAX);
        return;
    }
    for(i=0,file=files;i<count;++i,file+=strlen(file)+1) {
        length=trap->FS_Open(va("ext_data/st_weapons/%s",file),&handle,FS_READ);
        if(!handle) continue;
        if(length<=0 || length>=sizeof(text)) { trap->FS_Close(handle); continue; }
        trap->FS_Read(text,length,handle);
        trap->FS_Close(handle);
        text[length]=0;
        if(ST_DLCParse(text,&found[n])) ++n;
        else Com_Printf("Saber Trials DLC: invalid definition %s; skipped.\n",file);
    }
    qsort(found,n,sizeof(found[0]),ST_DLCCompare);
    for(i=0;i<n;i=j) {
        for(j=i+1;j<n && !strcmp(found[i].id,found[j].id);++j) {}
        if(j!=i+1) {
            Com_Printf("Saber Trials DLC: duplicate id %s; all copies skipped.\n",found[i].id);
            continue;
        }
        st_dlcWeapons[++st_dlcCount]=found[i];
    }
    Com_Printf("Saber Trials DLC: loaded %d additive guns.\n",st_dlcCount);
}

void ST_DLCManifest(char *text,int size) {
    int i;
    Q_strncpyz(text,"1",size);
    for(i=1;i<=st_dlcCount;++i)
        Q_strcat(text,size,va(" %s %d %08x",st_dlcWeapons[i].id,st_dlcWeapons[i].base,st_dlcWeapons[i].checksum));
}

qboolean ST_DLCMatchManifest(const char *text) {
    static stDlcWeapon_t local[ST_DLC_MAX+1];
    char buffer[ST_DLC_MANIFEST_SIZE],*cursor=buffer,id[32],*token,*end;
    int count=st_dlcCount,i,base;
    unsigned hash;
    memcpy(local,st_dlcWeapons,sizeof(local));
    memset(st_dlcWeapons,0,sizeof(st_dlcWeapons));
    st_dlcCount=0;
    if(strlen(text)>=sizeof(buffer)) return qfalse;
    Q_strncpyz(buffer,text,sizeof(buffer));
    if(strcmp(COM_ParseExt(&cursor,qtrue),"1")) return qfalse;
    while((token=COM_ParseExt(&cursor,qtrue))[0]) {
        if(st_dlcCount==ST_DLC_MAX || strlen(token)>=sizeof(id) || !ST_DLCSafe(token,qfalse)) goto invalid;
        Q_strncpyz(id,token,sizeof(id));
        token=COM_ParseExt(&cursor,qtrue);
        base=(int)strtol(token,&end,10);
        if(!token[0] || *end || !((base>=WP_BRYAR_PISTOL && base<=WP_ROCKET_LAUNCHER) || base==WP_CONCUSSION || base==WP_BRYAR_OLD)) goto invalid;
        token=COM_ParseExt(&cursor,qtrue);
        hash=(unsigned)strtoul(token,&end,16);
        if(strlen(token)!=8 || *end) goto invalid;
        ++st_dlcCount;
        for(i=1;i<=count;++i) if(!strcmp(local[i].id,id) && local[i].base==base && local[i].checksum==hash) {
            st_dlcWeapons[st_dlcCount]=local[i];
            break;
        }
        if(i>count) {
            Q_strncpyz(st_dlcWeapons[st_dlcCount].id,id,sizeof(id));
            st_dlcWeapons[st_dlcCount].base=base;
            Com_Printf("Saber Trials DLC: %s missing or different; stock visuals used.\n",id);
        }
    }
    return qtrue;
invalid:
    memset(st_dlcWeapons,0,sizeof(st_dlcWeapons));
    st_dlcCount=0;
    return qfalse;
}

int ST_DLCBase(int id) {
    return id>0 && id<=st_dlcCount ? st_dlcWeapons[id].base : 0;
}
qboolean ST_DLCGun(int base) {
    return (base>=WP_BRYAR_PISTOL && base<=WP_ROCKET_LAUNCHER) ||
        base==WP_CONCUSSION || base==WP_BRYAR_OLD;
}
int ST_DLCAccessBit(int base) {
    /* Stats are signed 16-bit on the wire; the legacy pistol uses spare bit 2. */
    return base==WP_BRYAR_OLD ? 4 : 1<<base;
}
int ST_DLCEntityId(const entityState_t *state) {
    int id=((unsigned)state->time2>>ST_DLC_ENTITY_SHIFT)&ST_DLC_MAX;
    return ST_DLCBase(id)==state->weapon ? id : 0;
}
qboolean ST_DLCAllowed(const playerState_t *ps,int id) {
    int base=ST_DLCBase(id);
    return base && (ps->stats[ST_DLC_ALLOWED_STAT]&ST_DLCAccessBit(base)) &&
        ps->pm_type==PM_NORMAL && ps->stats[STAT_HEALTH]>0 &&
        !ps->duelInProgress && !ps->isJediMaster && !ps->trueJedi &&
        !ps->m_iVehicleNum && !ps->emplacedIndex;
}

/* The caller invokes this in place of PmoveSingle. Never enlarge the weapon enum
 * or inventory mask: virtual ownership is scoped to this movement step. */
#if defined(_GAME) || defined(_CGAME) || defined(ST_DLC_TEST)
void PmoveSingle(pmove_t *move);
void ST_DLCPmove(pmove_t *move) {
    playerState_t *ps=move->ps;
    int command=move->cmd.weapon, id=0, base=command;
    int inventory=ps->stats[STAT_WEAPONS], ammo[MAX_AMMO], i;
    qboolean infinite=(ps->stats[ST_DLC_ALLOWED_STAT]&ST_DLC_INFINITE)!=0;
    if(command>=ST_DLC_COMMAND) {
        id=command-ST_DLC_COMMAND;
        if(!ST_DLCAllowed(ps,id)) { id=ps->stats[ST_DLC_STAT]; base=ps->weapon; }
        else base=ST_DLCBase(id);
    }
    if(id && !ST_DLCAllowed(ps,id)) { id=0; base=WP_SABER; }
    if(base<WP_NONE || base>=WP_NUM_WEAPONS) { base=ps->weapon; id=ps->stats[ST_DLC_STAT]; }
    if(id) ps->stats[STAT_WEAPONS]|=1<<base;
    move->cmd.weapon=base;
    if(ps->weapon==base && ps->weaponTime<=0 && ps->weaponstate==WEAPON_READY)
        ps->stats[ST_DLC_STAT]=id;
    if(ST_DLCBase(ps->stats[ST_DLC_STAT])!=ps->weapon) ps->stats[ST_DLC_STAT]=0;
    if(infinite) {
        memcpy(ammo,ps->ammo,sizeof(ammo));
        for(i=AMMO_BLASTER;i<=AMMO_ROCKETS;++i) ps->ammo[i]=ammoData[i].max;
    }
    PmoveSingle(move);
    if(infinite) for(i=AMMO_BLASTER;i<=AMMO_ROCKETS;++i) ps->ammo[i]=ammo[i];
    if(id && !(inventory&(1<<base))) ps->stats[STAT_WEAPONS]&=~(1<<base);
    move->cmd.weapon=command;
    if(ST_DLCBase(ps->stats[ST_DLC_STAT])!=ps->weapon) ps->stats[ST_DLC_STAT]=0;
}
#endif
