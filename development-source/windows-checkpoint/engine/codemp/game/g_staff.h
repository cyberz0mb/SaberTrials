#ifndef G_STAFF_H
#define G_STAFF_H
#include "../staff/st_staff_game_api.h"
#include "../staff/st_staff_movement.h"
qboolean ST_StaffBlocked(const gentity_t* ent);
int ST_StaffRoleForClient(int slot);
qboolean ST_StaffThink(gentity_t* ent);
void ST_StaffFrame(void);
void ST_StaffClearClient(int slot);
void ST_StaffResetAll(void);
#endif
