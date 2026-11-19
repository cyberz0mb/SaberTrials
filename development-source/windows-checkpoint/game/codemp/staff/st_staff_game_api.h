#ifndef ST_STAFF_GAME_API_H
#define ST_STAFF_GAME_API_H
#include <stdint.h>
#define ST_STAFF_API_VERSION 2
#define ST_STAFF_MAX_ARGS 4
#define ST_STAFF_ARG_SIZE 192
enum STStaffCommand {
 ST_CMD_LIST=1, ST_CMD_WHOAMI, ST_CMD_ADD, ST_CMD_ROLE, ST_CMD_REMOVE,
 ST_CMD_FREEZE, ST_CMD_UNFREEZE, ST_CMD_GHOST_ON, ST_CMD_GHOST_OFF,
 ST_CMD_SUMMON, ST_CMD_TRAVEL_PLAYER, ST_CMD_TRAVEL_COORDS, ST_CMD_TRAVEL_SERVER,
 ST_CMD_RESOLVE, ST_CMD_LOGOUT, ST_CMD_RESOLVE_AIM
};
typedef struct STTargetRef { int slot; unsigned char generation[16]; } STTargetRef;
typedef struct STVerifiedAction {
 char account[65]; int role; uint64_t revision; int actorSlot;
 uint64_t sequence; int command; STTargetRef target;
 int argc; char args[ST_STAFF_MAX_ARGS][ST_STAFF_ARG_SIZE];
} STVerifiedAction;
typedef struct STGameResult { int ok; char message[768]; } STGameResult;
typedef struct STStaffImports {
 int version; unsigned int size;
 int (*RoleForClient)(int slot);
 int (*GenerationForClient)(int slot, unsigned char generation[16]);
} STStaffImports;
typedef struct STGameAPI {
 int version; unsigned int size;
 int (*Execute)(const STVerifiedAction*, STGameResult*);
 int (*ResolveTarget)(const char*, STTargetRef*);
 /* actorSlot -1 revokes all sessions; otherwise only effects owned by this connection. */
 void (*Revoke)(const char* account, int actorSlot);
 void (*ResetSessions)(void);
} STGameAPI;
typedef const STGameAPI* (*GetSaberTrialsStaffAPI_t)(const STStaffImports*);
static int ST_ValidGameAPI(const STGameAPI* api) {
 return api && api->version==ST_STAFF_API_VERSION && api->size==sizeof(STGameAPI)
  && api->Execute && api->ResolveTarget && api->Revoke && api->ResetSessions;
}
#endif
