// Test-only hooks, never included in a production build.
void ST_PhotoQA_f(void) {
    if (!Q_stricmp(CG_Argv(1),"input")) {
        ST_PhotoKey(atoi(CG_Argv(2)), atoi(CG_Argv(3)) ? qtrue : qfalse);
    } else if (!Q_stricmp(CG_Argv(1),"mouse")) {
        ST_PhotoMouse(atoi(CG_Argv(2)),atoi(CG_Argv(3)));
    }
    trap->Print("PHOTO_QA active=%d detached=%d solo=%d frozen=%d time=%d snap=%d origin=%.2f,%.2f,%.2f angles=%.2f,%.2f,%.2f fov=%.2f hud=%d streamer=%d catcher=%d pending=%d\n",
        stPhoto.active,stPhoto.detached,ST_PhotoInt("st_photoSolo"),ST_PhotoInt("st_photoFrozen"),cg.time,
        cg.snap ? cg.snap->serverTime : -1,cg.refdef.vieworg[0],cg.refdef.vieworg[1],cg.refdef.vieworg[2],
        cg.refdef.viewangles[0],cg.refdef.viewangles[1],cg.refdef.viewangles[2],cg.refdef.fov_x,
        cg_draw2D.integer,st_streamerMode.integer,trap->Key_GetCatcher(),stPhoto.captureFrames);
}
