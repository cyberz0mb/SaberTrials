"""Preference/replication foundation. The server gate stays off until combat is complete."""
def apply(source,change):
    change(source,'codemp/game/bg_public.h','#define\tEF2_HELD_BY_MONSTER',
           '#include "st_handedness.h"\n#define EF2_SABER_LEFT ST_HAND_LEFT_FLAG\n#define\tEF2_HELD_BY_MONSTER')
    change(source,'codemp/game/g_xcvar.h','XCVAR_DEF( bg_fighterAltControl,',
           'XCVAR_DEF( g_saberHandedness, "1", NULL, CVAR_SERVERINFO|CVAR_LATCH, qtrue )\nXCVAR_DEF( bg_fighterAltControl,')
    change(source,'codemp/game/g_local.h','char\t\tsaber1[MAX_QPATH], saber2[MAX_QPATH];',
           'char\t\tsaber1[MAX_QPATH], saber2[MAX_QPATH];\n int stHand; // active choice, latched at spawn')
    game='codemp/game/g_client.c'
    change(source,game,'qboolean G_SaberModelSetup(gentity_t *ent)', '''
static int G_STHandAtSpawn(gentity_t* ent,const char* userinfo) {
    const int request=ST_HandParse(Info_ValueForKey(userinfo,"saberHand"));
    const int clientOK=(ent->r.svFlags & SVF_BOT) ||
        !strcmp(Info_ValueForKey(userinfo,"st_handProtocol"),"1");
    int rigOK=0,bad=-1;
    if(request && g_saberHandedness.integer && clientOK && ent->ghoul2 &&
       trap->Cvar_VariableIntegerValue("st_mirrorRenderer")==1) {
        rigOK=ent->localAnimIndex>=0 && ent->localAnimIndex<=1 &&
            ST_DirectionValidateAnimationSet(bgAllAnims[ent->localAnimIndex].anims,MAX_TOTALANIMATIONS,&bad) &&
            trap->G2API_SetBoneAnim(ent->ghoul2,0,"model_root",0,1,
                BONE_ANIM_OVERRIDE_FREEZE|BONE_ANIM_MIRROR,1,level.time,-1,0) &&
            trap->G2API_AddBolt(ent->ghoul2,0,"*r_hand")>=0 &&
            trap->G2API_AddBolt(ent->ghoul2,0,"*l_hand")>=0;
    }
    return ST_HandAtSpawn(request,g_saberHandedness.integer,clientOK,rigOK);
}

qboolean G_SaberModelSetup(gentity_t *ent)''')
    change(source,game,'trap->G2API_SetBoltInfo(ent->client->weaponGhoul2[i], 0, 3+i);',
           'trap->G2API_SetBoltInfo(ent->client->weaponGhoul2[i], 0, ST_HandAttachment(i,ent->client->pers.stHand,1));')
    change(source,game,'trap->G2API_SetBoltInfo(ent->client->weaponGhoul2[i], 0, i);',
           'trap->G2API_SetBoltInfo(ent->client->weaponGhoul2[i], 0, ST_HandAttachment(i,ent->client->pers.stHand,0));')
    # The default instance is shared; set the destination copy, never mutate the template.
    change(source,game,'trap->G2API_CopySpecificGhoul2Model(g2SaberInstance, 0, ent->ghoul2, 1);',
           'trap->G2API_CopySpecificGhoul2Model(g2SaberInstance, 0, ent->ghoul2, 1);\n trap->G2API_SetBoltInfo(ent->ghoul2,1,ST_HandAttachment(0,ent->client->pers.stHand,0));')
    marker='trap->GetUserinfo( index, userinfo, sizeof( userinfo ) );'
    change(source,game,marker,marker+'''
    if(g_saberHandedness.integer) {
        char wantedModel[MAX_QPATH];
        Q_strncpyz(wantedModel,Info_ValueForKey(userinfo,"model"),sizeof(wantedModel));
        if(Q_stricmp(wantedModel,client->modelname)) {
            Q_strncpyz(client->modelname,wantedModel,sizeof(client->modelname));
            SetupGameGhoul2Model(ent,wantedModel,NULL);
            changedSaber=qtrue;
        }
    }
    {
        const int hand=G_STHandAtSpawn(ent,userinfo);
        if(hand!=client->pers.stHand){client->pers.stHand=hand;changedSaber=qtrue;}
    }
''')
    change(source,game,'client->pers = saved;',
           'client->pers = saved;\n client->ps.eFlags2=ST_HandSetFlag(client->ps.eFlags2,client->pers.stHand);\n client->torsoAnimExecute=client->legsAnimExecute=-1;')
    marker='Q_strcat( buf, sizeof( buf ), va( "st2\\\\%s\\\\", client->pers.saber2 ) );'
    change(source,game,marker,marker+'\n Q_strcat(buf,sizeof(buf),va("sh\\\\%d\\\\",client->pers.stHand));')
    marker='\tvalue = Info_ValueForKey( userinfo, "ja_guid" );'
    change(source,game,marker,'''    if(!isBot && g_saberHandedness.integer &&
        strcmp(Info_ValueForKey(userinfo,"st_handProtocol"),"1"))
        return "This server requires the updated Saber Trials client for saber handedness.";
'''+marker)
    # Actual server-side rigs are required for attachment-aware lock solving.
    change(source,game,'if (d_perPlayerGhoul2.integer || ent->s.number >= MAX_CLIENTS ||',
           'if (d_perPlayerGhoul2.integer || g_saberHandedness.integer || ent->s.number >= MAX_CLIENTS ||')
    change(source,game,'if ( d_perPlayerGhoul2.integer&& Q_stricmp( model, client->modelname ) )',
           'if ( (d_perPlayerGhoul2.integer || g_saberHandedness.integer) && Q_stricmp( model, client->modelname ) )')
    change(source,game,'if ( d_perPlayerGhoul2.integer && Q_stricmp( model, client->modelname ) )',
           'if ( (d_perPlayerGhoul2.integer || g_saberHandedness.integer) && Q_stricmp( model, client->modelname ) )')
    marker='Q_strncpyz( model, Info_ValueForKey( userinfo, "model" ), sizeof( model ) );'
    # Only the userinfo handler has this exact local model declaration.
    text=(source/game).read_text();start=text.index('qboolean ClientUserinfoChanged(');end=text.index('/*',text.index('\n\treturn qtrue;',start))
    part=text[start:end]
    if part.count(marker)!=1:raise RuntimeError('Handedness model deferral hook changed')
    part=part.replace(marker,marker+'''
    if(g_saberHandedness.integer && client->pers.stHand && ent->health>0 &&
       client->pers.connected==CON_CONNECTED && client->modelname[0] &&
       Q_stricmp(model,client->modelname))
        Q_strncpyz(model,client->modelname,sizeof(model)); // selected model applies next spawn
''')
    part=part.replace('char *modelname = Info_ValueForKey( userinfo, "model" );','char *modelname = model;')
    (source/game).write_text(text[:start]+part+text[end:],newline='\n')
    cg='codemp/cgame/cg_players.c'
    change(source,'codemp/cgame/cg_local.h','saberInfo_t\t\tsaber[MAX_SABERS];',
           'saberInfo_t\t\tsaber[MAX_SABERS];\n int stHand;')
    change(source,cg,'memset( &newInfo, 0, sizeof( newInfo ) );',
           'memset( &newInfo, 0, sizeof( newInfo ) );\n newInfo.stHand=ST_HandParse(Info_ValueForKey(configstring,"sh"));')
    # A mismatched local custom rig uses the engine's ordinary default-model
    # fallback, retaining authoritative hand/pose instead of a wrong-side blade.
    marker='\tci->bolt_motion = trap->G2API_AddBolt(ci->ghoul2Model, 0, "Motion");'
    change(source,cg,marker,marker+'''
    if(ci->stHand && (!trap->G2API_SetBoneAnim(ci->ghoul2Model,0,"model_root",0,1,
       BONE_ANIM_OVERRIDE_FREEZE|BONE_ANIM_MIRROR,1,cg.time,-1,0) ||
       ci->bolt_rhand<0 || ci->bolt_lhand<0)) {
        trap->Print("Saber Trials: this local character rig cannot use left-handed poses; loading the default model.\\n");
        return qfalse;
    }
''',2)
    change(source,cg,'trap->G2API_SetBoltInfo(ci->ghoul2Weapons[saberNum], 0, 3+saberNum);',
           'trap->G2API_SetBoltInfo(ci->ghoul2Weapons[saberNum], 0, ST_HandAttachment(saberNum,ci->stHand,1));')
    change(source,cg,'trap->G2API_SetBoltInfo(ci->ghoul2Weapons[saberNum], 0, saberNum);',
           'trap->G2API_SetBoltInfo(ci->ghoul2Weapons[saberNum], 0, ST_HandAttachment(saberNum,ci->stHand,0));')
    change(source,cg,'if ( !Q_stricmp( ci->modelName, match->modelName )',
           'if ( ci->stHand==match->stHand && !Q_stricmp( ci->modelName, match->modelName )')
    change(source,cg,'Q_stricmp( ci->modelName, match->modelName ) ||',
           'ci->stHand!=match->stHand || Q_stricmp( ci->modelName, match->modelName ) ||')
    # A same-hilt hand change must rebuild both templates, not copy stale bolts.
    for key in ('saberName','saber2Name'):
        change(source,cg,f'if (v && Q_stricmp(v, ci->{key}))',
               f'if (v && (newInfo.stHand!=ci->stHand || Q_stricmp(v, ci->{key})))')
    change(source,cg,'//ah well, just stick it over the right hand right now.\n\t\t\t\t\ttrap->G2API_GetBoltMatrix(cent->ghoul2, 0, ci->bolt_rhand,',
           '// Use the actual primary hilt, including left-hand and wrist attachments.\n\t\t\t\t\ttrap->G2API_GetBoltMatrix(cent->ghoul2, 1, 0,')
    change(source,cg,'((cent->torsoBolt & RARMBIT) || (cent->torsoBolt & RHANDBIT) || (cent->torsoBolt & WAISTBIT)) && g2HasWeapon',
           '(cent->torsoBolt & (WAISTBIT | ((cent->currentState.weapon==WP_SABER && ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum)) ? (1 << (G2_MODELPART_LARM-10)) : (RARMBIT|RHANDBIT)))) && g2HasWeapon')
    change(source,cg,'\tif (!cent->trickAlphaTime || (cg.time - cent->trickAlphaTime) > 1000)',
           '''    if(cent->ghoul2 && cent->currentState.weapon==WP_SABER &&
       (cent->torsoBolt & (WAISTBIT | (ST_HandEffective(cent->currentState.eFlags2,cent->currentState.m_iVehicleNum) ? (RARMBIT|RHANDBIT) : (1 << (G2_MODELPART_LARM-10))))) &&
       trap->G2API_HasGhoul2ModelOnIndex(&(cent->ghoul2),2))
        trap->G2API_RemoveGhoul2Model(&(cent->ghoul2),2);
\tif (!cent->trickAlphaTime || (cg.time - cent->trickAlphaTime) > 1000)''')
    ents='codemp/cgame/cg_ents.c'
    old='if (cent->currentState.modelGhoul2 == G2_MODELPART_RARM || cent->currentState.modelGhoul2 == G2_MODELPART_RHAND || cent->currentState.modelGhoul2 == G2_MODELPART_WAIST)'
    change(source,ents,old,'''if (cent->currentState.modelGhoul2 == G2_MODELPART_WAIST ||
                ((clEnt->currentState.weapon==WP_SABER && ST_HandEffective(clEnt->currentState.eFlags2,clEnt->currentState.m_iVehicleNum)) ?
                 cent->currentState.modelGhoul2==G2_MODELPART_LARM :
                 (cent->currentState.modelGhoul2==G2_MODELPART_RARM || cent->currentState.modelGhoul2==G2_MODELPART_RHAND)))''')
    change(source,ents,'\t\t\tclEnt->torsoBolt |= limbBit;', '''            if(clEnt->currentState.weapon==WP_SABER &&
                (cent->currentState.modelGhoul2==G2_MODELPART_WAIST ||
                (ST_HandEffective(clEnt->currentState.eFlags2,clEnt->currentState.m_iVehicleNum) ?
                 (cent->currentState.modelGhoul2==G2_MODELPART_RARM || cent->currentState.modelGhoul2==G2_MODELPART_RHAND) :
                 cent->currentState.modelGhoul2==G2_MODELPART_LARM)) &&
                trap->G2API_HasGhoul2ModelOnIndex(&(clEnt->ghoul2),2))
                trap->G2API_RemoveGhoul2Model(&(clEnt->ghoul2),2);
\t\t\tclEnt->torsoBolt |= limbBit;''')
    ui='codemp/ui/ui_main.c'
    change(source,'codemp/ui/ui_xcvar.h','XCVAR_DEF( capturelimit,',
           'XCVAR_DEF( saberHand, "0", NULL, CVAR_ARCHIVE|CVAR_USERINFO )\n'
           'XCVAR_DEF( st_handProtocol, "0", NULL, CVAR_USERINFO|CVAR_ROM )\n'
           'XCVAR_DEF( ui_saberHand, "0", NULL, CVAR_INTERNAL )\nXCVAR_DEF( capturelimit,')
    change(source,ui,'static void UI_UpdateSaberCvars ( void )\n{',
           'static void UI_UpdateSaberCvars ( void )\n{\n trap->Cvar_Set("saberHand",trap->Cvar_VariableValue("ui_saberHand")==1?"1":"0");')
    change(source,ui,'static void UI_GetSaberCvars ( void )\n{',
           'static void UI_GetSaberCvars ( void )\n{\n trap->Cvar_Set("ui_saberHand",trap->Cvar_VariableValue("saberHand")==1?"1":"0");')
    change(source,ui,'\tUI_UpdateCvars();',
           '\tUI_UpdateCvars();\n trap->Cvar_Set("st_handProtocol",trap->Cvar_VariableValue("st_mirrorRenderer")==1?"1":"0");')
    # Capability belongs to the renderer that actually evaluates Ghoul2 poses.
    change(source,'codemp/client/cl_main.cpp','void CL_InitRef( void ) {',
           'void CL_InitRef( void ) {\n Cvar_Get("st_handProtocol","0",CVAR_ROM|CVAR_USERINFO);\n Cvar_Set("st_handProtocol","0");\n Cvar_Get("st_mirrorRenderer","0",CVAR_ROM);\n Cvar_Set("st_mirrorRenderer","0");')
    for renderer in ('rd-vanilla','rd-rend2'):
        change(source,f'codemp/{renderer}/tr_init.cpp','void R_Init( void ) {',
               'void R_Init( void ) {\n ri.Cvar_Get("st_mirrorRenderer","0",CVAR_ROM,"Saber Trials pose capability");\n ri.Cvar_Set("st_mirrorRenderer","1");\n ri.Cvar_Set("st_handProtocol","1");')
        change(source,f'codemp/{renderer}/tr_init.cpp','void RE_Shutdown( qboolean destroyWindow, qboolean restarting ) {',
               'void RE_Shutdown( qboolean destroyWindow, qboolean restarting ) {\n ri.Cvar_Set("st_mirrorRenderer","0");')
    path=source/'codemp/rd-dedicated/G2_API.cpp';s=path.read_text()
    start=s.index('int G2API_InitGhoul2Model(');body=s.index('{',start)+1
    s=s[:body]+'\n Cvar_Get("st_mirrorRenderer","0",CVAR_ROM);\n Cvar_Set("st_mirrorRenderer","1");'+s[body:]
    path.write_text(s,newline='\n')
