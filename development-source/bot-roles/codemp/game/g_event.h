#ifndef G_EVENT_H
#define G_EVENT_H
#include "st_event.h"
void ST_EventInit(void);
qboolean ST_EventActive(void);
qboolean ST_EventPlacing(void);
qboolean ST_EventCanJoin(int slot,int team);
qboolean ST_EventClientCommand(gentity_t* ent);
void ST_EventConsole(void);
void ST_EventFrame(void);
qboolean ST_EventThink(gentity_t* ent);
qboolean ST_EventBlocked(const gentity_t* ent);
qboolean ST_EventHoldEntity(gentity_t* ent);
qboolean ST_EventAllowCommand(int slot,const char* command);
void ST_EventDisconnect(int slot);
int ST_EventStaff(const STVerifiedAction*,STGameResult*);
/* Engine-only identity bridge. The identity service must authenticate the
 * account AND this exact game connection before calling SetAccount. */
#include "st_event_account_api.h"
#endif
