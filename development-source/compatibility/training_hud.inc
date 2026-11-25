// Optional JKA movement readouts, inspired by TaystJK's movement HUD.
// Use the local player's observed motion. Nothing here writes user commands.
static void ST_DrawTrainingHud() {
    static cvar_t *strafe=Cvar_Get("st_trainStrafe","0",CVAR_ARCHIVE);
    static cvar_t *snap=Cvar_Get("st_trainSnap","0",CVAR_ARCHIVE);
    static cvar_t *pitch=Cvar_Get("st_trainPitch","0",CVAR_ARCHIVE);
    static cvar_t *speed=Cvar_Get("st_trainSpeed","0",CVAR_ARCHIVE);
    static cvar_t *keys=Cvar_Get("st_trainKeys","0",CVAR_ARCHIVE);
    if (!(strafe->integer || snap->integer || pitch->integer || speed->integer || keys->integer)) return;
    if (!cl.snap.valid || clc.demoplaying || Key_GetCatcher() ||
        !Cvar_VariableIntegerValue("cg_draw2D") || Cvar_VariableIntegerValue("st_photoMode")) return;
    const playerState_t &ps=cl.snap.ps;
    if (ps.clientNum!=clc.clientNum || ps.pm_type!=PM_NORMAL || ps.m_iVehicleNum ||
        ps.persistant[PERS_TEAM]==TEAM_SPECTATOR || ps.stats[STAT_HEALTH]<=0) return;
    const usercmd_t &cmd=cl.cmds[cl.cmdNumber & CMD_MASK];
    const usercmd_t &prev=cl.cmds[(cl.cmdNumber-1) & CMD_MASK];
    const float pace=sqrtf(ps.velocity[0]*ps.velocity[0]+ps.velocity[1]*ps.velocity[1]);
    const int fixed=Cvar_VariableIntegerValue("pmove_fixed");
    const float dt=Com_Clampi(1,32,fixed?Cvar_VariableIntegerValue("pmove_msec"):cmd.serverTime-prev.serverTime)*.001f;
    const float wish=ps.speed;
    const float yaw=SHORT2ANGLE(cmd.angles[YAW]+ps.delta_angles[YAW]);
    const float viewPitch=AngleNormalize180(SHORT2ANGLE(cmd.angles[PITCH]+ps.delta_angles[PITCH]));
    vec4_t cyan={.32f,.92f,1.f,1.f}, muted={.22f,.38f,.44f,.9f}, gold={1.f,.76f,.31f,1.f};
    if (speed->integer) {
        const char *s=va("%d u/s",(int)(pace+.5f));
        SCR_DrawStringExt(320-(int)strlen(s)*4,405,8,s,cyan,qtrue,qtrue);
    }
    if (keys->integer) {
        const char *labels[]={"F","L","B","R","UP","DN"};
        const bool pressed[]={cmd.forwardmove>0,cmd.rightmove<0,cmd.forwardmove<0,cmd.rightmove>0,cmd.upmove>0,cmd.upmove<0};
        for(int i=0;i<6;++i)
            SCR_DrawStringExt(264+i*20,422,8,labels[i],pressed[i]?cyan:muted,qtrue,qtrue);
    }
    if (pitch->integer) {
        SCR_FillRect(366,239,10,1,muted);
        SCR_FillRect(370,239+Com_Clamp(-40.f,40.f,viewPitch),8,2,gold);
        SCR_DrawStringExt(382,237,7,va("%.0f",viewPitch),cyan,qtrue,qtrue);
    }
    const float wishOffset=RAD2DEG(atan2f(-(float)cmd.rightmove,(float)cmd.forwardmove));
    if (snap->integer && wish>0) {
        // Each half-integer boundary changes a rounded horizontal velocity component.
        const float step=wish*dt;
        int start=0,last=-1;
        for(int x=0;x<=128;++x) {
            int zone=-1;
            if(x<128){
                const float radians=DEG2RAD(yaw+wishOffset+(64-x)*.7f);
                zone=((int)floorf(fabsf(step*cosf(radians))+.5f)+(int)floorf(fabsf(step*sinf(radians))+.5f))&1;
            }
            if(zone!=last){
                if(x>start) SCR_FillRect(256+start,380,x-start,4,last?cyan:muted);
                start=x;last=zone;
            }
        }
        SCR_FillRect(319,378,2,8,gold);
    }
    if(strafe->integer && pace>1 && wish>0 && (cmd.forwardmove || cmd.rightmove)) {
        const bool ground=ps.groundEntityNum!=ENTITYNUM_NONE;
        const float afterFriction=ground?Q_max(1.f,pace-Q_max(100.f,pace)*6.f*dt):pace;
        const float target=RAD2DEG(acosf(Com_Clamp(-1.f,1.f,wish*(1.f-(ground?10.f:1.f)*dt)/afterFriction)));
        const float heading=RAD2DEG(atan2f(ps.velocity[1],ps.velocity[0]));
        const float fov=Com_Clamp(10.f,160.f,Cvar_VariableValue("cg_fov"));
        for(int side=-1;side<=1;side+=2) {
            const float delta=AngleNormalize180(heading+side*target-wishOffset-yaw);
            if(fabsf(delta)>=fov*.5f) continue;
            const float x=320.f-320.f*tanf(DEG2RAD(delta))/tanf(DEG2RAD(fov*.5f));
            SCR_FillRect(x-1,260,2,12,cyan);
        }
    }
}
