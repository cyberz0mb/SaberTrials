#ifndef ST_MVP_RETENTION_H
#define ST_MVP_RETENTION_H
#include "st_mvp_api.h"
/* Preserve the current leader's latest finish while retiring older footage.
 * Later fighting by other players must not erase a passive MVP's only clip. */
static int ST_MvpRetireIndex(const stMvpEvent_t *events,int count,int leader) {
    int i,protectedIndex=-1;
    for(i=0;i<count;++i)if(events[i].attacker==leader)protectedIndex=i;
    for(i=0;i<count;++i)if(i!=protectedIndex)return i;
    return 0; /* A single clip can still expire if the hard budget requires it. */
}
#endif
