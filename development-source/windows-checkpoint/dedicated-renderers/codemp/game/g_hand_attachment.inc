/* Rebind only destination instances, never shared weapon templates. */
static void G_STSyncHandAttachments(gentity_t *self) {
    int slot,hand;
    if(self->s.number<0 || self->s.number>=MAX_CLIENTS ||
       !self->client || !self->ghoul2 || self->client->ps.weapon!=WP_SABER)return;
    hand=ST_HandEffective(self->client->ps.eFlags2,self->client->ps.m_iVehicleNum);
    for(slot=0;slot<MAX_SABERS;slot++) {
        if(trap->G2API_HasGhoul2ModelOnIndex(&(self->ghoul2),slot+1))
            trap->G2API_SetBoltInfo(self->ghoul2,slot+1,
                ST_HandAttachment(slot,hand,(self->client->saber[slot].saberFlags&SFL_BOLT_TO_WRIST)!=0));
    }
}
