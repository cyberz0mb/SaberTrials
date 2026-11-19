/* Test-only state probe, excluded from production preparation. */
static void ST_CGameQA(void) {
 static int previous;char value[32];int probe,i;
 trap->Cvar_VariableStringBuffer("st_staffQAProbe",value,sizeof(value));probe=atoi(value);
 if(!probe||probe==previous)return;previous=probe;
 Com_Printf("STAFF_VIEW mode=%d pm=%d photo=%d x=%.2f y=%.2f z=%.2f sx=%.2f sy=%.2f sz=%.2f\n",cg.predictedPlayerState.stats[15],cg.predictedPlayerState.pm_type,ST_PhotoActive(),cg.predictedPlayerState.origin[0],cg.predictedPlayerState.origin[1],cg.predictedPlayerState.origin[2],cg.snap->ps.origin[0],cg.snap->ps.origin[1],cg.snap->ps.origin[2]);
 for(i=0;i<3;i++)Com_Printf("STAFF_VISIBLE slot=%d valid=%d flags=%d\n",i,cg_entities[i].currentValid,cg_entities[i].currentState.eFlags);
}
