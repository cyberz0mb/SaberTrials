/* Keeps mounted stock playback and post-dismount dominant grip synchronized. */
void CG_STSyncHandAttachments(centity_t *cent,void *instance) {
    clientInfo_t *ci;
    int slot,hand;
    if(!instance || cent->currentState.weapon!=WP_SABER || cent->currentState.eType!=ET_PLAYER ||
       cent->currentState.clientNum<0 || cent->currentState.clientNum>=MAX_CLIENTS)return;
    ci=&cgs.clientinfo[cent->currentState.clientNum];
    if(!ci)return;
    hand=cent->stLockStandardPose?ST_HAND_RIGHT:ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum);
    for(slot=0;slot<MAX_SABERS;slot++) {
        if(trap->G2API_HasGhoul2ModelOnIndex(&instance,slot+1))
            trap->G2API_SetBoltInfo(instance,slot+1,
                ST_HandAttachment(slot,hand,(ci->saber[slot].saberFlags&SFL_BOLT_TO_WRIST)!=0));
    }
}
