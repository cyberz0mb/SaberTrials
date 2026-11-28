// Called only for a visible character or its Profile preview.
typedef struct { void *owner; int bolts[2]; } stWearBolts_t;
static void ST_DrawWearable(const refEntity_t *parent, qhandle_t model, int slot, int time,
                            const vec3_t angles, qhandle_t *models, stWearBolts_t *cache) {
    mdxaBone_t matrix;
    refEntity_t piece;
    int i, j, bolt;
    if (!model || !parent->ghoul2) return;
    if (cache->owner!=parent->ghoul2) {
        cache->owner=parent->ghoul2;
        cache->bolts[0]=cache->bolts[1]=-2;
    }
    if (cache->bolts[slot]==-2)
        cache->bolts[slot]=trap->G2API_AddBolt(parent->ghoul2,0,slot ? "*back" : "*head_top");
    bolt=cache->bolts[slot];
    if (bolt<0) return;
    vec3_t scale;
    VectorCopy(parent->modelScale,scale);
    const qboolean valid=trap->G2API_GetBoltMatrix(parent->ghoul2,0,bolt,&matrix,angles,
        parent->origin,time,models,scale);
    if (!valid) return;
    memset(&piece,0,sizeof(piece));
    piece.reType=RT_MODEL;piece.hModel=model;piece.renderfx=parent->renderfx;
    piece.customShader=parent->customShader;
    memcpy(piece.shaderRGBA,parent->shaderRGBA,sizeof(piece.shaderRGBA));
    for (i=0;i<3;++i) {
        for (j=0;j<3;++j) piece.axis[i][j]=matrix.matrix[j][i];
        piece.origin[i]=matrix.matrix[i][3]-2*matrix.matrix[i][2];
    }
    VectorCopy(piece.origin,piece.oldorigin);
    VectorCopy(parent->lightingOrigin,piece.lightingOrigin);
    trap->R_AddRefEntityToScene(&piece);
}
