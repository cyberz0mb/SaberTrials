/* Called between frames, in isolated QA builds only. */
float ST_QAMasterDamage(void) {
    float result;
    WP_SaberClearDamage();
    WP_SaberDamageAdd(0, vec3_origin, vec3_origin, 10, qfalse, 0);
    WP_SaberDamageAdd(0, vec3_origin, vec3_origin, 20, qfalse, 0);
    result = totalDmg[0];
    WP_SaberClearDamage();
    return result;
}
