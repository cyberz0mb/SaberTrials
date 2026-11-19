/* Same per-move scratch initialization as G_MoverTeam, for the isolated fixture. */
qboolean ST_QAPush(gentity_t* check,gentity_t* pusher,vec3_t move,vec3_t amove) {
 pushed_p=pushed;
 return G_TryPushingEntity(check,pusher,move,amove);
}
