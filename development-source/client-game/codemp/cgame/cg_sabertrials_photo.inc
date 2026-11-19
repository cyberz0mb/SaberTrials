// Photo camera and capture. GPL-2.0-or-later. Included by cg_view.c.
// Never changes the saved HUD, portrait, Streamer, view or input preferences.
#include "ui/ui_shared.h"
typedef struct {
    qboolean active, detached, initialized;
    vec3_t origin, angles;
    int lastRealTime, captureFrames, cleanUntil;
} stPhoto_t;
static stPhoto_t stPhoto;

static int ST_PhotoInt(const char *name) {
    char text[32];
    trap->Cvar_VariableStringBuffer(name, text, sizeof(text));
    return atoi(text);
}

qboolean ST_PhotoActive(void) { return stPhoto.active; }

void ST_PhotoStop(void) {
    if (stPhoto.detached) trap->Key_SetCatcher(trap->Key_GetCatcher() & ~KEYCATCH_CGAME);
    memset(&stPhoto, 0, sizeof(stPhoto));
    trap->Cvar_Set("st_photoMode", "0");
    trap->Cvar_Set("st_photoFreeze", "0");
}

static qboolean ST_PhotoEligible(void) {
    if (!cg.snap || cg.predictedPlayerState.pm_type == PM_INTERMISSION) return qfalse;
    if (cg.demoPlayback || ST_PhotoInt("st_photoSolo")) return qtrue;
    // Following replaces the received player state. Consult our own client info.
    return cgs.clientinfo[cg.clientNum].team == TEAM_SPECTATOR;
}

void ST_PhotoToggle_f(void) {
    if (stPhoto.active || ST_PhotoInt("st_photoMode")) ST_PhotoStop();
    else if (!ST_PhotoEligible()) trap->Print("Photo Mode: spectate first, or use local solo play / a replay.\n");
    else trap->Cvar_Set("st_photoMode", "1");
}

void ST_PhotoCapture_f(void) {
    if (!stPhoto.active && !ST_PhotoEligible()) {
        trap->Print("Open Photo Mode before taking a clean photo.\n");
        return;
    }
    trap->Cvar_Set("st_photoMode", "1");
    // Give the UI/console time to close; do not change the player's HUD cvars.
    stPhoto.captureFrames = 3;
    stPhoto.cleanUntil = trap->Milliseconds() + 1000;
}

static void ST_PhotoSettings(void) {
    trap->Key_SetCatcher(trap->Key_GetCatcher() & ~KEYCATCH_CGAME);
    trap->SendConsoleCommand("ui_openmenu st_photo\n");
}

qboolean ST_PhotoKey(int key, qboolean down) {
    if (!stPhoto.active || !stPhoto.detached) return qfalse;
    if (!down || (key & K_CHAR_FLAG)) return qtrue;
    if (key == A_TAB) ST_PhotoSettings();
    else if (key == A_ENTER || key == A_MOUSE1) ST_PhotoCapture_f();
    else if (key == 'f' && ST_PhotoInt("st_photoSolo"))
        trap->Cvar_Set("st_photoFreeze", ST_PhotoInt("st_photoFreeze") ? "0" : "1");
    else if (key == A_MWHEELUP || key == A_MWHEELDOWN)
        trap->Cvar_Set("st_photoFov", va("%.6g", Com_Clamp(20,120,
            st_photoFov.value + (key == A_MWHEELUP ? -2 : 2))));
    return qtrue;
}

qboolean ST_PhotoMouse(int x, int y) {
    if (!stPhoto.active || !stPhoto.detached) return qfalse;
    stPhoto.angles[YAW] = AngleNormalize180(stPhoto.angles[YAW] - x * 0.12f);
    stPhoto.angles[PITCH] = Com_Clamp(-89,89,stPhoto.angles[PITCH] + y * 0.12f);
    return qtrue;
}

static void ST_PhotoFrame(void) {
    qboolean detached;
    if (!st_photoMode.integer) {
        if (stPhoto.active) ST_PhotoStop();
        return;
    }
    if (!ST_PhotoEligible()) {
        ST_PhotoStop();
        trap->Print("Photo Mode ended: free camera requires solo play, a replay, or spectating.\n");
        return;
    }
    detached = cg.demoPlayback || ST_PhotoInt("st_photoSolo");
    if (!stPhoto.active) {
        stPhoto.active = qtrue;
        stPhoto.lastRealTime = trap->Milliseconds();
        if (!detached && (cg.snap->ps.pm_flags & PMF_FOLLOW))
            trap->SendClientCommand("follow");
    }
    if (stPhoto.detached != detached) {
        if (stPhoto.detached) trap->Key_SetCatcher(trap->Key_GetCatcher() & ~KEYCATCH_CGAME);
        stPhoto.initialized = qfalse;
    }
    stPhoto.detached = detached;
    if (detached && !trap->Key_GetCatcher()) trap->Key_SetCatcher(KEYCATCH_CGAME);
    // Online spectators use native movement so the server streams the camera's
    // actual visibility set. No detached camera or fake player movement online.
}

static void ST_PhotoView(void) {
    int now, elapsed, catcher;
    float fov, aspect;
    if (!stPhoto.active) return;
    now = trap->Milliseconds();
    elapsed = Com_Clampi(0,100,now - stPhoto.lastRealTime);
    stPhoto.lastRealTime = now;
    catcher = trap->Key_GetCatcher();
    if (stPhoto.detached) {
        if (!stPhoto.initialized) {
            trace_t fit;
            vec3_t mins = {-8,-8,-8}, maxs = {8,8,8};
            int distance, axis, sign;
            VectorCopy(cg.refdef.vieworg, stPhoto.origin);
            VectorCopy(cg.refdef.viewangles, stPhoto.angles);
            // The ordinary third-person camera has a smaller collision hull.
            // Nudge out of nearby walls before using the photo camera hull,
            // otherwise a camera starting against a wall could never move.
            CG_Trace(&fit,stPhoto.origin,mins,maxs,stPhoto.origin,cg.clientNum,MASK_SOLID);
            for (distance=8; fit.startsolid && distance<=32; distance+=8) {
                for (axis=0; fit.startsolid && axis<3; axis++) {
                    for (sign=-1; fit.startsolid && sign<=1; sign+=2) {
                        vec3_t candidate;
                        trace_t path, space;
                        VectorCopy(stPhoto.origin,candidate);
                        candidate[axis] += distance*sign;
                        CG_Trace(&path,stPhoto.origin,NULL,NULL,candidate,cg.clientNum,MASK_SOLID);
                        CG_Trace(&space,candidate,mins,maxs,candidate,cg.clientNum,MASK_SOLID);
                        if (path.fraction==1 && !path.startsolid && !space.startsolid && !space.allsolid) {
                            VectorCopy(candidate,stPhoto.origin);
                            fit=space;
                        }
                    }
                }
            }
            stPhoto.initialized = qtrue;
        }
        if (catcher == KEYCATCH_CGAME) {
            vec3_t forward, right, direction, end;
            trace_t trace;
            float speed = Com_Clamp(20,800,st_photoSpeed.value) * elapsed / 1000.0f;
            int f = trap->Key_IsDown('w') - trap->Key_IsDown('s');
            int r = trap->Key_IsDown('d') - trap->Key_IsDown('a');
            int u = trap->Key_IsDown(A_SPACE) - trap->Key_IsDown(A_CTRL);
            if (trap->Key_IsDown(A_SHIFT)) speed *= 0.25f;
            AngleVectors(stPhoto.angles, forward, right, NULL);
            VectorScale(forward, f, direction);
            VectorMA(direction, r, right, direction);
            direction[2] += u;
            if (VectorNormalize(direction)) {
                vec3_t mins = {-8,-8,-8}, maxs = {8,8,8};
                VectorMA(stPhoto.origin, speed, direction, end);
                CG_Trace(&trace, stPhoto.origin, mins, maxs, end, cg.clientNum, MASK_SOLID);
                if (!trace.startsolid && !trace.allsolid) VectorCopy(trace.endpos, stPhoto.origin);
            }
        }
        VectorCopy(stPhoto.origin, cg.refdef.vieworg);
        VectorCopy(stPhoto.angles, cg.refdef.viewangles);
        cg.renderingThirdPerson = qtrue;
    }
    cg.refdef.viewangles[ROLL] = Com_Clamp(-45,45,st_photoRoll.value);
    AnglesToAxis(cg.refdef.viewangles,cg.refdef.viewaxis);
    cg.refdef.x = cg.refdef.y = 0;
    cg.refdef.width = cgs.glconfig.vidWidth;
    cg.refdef.height = cgs.glconfig.vidHeight;
    fov = Com_Clamp(20,120,st_photoFov.value);
    aspect = (float)cg.refdef.width / cg.refdef.height;
    if (cg_fovAspectAdjust.integer) fov = atan(tan(fov*M_PI/360.0f)*0.75f*aspect)*360.0f/M_PI;
    cg.refdef.fov_x = fov;
    cg.refdef.fov_y = atan(tan(fov*M_PI/360.0f)/aspect)*360.0f/M_PI;
}

void ST_PhotoDraw(void) {
    const vec4_t cyan = {.45f,.83f,1,1};
    int now = trap->Milliseconds();
    if (!stPhoto.active) return;
    cg.scoreBoardShowing = qfalse;
    if (stPhoto.captureFrames > 0) {
        if (trap->Key_GetCatcher() & (KEYCATCH_UI|KEYCATCH_CONSOLE)) {
            stPhoto.captureFrames = 3;
            stPhoto.cleanUntil = now + 1000;
        } else if (--stPhoto.captureFrames == 0) trap->SendConsoleCommand("screenshot_png\n");
        return;
    }
    if (now < stPhoto.cleanUntil || (trap->Key_GetCatcher() & (KEYCATCH_UI|KEYCATCH_CONSOLE))) return;
    if (st_photoGuides.integer) {
        vec4_t line = {.45f,.83f,1,.3f};
        CG_FillRect(640.0f/3,0,.5f,480,line); CG_FillRect(1280.0f/3,0,.5f,480,line);
        CG_FillRect(0,160,640,.5f,line); CG_FillRect(0,320,640,.5f,line);
    }
    if (st_photoHelp.integer) {
        vec4_t shade = {.008f,.02f,.035f,.72f};
        CG_FillRect(12,423,616,45,shade);
        CG_Text_Paint(24,439,.48f,cyan,stPhoto.detached ?
            "PHOTO  |  WASD + mouse   Space / Ctrl: up / down   Shift: slow" :
            "PHOTO  |  Use your spectator movement keys   Esc: settings",0,0,ITEM_TEXTSTYLE_SHADOWED,FONT_SMALL2);
        CG_Text_Paint(24,457,.46f,colorWhite,stPhoto.detached ?
            (ST_PhotoInt("st_photoSolo") ? "Enter: photo   Tab: settings   Esc: exit   F: Live / Freeze" :
            "Enter: photo   Tab: settings   Esc: exit   Wheel: zoom") :
            "Take a photo from the Photo Mode menu or your Capture Photo key.",0,0,ITEM_TEXTSTYLE_SHADOWED,FONT_SMALL2);
    }
}
