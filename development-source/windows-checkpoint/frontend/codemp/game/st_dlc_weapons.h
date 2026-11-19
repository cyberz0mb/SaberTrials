/* Saber Trials additive gun definitions. GPL-2.0-or-later. */
#ifndef ST_DLC_WEAPONS_H
#define ST_DLC_WEAPONS_H

#define ST_DLC_MAX 63
#define ST_DLC_COMMAND 32
#define ST_DLC_CONFIGSTRING 33
#define ST_DLC_STAT 13
#define ST_DLC_ALLOWED_STAT 14
#define ST_DLC_ENTITY_SHIFT 18 /* Lower 18 bits remain the Holocron mask. */
#define ST_DLC_INFINITE 1
#define ST_DLC_MANIFEST_SIZE 4096

enum {
    ST_DLC_VIEW, ST_DLC_WORLD, ST_DLC_ICON, ST_DLC_HANDS,
    ST_DLC_MUZZLE, ST_DLC_ALT_MUZZLE,
    ST_DLC_SHOT, ST_DLC_ALT_SHOT,
    ST_DLC_IMPACT, ST_DLC_ALT_IMPACT,
    ST_DLC_FIRE_SOUND, ST_DLC_ALT_FIRE_SOUND,
    ST_DLC_PROJECTILE, ST_DLC_ALT_PROJECTILE,
    ST_DLC_ASSET_COUNT
};
typedef struct {
    char id[32], name[64];
    int base;
    unsigned checksum;
    qboolean available;
    char asset[ST_DLC_ASSET_COUNT][MAX_QPATH];
} stDlcWeapon_t;

extern stDlcWeapon_t st_dlcWeapons[ST_DLC_MAX+1];
extern int st_dlcCount;
qboolean ST_DLCParse(char *text, stDlcWeapon_t *weapon);
void ST_DLCLoad(void);
void ST_DLCManifest(char *text, int size);
qboolean ST_DLCMatchManifest(const char *text);
int ST_DLCEntityId(const entityState_t *state);
int ST_DLCBase(int id);
qboolean ST_DLCGun(int base);
int ST_DLCAccessBit(int base);
qboolean ST_DLCAllowed(const playerState_t *ps, int id);
void ST_DLCPmove(pmove_t *move);

#ifdef _GAME
void ST_DLCGameInit(void);
void ST_DLCUpdateAccess(gentity_t *ent);
extern int st_dlcFiringId, st_dlcFiringAlt;
#endif

#ifdef _CGAME
void ST_DLCClientInit(void);
void ST_DLCCleanup(void);
void ST_DLCInspect(void);
int ST_DLCCommandWeapon(int base);
weaponInfo_t *ST_DLCWeaponInfo(int id, int base);
qboolean ST_DLCImpact(const entityState_t *state, vec3_t origin, vec3_t dir);
qboolean ST_DLCHitscanImpact(const entityState_t *state, int base, vec3_t origin, vec3_t dir);
qboolean ST_DLCBeam(const entityState_t *state, int base, int alt, vec3_t start, vec3_t end);
#endif
#endif
