/* Included by g_main.c. Availability is server-owned, including cheat state. */
#include "st_dlc_weapons.h"
static vmCvar_t st_dlcEnabled, st_dlcInfiniteAmmo;

void ST_DLCGameInit(void) {
    char manifest[ST_DLC_MANIFEST_SIZE];
    trap->Cvar_Register(&st_dlcEnabled,"g_weaponDLC","1",CVAR_ARCHIVE|CVAR_LATCH|CVAR_SERVERINFO);
    trap->Cvar_Register(&st_dlcInfiniteAmmo,"g_infiniteAmmo","0",CVAR_CHEAT);
    ST_DLCLoad();
    if(!st_dlcEnabled.integer) st_dlcCount=0;
    ST_DLCManifest(manifest,sizeof(manifest));
    trap->SetConfigstring(ST_DLC_CONFIGSTRING,manifest);
}

void ST_DLCUpdateAccess(gentity_t *ent) {
    playerState_t *ps;
    int disabled,mask=0,i;
    if(!ent->client || ent->s.number>=MAX_CLIENTS) return;
    ps=&ent->client->ps;
    trap->Cvar_Update(&st_dlcInfiniteAmmo);
    disabled=(level.gametype==GT_DUEL || level.gametype==GT_POWERDUEL) ?
        g_duelWeaponDisable.integer : g_weaponDisable.integer;
    if(ps->pm_type==PM_NORMAL && ps->stats[STAT_HEALTH]>0 &&
       ent->client->sess.sessionTeam!=TEAM_SPECTATOR && !level.intermissiontime &&
       !ps->duelInProgress && !ps->trueJedi && !ps->isJediMaster &&
       !ps->m_iVehicleNum && !ps->emplacedIndex && !HasSetSaberOnly()) {
        for(i=1;i<=st_dlcCount;++i) {
            int bit=1<<st_dlcWeapons[i].base;
            /* Siege class restrictions still apply. Other modes require no pickup. */
            if(!(disabled&bit) && (level.gametype!=GT_SIEGE || (ps->stats[STAT_WEAPONS]&bit)))
                mask|=ST_DLCAccessBit(st_dlcWeapons[i].base);
        }
        if(sv_cheats.integer && st_dlcInfiniteAmmo.integer) mask|=ST_DLC_INFINITE;
    }
    ps->stats[ST_DLC_ALLOWED_STAT]=mask;
    if(ps->stats[ST_DLC_STAT] && !ST_DLCAllowed(ps,ps->stats[ST_DLC_STAT])) {
        ps->stats[ST_DLC_STAT]=0;
        if(!(ps->stats[STAT_WEAPONS]&(1<<ps->weapon))) {
            for(i=WP_SABER;i>WP_NONE;--i) if(ps->stats[STAT_WEAPONS]&(1<<i)) break;
            ps->weapon=i;
            ps->weaponstate=WEAPON_READY;
        }
    }
}
