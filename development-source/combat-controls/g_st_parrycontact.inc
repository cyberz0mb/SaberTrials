/* Called only after authoritative trace, duel/target and unblockable checks.
 * Idle touches, thrown sabers and projectile probes cannot spend a parry. */
static qboolean ST_TryAttackParryContact(gentity_t *attacker,gentity_t *defender,
                                        vec3_t point,int damage,qboolean unblockable) {
 return attacker && attacker->client && attacker!=defender &&
   attacker->health>0 && !attacker->client->ps.saberInFlight &&
   !unblockable && damage>SABER_NONATTACK_DAMAGE && SaberAttacking(attacker) &&
   ST_ConsumeAttackParry(defender,point);
}
