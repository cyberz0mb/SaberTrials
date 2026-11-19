/* Physical contact-limb routing after directional source mapping + reflection.
 * Never swap the persistent anatomical renderInfo foot/hand bolt identities.
 */
#ifndef ST_DIRECTION_KICK_H
#define ST_DIRECTION_KICK_H
enum stDirectionContactLimb_e {
    ST_CONTACT_NONE,
    ST_CONTACT_RIGHT_FOOT,
    ST_CONTACT_LEFT_FOOT,
    ST_CONTACT_RIGHT_HAND,
    ST_CONTACT_LEFT_HAND
};

/* For the hilt-bash branch pass BOTH_A7_HILT from torsoAnim. Otherwise pass
 * semantic legsAnim. splitRightPhase is level.framenum & 1 for KICK_RL. */
static inline int ST_DirectionKickLimb(int semanticAnim, int mirrored, int splitRightPhase)
{
    switch (semanticAnim) {
    case BOTH_A7_HILT:
        return mirrored ? ST_CONTACT_LEFT_HAND : ST_CONTACT_RIGHT_HAND;
    case BOTH_A7_KICK_R:
        return ST_CONTACT_RIGHT_FOOT;
    case BOTH_A7_KICK_L:
        return ST_CONTACT_LEFT_FOOT;
    case BOTH_A7_KICK_RL:
        return splitRightPhase ? ST_CONTACT_RIGHT_FOOT : ST_CONTACT_LEFT_FOOT;
    case BOTH_A7_KICK_F:
    case BOTH_A7_KICK_B:
    case BOTH_A7_KICK_F_AIR:
    case BOTH_A7_KICK_B_AIR:
    case BOTH_A7_KICK_R_AIR:
    case BOTH_A7_KICK_L_AIR:
    case BOTH_A7_KICK_S:
    case BOTH_A7_KICK_BF:
    case BOTH_GETUP_BROLL_B:
    case BOTH_GETUP_BROLL_F:
    case BOTH_GETUP_FROLL_B:
    case BOTH_GETUP_FROLL_F:
        return mirrored ? ST_CONTACT_LEFT_FOOT : ST_CONTACT_RIGHT_FOOT;
    default:
        return ST_CONTACT_NONE;
    }
}
#endif
