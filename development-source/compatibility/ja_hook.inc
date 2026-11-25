// The JA+ client identifies a hook by its missile entity and weapon type.
// Draw only the endpoint supplied by the server. The server owns the pull.
static void JA_DrawHook(centity_t *hook) {
    // Slider's client reads the missile's otherEntityNum for the hand bolt.
    // clientNum on a missile can be zero even when another player fired it.
    int owner=hook->currentState.otherEntityNum;
    if (owner<0 || owner>=MAX_CLIENTS) return;
    centity_t *player=&cg_entities[owner];
    // The local player arrives as playerState and can be absent from the
    // snapshot entity list. Remote owners still need a current entity.
    const qboolean local=(qboolean)(cg.snap && cg.snap->ps.clientNum==owner);
    if (!local && !player->currentValid) return;
    const float *origin=local?cg.predictedPlayerState.origin:player->lerpOrigin;
    refEntity_t beam={0};
    VectorCopy(origin,beam.origin);
    beam.origin[2]+=24;
    mdxaBone_t hand;
    int bolt=cgs.clientinfo[owner].bolt_rhand;
    if (player->ghoul2 && bolt>=0 && trap->G2API_GetBoltMatrix(player->ghoul2,0,bolt,&hand,
            player->turAngles,origin,cg.time,cgs.gameModels,player->modelScale))
        BG_GiveMeVectorFromMatrix(&hand,ORIGIN,beam.origin);
    VectorCopy(hook->lerpOrigin,beam.oldorigin);
    beam.reType=RT_LINE;
    beam.radius=1;
    beam.customShader=cgs.media.whiteShader;
    beam.shaderRGBA[0]=beam.shaderRGBA[3]=255;
    beam.shaderTexCoord[0]=beam.shaderTexCoord[1]=1;
    trap->R_AddRefEntityToScene(&beam);
    if (cgs.media.jaHook) {
        refEntity_t model={0};
        model.reType=RT_MODEL;
        model.hModel=cgs.media.jaHook;
        VectorCopy(hook->lerpOrigin,model.origin);
        AnglesToAxis(hook->lerpAngles,model.axis);
        trap->R_AddRefEntityToScene(&model);
    }
}
