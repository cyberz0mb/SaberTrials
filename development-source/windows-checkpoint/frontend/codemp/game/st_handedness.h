// Shared preference, replication and attachment policy; no gameplay timers.
#ifndef ST_HANDEDNESS_H
#define ST_HANDEDNESS_H
#define ST_HAND_PROTOCOL 1
#define ST_HAND_LEFT_FLAG (1u << 9)
enum { ST_HAND_RIGHT=0, ST_HAND_LEFT=1 };
static inline int ST_HandParse(const char* value) {
    return value && value[0]=='1' && value[1]==0 ? ST_HAND_LEFT : ST_HAND_RIGHT;
}
static inline int ST_HandAtSpawn(int requested,int serverEnabled,int clientSupported,int rigSupported) {
    return requested==ST_HAND_LEFT && serverEnabled && clientSupported && rigSupported
        ? ST_HAND_LEFT : ST_HAND_RIGHT;
}
static inline unsigned ST_HandSetFlag(unsigned flags,int hand) {
    return (flags & ~ST_HAND_LEFT_FLAG) | (hand==ST_HAND_LEFT?ST_HAND_LEFT_FLAG:0);
}
static inline int ST_HandFromFlags(unsigned flags) {
    return (flags & ST_HAND_LEFT_FLAG)?ST_HAND_LEFT:ST_HAND_RIGHT;
}
/* Mounted combat retains the engine's original pose/weapon policy. The saved
 * dominant hand is unchanged and resumes immediately after dismounting. */
static inline int ST_HandEffective(unsigned flags,int vehicleNum) {
    return vehicleNum ? ST_HAND_RIGHT : ST_HandFromFlags(flags);
}
static inline int ST_HandAttachment(int slot,int hand,int wrist) {
    if(slot<0 || slot>1)return -1;
    return (slot^(hand==ST_HAND_LEFT))+(wrist?3:0);
}
#endif
