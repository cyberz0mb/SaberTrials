/* Saber Trials head portrait. Included by cg_draw.c. GPL-2.0-or-later.
 * Own the preview instance: never change surfaces or bones on a world player.
 */
#include "ghoul2/G2.h"
typedef struct {
    void *model, *source;
    int client, mode, headBolt, eyeLeft, eyeRight, faceBolt, time;
    qhandle_t skin;
    qboolean attempted, ready;
    float yaw, pitch, kick, distance, offset;
} stPortrait_t;
static stPortrait_t st_portrait;

void ST_PortraitClear(void) {
    if (st_portrait.model) trap->G2API_CleanGhoul2Models(&st_portrait.model);
    memset(&st_portrait, 0, sizeof(st_portrait));
    st_portrait.client = -1;
}

void ST_PortraitInvalidate(int clientNum) {
    if (st_portrait.client == clientNum) ST_PortraitClear();
}

static qboolean ST_PortraitClient(int n) {
    return n >= 0 && n < MAX_CLIENTS && cgs.clientinfo[n].infoValid;
}

static int ST_PortraitOpponent(void) {
    int self = cg.clientNum;
    if (!cg.snap || cg.snap->ps.clientNum != self ||
        !ST_PortraitClient(self) || cgs.clientinfo[self].team == TEAM_SPECTATOR) return -1;
    if (cg.snap->ps.duelInProgress && ST_PortraitClient(cg.snap->ps.duelIndex) &&
        cg.snap->ps.duelIndex != self) return cg.snap->ps.duelIndex;
    if (cgs.gametype == GT_DUEL) {
        int other = self == cgs.duelist1 ? cgs.duelist2 : self == cgs.duelist2 ? cgs.duelist1 : -1;
        if (ST_PortraitClient(other) && other != self) return other;
    }
    // Power Duel and team fights do not have one unambiguous opponent.
    return -1;
}

static int ST_PortraitTarget(const char **label) {
    int other = ST_PortraitOpponent();
    if (st_portraitTarget.integer == 1) { *label = "Your character"; return cg.clientNum; }
    if (other >= 0) { *label = "Opponent"; return other; }
    if (st_portraitTarget.integer == 2) { *label = "You / no duel opponent"; return cg.clientNum; }
    if (cgs.gametype == GT_JEDIMASTER && ST_PortraitClient(cgs.jediMaster)) {
        *label = "Jedi Master"; return cgs.jediMaster;
    }
    if (cgs.gametype >= GT_TEAM || cgs.gametype == GT_DUEL || cgs.gametype == GT_POWERDUEL) {
        int i, best = -1, score = -999999;
        // Team modes don't publish CS_CLIENT_DUELWINNER; in Duel it describes
        // the last winner. Use public scores for spectators and team matches.
        for (i = 0; i < cg.numScores; i++) {
            int n = cg.scores[i].client;
            if (ST_PortraitClient(n) && cgs.clientinfo[n].team != TEAM_SPECTATOR && cg.scores[i].score > score) {
                best = n; score = cg.scores[i].score;
            }
        }
        if (best >= 0) { *label = "Score leader"; return best; }
    }
    if (ST_PortraitClient(cgs.duelWinner) && cgs.clientinfo[cgs.duelWinner].team != TEAM_SPECTATOR) {
        *label = "Leader"; return cgs.duelWinner;
    }
    *label = "Your character";
    return cg.clientNum;
}

static float ST_PortraitClamp(float n, float low, float high) {
    if (n != n) return low;
    return n < low ? low : n > high ? high : n;
}

static void ST_PortraitFreeze(const char *bone, int anim) {
    const animation_t *a = &bgHumanoidAnimations[anim];
    if (a->numFrames > 0) trap->G2API_SetBoneAnim(st_portrait.model, 0, bone,
        a->firstFrame, a->firstFrame + 1, BONE_ANIM_OVERRIDE_FREEZE,
        1, cg.time, -1, 0);
}

static void ST_PortraitProfile(const char *modelName) {
    fileHandle_t file = 0;
    char data[4096];
    const char *p = data, *token;
    int length;
    st_portrait.distance = 40;
    st_portrait.offset = 2;
    length = trap->FS_Open(va("models/players/%s/st_portrait.cfg", modelName), &file, FS_READ);
    if (!file) return;
    if (length <= 0 || length >= sizeof(data)) { trap->FS_Close(file); return; }
    trap->FS_Read(data, length, file); trap->FS_Close(file); data[length] = 0;
    while ((token = COM_ParseExt(&p, qtrue))[0]) {
        if (!Q_stricmp(token, "distance")) {
            st_portrait.distance = ST_PortraitClamp(atof(COM_ParseExt(&p, qtrue)), 24, 90);
        } else if (!Q_stricmp(token, "offset")) {
            st_portrait.offset = ST_PortraitClamp(atof(COM_ParseExt(&p, qtrue)), -10, 20);
        } else if (!Q_stricmp(token, "hide")) {
            token = COM_ParseExt(&p, qtrue);
            if (token[0]) trap->G2API_SetSurfaceOnOff(st_portrait.model, token, 2);
        } else break;
    }
}

static qboolean ST_PortraitPrepare(int clientNum, int mode) {
    clientInfo_t *ci = &cgs.clientinfo[clientNum];
    if (st_portrait.client != clientNum || st_portrait.source != ci->ghoul2Model ||
        st_portrait.skin != ci->torsoSkin || st_portrait.mode != mode) ST_PortraitClear();
    if (st_portrait.attempted) return st_portrait.ready;
    if (!ci->ghoul2Model || ci->deferred) return qfalse;
    st_portrait.attempted = qtrue;
    st_portrait.client = clientNum;
    st_portrait.source = ci->ghoul2Model;
    st_portrait.skin = ci->torsoSkin;
    st_portrait.mode = mode;
    trap->G2API_DuplicateGhoul2Instance(ci->ghoul2Model, &st_portrait.model);
    if (!st_portrait.model) return qfalse;
    if (!trap->G2API_SetRootSurface(st_portrait.model, 0, "head")) {
        trap->G2API_CleanGhoul2Models(&st_portrait.model);
        return qfalse;
    }
    ST_PortraitProfile(ci->modelName);
    st_portrait.headBolt = trap->G2API_AddBolt(st_portrait.model, 0, "cranium");
    if (st_portrait.headBolt < 0) {
        trap->G2API_CleanGhoul2Models(&st_portrait.model);
        return qfalse;
    }
    st_portrait.faceBolt = trap->G2API_AddBolt(st_portrait.model, 0, "face");
    st_portrait.eyeLeft = trap->G2API_AddBolt(st_portrait.model, 0, "leye");
    st_portrait.eyeRight = trap->G2API_AddBolt(st_portrait.model, 0, "reye");
    ST_PortraitFreeze("model_root", BOTH_STAND1);
    if (st_portrait.faceBolt >= 0) ST_PortraitFreeze("face", FACE_ALERT);
    st_portrait.time = cg.time;
    st_portrait.ready = qtrue;
    return qtrue;
}

static void ST_PortraitFace(centity_t *cent, clientInfo_t *ci, qboolean live) {
    float frame, speed;
    int start, end, flags;
    vec3_t blink = {0, 0, 0};
    if (st_portrait.faceBolt >= 0) {
        if (live && !cent->noFace && trap->G2API_GetBoneAnim(cent->ghoul2, "face", cg.time,
                &frame, &start, &end, &flags, &speed, NULL, 0) && frame >= start && frame < end) {
            // Ghoul2 derives its start time by dividing by animSpeed when
            // setFrame is supplied. Never pass zero speed with an explicit frame.
            if (fabsf(speed) > .0001f)
                trap->G2API_SetBoneAnim(st_portrait.model, 0, "face", start, end,
                    flags & BONE_ANIM_TOTAL, speed, cg.time, frame, 0);
            else trap->G2API_SetBoneAnim(st_portrait.model, 0, "face", (int)frame, (int)frame + 1,
                    BONE_ANIM_OVERRIDE_FREEZE, 1, cg.time, -1, 0);
        } else ST_PortraitFreeze("face", FACE_ALERT);
    }
    if (live && ci->facial_blink < 0 && -ci->facial_blink > cg.time) blink[YAW] = -50;
    if (st_portrait.eyeLeft >= 0) trap->G2API_SetBoneAngles(st_portrait.model, 0, "leye", blink,
        BONE_ANGLES_POSTMULT, POSITIVE_Y, POSITIVE_Z, POSITIVE_X, NULL, 80, cg.time);
    if (st_portrait.eyeRight >= 0) trap->G2API_SetBoneAngles(st_portrait.model, 0, "reye", blink,
        BONE_ANGLES_POSTMULT, POSITIVE_Y, POSITIVE_Z, POSITIVE_X, NULL, 80, cg.time);
}

static qboolean ST_PortraitRender(int clientNum, float x, float y, float w, float h, int mode) {
    refdef_t rd;
    refEntity_t ent;
    mdxaBone_t matrix;
    vec3_t angles = {0, 180, 0}, zero = {0, 0, 0}, scale = {1, 1, 1};
    vec3_t light = {0, -20, 25};
    clientInfo_t *ci = &cgs.clientinfo[clientNum];
    centity_t *cent = &cg_entities[clientNum];
    qboolean live;
    float yaw = 0, pitch = 0, blend, kick = 0;
    int elapsed, pain;
    if (!ST_PortraitPrepare(clientNum, mode)) return qfalse;
    // The local predicted player is generated from playerState and is not in
    // the entity snapshot list, so currentValid alone excludes our own face.
    live = mode == 1 && (cent->currentValid || (clientNum == cg.predictedPlayerState.clientNum &&
        cg.predictedPlayerState.persistant[PERS_TEAM] != TEAM_SPECTATOR)) &&
        cent->ghoul2 && cent->currentState.eType == ET_PLAYER;
    if (live) {
        // Compress look angles to keep the face readable even while spinning.
        yaw = ST_PortraitClamp(AngleSubtract(cent->lerpAngles[YAW], cent->pe.legs.yawAngle), -50, 50) * .35f;
        pitch = ST_PortraitClamp(AngleNormalize180(cent->lerpAngles[PITCH]), -45, 45) * .25f;
        yaw += 2.0f * sinf(cg.time * .0012f + clientNum);
        pitch += sinf(cg.time * .0017f + clientNum);
        if (st_portraitDamage.integer) {
            pain = clientNum == cg.clientNum ? cg.damageTime : cent->pe.painTime;
            elapsed = cg.time - pain;
            if (pain > 0 && elapsed >= 0 && elapsed < 450) kick = 1.0f - elapsed / 450.0f;
        }
    }
    blend = ST_PortraitClamp((cg.time - st_portrait.time) / 120.0f, 0, 1);
    st_portrait.yaw += (yaw - st_portrait.yaw) * blend;
    st_portrait.pitch += (pitch - st_portrait.pitch) * blend;
    st_portrait.time = cg.time;
    st_portrait.kick = kick;
    if (mode == 1) {
        angles[YAW] += st_portrait.yaw;
        angles[PITCH] = st_portrait.pitch - kick * 7;
        angles[ROLL] = kick * 8;
        ST_PortraitFace(cent, ci, live);
    }
    memset(&ent, 0, sizeof(ent));
    memset(&rd, 0, sizeof(rd));
    if (!trap->G2API_GetBoltMatrix(st_portrait.model, 0, st_portrait.headBolt, &matrix,
            angles, zero, cg.time, cgs.gameModels, scale)) return qfalse;
    // Anchor on the cranium, not the animated body's origin; attacks cannot
    // drag the portrait off-screen. Leave room for hoods and long hair.
    ent.origin[0] = st_portrait.distance - matrix.matrix[0][3];
    ent.origin[1] = -matrix.matrix[1][3];
    ent.origin[2] = -matrix.matrix[2][3] - st_portrait.offset;
    AnglesToAxis(angles, ent.axis);
    VectorCopy(scale, ent.modelScale);
    ent.ghoul2 = st_portrait.model;
    ent.radius = 100;
    ent.customSkin = ci->torsoSkin;
    ent.renderfx = RF_NOSHADOW | RF_MINLIGHT;
    ent.shaderRGBA[0] = ent.shaderRGBA[1] = ent.shaderRGBA[2] = ent.shaderRGBA[3] = 255;
    rd.rdflags = RDF_NOWORLDMODEL | RDF_NOFOG;
    AxisClear(rd.viewaxis);
    rd.fov_x = rd.fov_y = 30;
    x *= cgs.screenXScale; w *= cgs.screenXScale;
    y *= cgs.screenYScale; h *= cgs.screenYScale;
    rd.x = (int)x; rd.y = (int)y; rd.width = (int)w; rd.height = (int)h;
    rd.time = cg.time;
    trap->R_ClearScene();
    trap->R_AddRefEntityToScene(&ent);
    trap->R_AddLightToScene(light, 200, 1.0f, .93f, .85f);
    trap->R_RenderScene(&rd);
    return qtrue;
}

static float ST_DrawPortrait(float y) {
    const char *label;
    int client, mode = st_portraitMode.integer;
    float h, w, x, textScale;
    clientInfo_t *ci;
    if (!cg.snap || mode <= 0 || !cg_drawEnemyInfo.integer) {
        ST_PortraitClear();
        return y;
    }
    if (st_portraitTarget.integer == 0 &&
        (cgs.gametype >= GT_TEAM || cgs.gametype == GT_DUEL || cgs.gametype == GT_POWERDUEL) &&
        cg.scoresRequestTime + 5000 < cg.time) {
        cg.scoresRequestTime = cg.time;
        trap->SendClientCommand("score");
    }
    client = ST_PortraitTarget(&label);
    if (!ST_PortraitClient(client)) { ST_PortraitClear(); return y; }
    ci = &cgs.clientinfo[client];
    h = ST_PortraitClamp(st_portraitSize.value, 48, 144);
    w = h * cgs.screenYScale / cgs.screenXScale;
    x = 630 - w;
    y += 5;
    if (!ST_PortraitRender(client, x, y, w, h, mode == 2 ? 2 : 1) && ci->modelIcon)
        CG_DrawPic(x, y, w, h, ci->modelIcon); // Unsupported custom head hierarchy.
    y += h;
    textScale = .8f;
    if (CG_Text_Width(ci->name, textScale, FONT_SMALL2) > 200)
        textScale *= 200.0f / CG_Text_Width(ci->name, textScale, FONT_SMALL2);
    CG_Text_Paint(630 - CG_Text_Width(ci->name, textScale, FONT_SMALL2), y,
        textScale, colorWhite, ci->name, 0, 0, 0, FONT_SMALL2);
    y += 13;
    CG_Text_Paint(630 - CG_Text_Width(label, .7f, FONT_SMALL2), y,
        .7f, colorWhite, label, 0, 0, 0, FONT_SMALL2);
    if (cgs.gametype == GT_DUEL && client == ST_PortraitOpponent()) {
        const char *score = va("%i/%i", ci->score, cgs.fraglimit);
        y += 13;
        CG_Text_Paint(630 - CG_Text_Width(score, .7f, FONT_SMALL2), y,
            .7f, colorWhite, score, 0, 0, 0, FONT_SMALL2);
    }
    if (cgs.showDuelHealths >= 2 && client == ST_PortraitOpponent()) {
        int slot = client == cgs.duelist1 ? 1 : client == cgs.duelist2 ? 2 : 0;
        if (slot) { y += 13; CG_DrawDuelistHealth(630 - w, y, w, 8, slot); }
    }
    return y + 20;
}
