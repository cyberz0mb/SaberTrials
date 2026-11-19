/* Local fidelity-proof bridge. Contains borrowed pointers, never network data.
 * GPL-2.0-or-later. Only valid synchronously in a matching listen-server build. */
#ifndef ST_MVP_API_H
#define ST_MVP_API_H
#define ST_MVP_ACTORS 32
#define ST_MVP_FRAMES 512
#define ST_MVP_EVENTS 32
#define ST_MVP_LIMBS 32
#define ST_MVP_BLADES 16
#define ST_MVP_PROPS 64
#define ST_MVP_RENDER_POSES 256
#define ST_MVP_MAX_GAP 300
#define ST_MVP_MEMORY_LIMIT (256 * 1024 * 1024)
#define ST_MVP_PRESENT_MVP 0
#define ST_MVP_PRESENT_DUEL 1
#define ST_MVP_PRESENT_MATCH 2
#define ST_MVP_PRESENT_CHAMPION 3
#define ST_MVP_WINNER_MS 5000
#define ST_MVP_CARD_MS 3000

typedef struct {
    float base[3],dir[3],length,radius,duration;
    int color,style,strong,flags;
} stMvpBlade_t;
typedef struct {
    int clientNum;
    void *pose;
    float origin[3], angles[3], scale[3];
    float bladeBase[3], bladeDir[3], bladeLength;
    int bladeColor, alive, spawnId;
    float trailDuration;
    int trailStyle, strongTrail;
    int bladeCount, poseBytes, weapon;
    stMvpBlade_t blades[ST_MVP_BLADES];
} stMvpActor_t;

typedef struct {
    int entityNum, owner, part;
    float origin[3], angles[3];
} stMvpLimb_t;

typedef struct {
    int entityNum,modelIndex,brush,poseBytes,type,weapon,flags;
    void *pose;
    float origin[3],angles[3],scale[3],velocity[3];
} stMvpProp_t;

typedef struct {
    int time, count, bytes;
    stMvpActor_t actors[ST_MVP_ACTORS];
    int limbCount;
    stMvpLimb_t limbs[ST_MVP_LIMBS];
    int propCount;
    stMvpProp_t props[ST_MVP_PROPS];
} stMvpSample_t;

typedef struct {
    int killTime, firstTime, lastTime, attacker, victim;
} stMvpEvent_t;

typedef struct {
    int killTime, firstTime, lastTime, winner, totalKills, retainedBytes;
    int resultTime, presentation, winnerScore, loserScore, cardOnly, forfeit;
    int eventCount;
    stMvpEvent_t events[ST_MVP_EVENTS];
    char name[64];
    const stMvpSample_t *before, *after;
} stMvpClip_t;
#endif
