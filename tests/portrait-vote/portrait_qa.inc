// Isolated native menu-only fixture: same head anchoring and refdef as cgame.
void ST_PortraitViewportQAPaint(void) {
    static void *model;
    static int bolt=-1;
    static qhandle_t skin;
    const int time=uiInfo.uiDC.realTime;
    vec4_t background={.012f,.016f,.02f,1},ink={.75f,.9f,1,1};
    vec3_t angles={0,180,0},zero={0,0,0},scale={1,1,1},light={0,-20,25};
    refEntity_t ent;refdef_t rd;mdxaBone_t matrix;
    float h=80,w=h*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
    if (!trap->Cvar_VariableValue("st_portraitviewportqa")) return;
    UI_FillRect(0,0,640,480,background);
    uiInfo.uiDC.drawText(24,24,.45f,ink,"Native head viewport check",0,0,0,1);
    if (!model) {
        skin=trap->R_RegisterSkin("models/players/kyle/model_default.skin");
        trap->G2API_InitGhoul2Model(&model,"models/players/kyle/model.glm",0,skin,0,0,0);
        if (!model || !trap->G2API_SetRootSurface(model,0,"head")) { trap->Print("PORTRAIT_VIEW_QA failed head\n");return; }
        bolt=trap->G2API_AddBolt(model,0,"cranium");
        trap->Print("PORTRAIT_VIEW_QA ready bolt=%d\n",bolt);
    }
    uiInfo.uiDC.drawText(540,112,.6f,ink,"Leader",0,0,0,1);
    if (trap->Cvar_VariableValue("st_portraitviewportqa_hidden")) return;
    memset(&ent,0,sizeof(ent));memset(&rd,0,sizeof(rd));
    if (!trap->G2API_GetBoltMatrix(model,0,bolt,&matrix,angles,zero,time,NULL,scale)) return;
    ent.origin[0]=40-matrix.matrix[0][3];ent.origin[1]=-matrix.matrix[1][3];ent.origin[2]=-matrix.matrix[2][3]-2;
    AnglesToAxis(angles,ent.axis);VectorCopy(scale,ent.modelScale);
    ent.ghoul2=model;ent.radius=100;ent.customSkin=skin;ent.renderfx=RF_NOSHADOW|RF_MINLIGHT;
    ent.shaderRGBA[0]=ent.shaderRGBA[1]=ent.shaderRGBA[2]=ent.shaderRGBA[3]=255;
    rd.rdflags=RDF_NOWORLDMODEL|RDF_NOFOG;AxisClear(rd.viewaxis);rd.fov_x=rd.fov_y=30;
    rd.x=(630-w)*uiInfo.uiDC.xscale;rd.y=5*uiInfo.uiDC.yscale;
    rd.width=w*uiInfo.uiDC.xscale;rd.height=h*uiInfo.uiDC.yscale;rd.time=time;
    trap->R_ClearScene();trap->R_AddRefEntityToScene(&ent);
    trap->R_AddLightToScene(light,200,1,.93f,.85f);trap->R_RenderScene(&rd);
}
