/* Private visual fixture only. Not part of the production overlay or packages.
 * Forces local render poses through the real Ghoul2 APIs. Server state/collision
 * and animation files are untouched. Keep sv_cheats gating even in this fixture.
 */
static qboolean ST_ModelQA(centity_t *cent) {
    static vmCvar_t face, blink, frame, arm;
    static qboolean registered=qfalse;
    static int lastFace=-99,lastBlink=-99,lastFrame=-99,lastArm=0;
    char cheats[16]; vec3_t angles={0,0,0};
    if(cent->currentState.number!=cg.clientNum) return qfalse;
    trap->Cvar_VariableStringBuffer("sv_cheats",cheats,sizeof(cheats));
    if(!atoi(cheats)) return qfalse;
    if(!registered) {
        trap->Cvar_Register(&face,"st_modelQA_face","-1",CVAR_CHEAT);
        trap->Cvar_Register(&blink,"st_modelQA_blink","-1",CVAR_CHEAT);
        trap->Cvar_Register(&frame,"st_modelQA_frame","-1",CVAR_CHEAT);
        trap->Cvar_Register(&arm,"st_modelQA_hideArm","0",CVAR_CHEAT);
        registered=qtrue;
    }
    trap->Cvar_Update(&face);trap->Cvar_Update(&blink);trap->Cvar_Update(&frame);trap->Cvar_Update(&arm);
    /* r_arm is a grouping surface in this asset. OFF alone leaves its child
     * mesh chunks visible; NODESCENDANTS is required to simulate a lost limb. */
    if(arm.integer || lastArm) trap->G2API_SetSurfaceOnOff(cent->ghoul2,"r_arm",arm.integer?(0x2|0x100):0);
    if(frame.integer>=0 && frame.integer<20000) {
        const char *names[]={"model_root","lower_lumbar","Motion"};int i;
        for(i=0;i<3;++i) trap->G2API_SetBoneAnim(cent->ghoul2,0,names[i],frame.integer,frame.integer+1,
            BONE_ANIM_OVERRIDE|BONE_ANIM_OVERRIDE_FREEZE,1,cg.time,-1,0);
    }
    if(face.integer>=0 && face.integer<18) trap->G2API_SetBoneAnim(cent->ghoul2,0,"face",face.integer,face.integer+1,
        BONE_ANIM_OVERRIDE|BONE_ANIM_OVERRIDE_FREEZE,1,cg.time,-1,0);
    if(blink.integer>=0) {
        angles[YAW]=blink.integer?-50:0;
        trap->G2API_SetBoneAngles(cent->ghoul2,0,"leye",angles,BONE_ANGLES_POSTMULT,POSITIVE_Y,POSITIVE_Z,POSITIVE_X,NULL,0,cg.time);
        trap->G2API_SetBoneAngles(cent->ghoul2,0,"reye",angles,BONE_ANGLES_POSTMULT,POSITIVE_Y,POSITIVE_Z,POSITIVE_X,NULL,0,cg.time);
    }
    if(face.integer!=lastFace || blink.integer!=lastBlink || frame.integer!=lastFrame || arm.integer!=lastArm) {
        trap->Print("ST_MODEL_QA local=%d face=%d blink=%d frame=%d hideArm=%d animIndex=%d noFace=%d\n",
            cg.clientNum,face.integer,blink.integer,frame.integer,arm.integer,cent->localAnimIndex,cent->noFace);
        lastFace=face.integer;lastBlink=blink.integer;lastFrame=frame.integer;lastArm=arm.integer;
    }
    return face.integer>=0 || blink.integer>=0;
}
