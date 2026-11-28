// Optional JKA movement readouts, inspired by TaystJK's movement HUD.
// Use the local player's observed motion. Nothing here writes user commands.
static void ST_DrawMovementKeys(const usercmd_t &cmd) {
    constexpr float keySize = 25.f;
    constexpr float pitch = 24.f;
    constexpr float top = 415.f;
    constexpr float idleOpacity = .72f;
    const float aspect = cls.glconfig.vidWidth > 0 && cls.glconfig.vidHeight > 0
        ? (640.f * cls.glconfig.vidHeight) / (480.f * cls.glconfig.vidWidth) : 1.f;
    const bool pressed[] = {
        cmd.upmove > 0, cmd.forwardmove > 0, cmd.upmove < 0,
        cmd.rightmove < 0, cmd.forwardmove < 0, cmd.rightmove > 0,
    };
    const auto art = CL_PersonalArt("movement_keycaps");
    const vec4_t idleTint = {1.f, 1.f, 1.f, idleOpacity};
    for (int i = 0; i < ARRAY_LEN(pressed); ++i) {
        const float x = 320.f + ((i % 3 - 1) * pitch - keySize * .5f) * aspect;
        const float y = top + i / 3 * pitch;
        if (art) {
            // The first row of the atlas is idle, the second is pressed.
            const float u = i / 8.f;
            const float v = pressed[i] ? .5f : 0.f;
            re->SetColor(pressed[i] ? nullptr : idleTint);
            re->DrawStretchPic(x, y, keySize * aspect, keySize,
                               u, v, u + .125f, v + .5f, art);
        } else {
            vec4_t dark = {.09f, .14f, .18f, pressed[i] ? .8f : .8f * idleOpacity};
            vec4_t light = {.9f, .98f, 1.f, pressed[i] ? 1.f : idleOpacity};
            const char *symbols[] = {"^_", "^", "v_", "<", "v", ">"};
            const auto *label = symbols[i];
            SCR_FillRect(x + 2.f * aspect, y + 2.f, (keySize - 4.f) * aspect, keySize - 4.f,
                         pressed[i] ? light : dark);
            SCR_DrawStringExt(static_cast<int>(x + (keySize - strlen(label) * 7.f) * .5f * aspect),
                              static_cast<int>(y + (keySize - 7.f) * .5f), 7, label,
                              pressed[i] ? dark : light, qtrue, qfalse);
        }
    }
    re->SetColor(nullptr);
}

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
    if (keys->integer)
        ST_DrawMovementKeys(cmd);
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
