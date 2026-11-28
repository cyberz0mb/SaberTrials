"""Apply the JA+ client protocol to the Windows client and its optional cgame."""
from pathlib import Path
import shutil

from full_client_ui import change

FILES = Path(__file__).resolve().parents[1] / "development-source/compatibility"


def patch_engine(tree):
    client=tree/"codemp/client"
    shutil.copyfile(FILES/"ja_identity.h",client/"ja_identity.h")
    header=client/"client.h"
    mark="void CL_PersonalStatus();"
    change(header,mark,mark+"\nbool CL_JAConnection();\nbool JA_ActionsActive();\nbool JA_RGBAllowed();\nbool JA_HookPressAllowed();\nvoid JA_ClearHook();")
    main=client/"cl_main.cpp"
    mark='#include "outgoing_chat.inc"'
    change(main,mark,mark+'\n#include "ja_client.inc"')
    change(main,"\tCL_EmotesInit();","\tCL_EmotesInit();\n    JA_Init();")
    mark="void CL_Disconnect( qboolean showMainMenu ) {"
    change(main,mark,mark+"\n    JA_ClearHook();")
    mark="// send a reliable userinfo update if needed"
    change(main,mark,"JA_CheckUserinfo();\n    "+mark)
    mark=r'CL_AddReliableCommand( va("userinfo \"%s\"", Cvar_InfoString( CVAR_USERINFO ) ), qfalse );'
    change(main, mark,'''char info[MAX_INFO_STRING];
        Q_strncpyz(info,Cvar_InfoString(CVAR_USERINFO),sizeof(info));
        JA_Userinfo(info);
        CL_AddReliableCommand(va("userinfo \\"%s\\"",info),qfalse);''')
    cg=client/"cl_cgame.cpp"
    mark="cls.state = CA_PRIMED;"
    change(cg,mark,mark+"\n    if(CL_JAConnection())cvar_modifiedFlags|=CVAR_USERINFO;")
    inp=client/"cl_input.cpp"
    mark="void IN_Button12Down(void)"
    change(inp,mark,'''static kbutton_t jaHook;
static bool jaHookSent;
void JA_ClearHook(){Com_Memset(&jaHook,0,sizeof(jaHook));jaHookSent=false;}
void JA_PrintHookPackets(){Com_Printf("Grapple input included in an outgoing packet this session: %s.\\n",jaHookSent?"yes":"no");}
static void JA_HookDown(){if(JA_HookPressAllowed())IN_KeyDown(&jaHook);}
static void JA_HookUp(){IN_KeyUp(&jaHook);}
'''+mark)
    mark="if (cmd->buttons & BUTTON_FORCEPOWER)"
    change(inp, mark,'''if (jaHook.active || jaHook.wasPressed) {
        if(JA_ActionsActive()){cmd->buttons |= 1<<12; jaHook.wasPressed=qfalse;}
        else JA_ClearHook();
    }
    '''+mark)
    mark='{ "+button12", "Button 12", IN_Button12Down, NULL },'
    change(inp,mark,'{ "+st_jaGrapple", "JA+ grapple hook", JA_HookDown, NULL },\n    { "-st_jaGrapple", NULL, JA_HookUp, NULL },\n    '+mark)
    mark="MSG_WriteDeltaUsercmdKey (&buf, key, oldcmd, cmd);"
    change(inp,mark,mark+"\n            if(!jaHookSent && (cmd->buttons & (1<<12)) && JA_ActionsActive()) jaHookSent=true;")
    catalog=tree/"codemp/ui/st_controls_catalog.h"
    change(catalog,"int restricted;} stcAction_t;","int restricted,jaOnly;} stcAction_t;")
    mark='{"Pause menu","togglemenu"'
    change(catalog,mark,'''{"JA+ grapple hook","+st_jaGrapple","Movement","Hold to pull on servers with grapple enabled",0,1},
 {"JA+ jetpack","st_jaJetpack","Movement","Toggle the jetpack when the server permits it",0,1},
 {"JA+ full Force duel","st_jaFullForceDuel","Combat","Challenge your target under the server's duel rules",0,1},
 '''+mark)
    controls=client/"cl_st_controls.inc"
    change(controls,"extern cvar_t *cvar_vars;","extern cvar_t *cvar_vars;\nextern void Com_WriteConfiguration(void);")
    mark='auto& a=stcActions[i];if((q->a==STC_SERVER)'
    change(controls,mark,'auto& a=stcActions[i];if(a.jaOnly && !JA_ActionsActive())continue;if((q->a==STC_SERVER)')
    mark='STC_Open();if(restart)Cbuf_ExecuteText'
    change(controls,mark,'if(JA_ActionsActive() && stcDraft.dirty())Com_WriteConfiguration();'+mark)


def patch_frontend(tree):
    ui=tree/"codemp/ui"
    controls=ui/"ui_st_controls.inc"
    change(controls,"Discard pending controls changes and return?","Apply your controls before leaving?")
    mark="else if(id==1700){int modal=scui.modal;"
    change(controls,mark,'''else if(id==1703 && scui.modal==1){
        r=SCUI_Call(STC_APPLY,0,0,0,NULL,NULL);
        SCUI_Status(r);
        if(r.status>0){scui.modal=0;SCUI_Close();}
    }
    '''+mark)
    modals=ui/"ui_st_controls_modals.inc"
    change(modals,'"DISCARD PENDING EDITS?"','scui.modal==1?"UNSAVED CONTROLS":"DISCARD PENDING EDITS?"')
    mark='else SCUI_Button(400,378,172,25,scui.modal==8?'
    change(modals,mark,'''else if(scui.modal==1){
        SCUI_Button(240,378,120,25,"Discard",1700,0,0,qfalse);
        SCUI_Button(371,378,201,25,"Apply and return",1703,0,0,qtrue);
    }'''+mark)
    # The external game's approved saber materials are available to the UI.
    # Use vertex-tinted stock art when original JA+ effects are absent.
    crystal_draw=ui/"st_crystal_blade.inc"
    mark='const qhandle_t core = trap->R_RegisterShaderNoMip(coreShader);\n\tconst qhandle_t glow = trap->R_RegisterShaderNoMip("gfx/st_crystals/rgbGlow");'
    change(crystal_draw,mark,'''qhandle_t core,glow;
    if (ST_IsPersonalFrontend()) {
        core=trap->R_RegisterShaderNoMip("gfx/effects/sabers/RGBLine");
        glow=trap->R_RegisterShaderNoMip("gfx/effects/sabers/RGBGlow");
        if(!core)core=trap->R_RegisterShaderNoMip("gfx/misc/bline_w");
        if(!glow)glow=trap->R_RegisterShaderNoMip("gfx/effects/whiteGlow");
    } else {
        core=trap->R_RegisterShaderNoMip(coreShader);
        glow=trap->R_RegisterShaderNoMip("gfx/st_crystals/rgbGlow");
    }''')
    bench=ui/"ui_st_workbench.inc"
    mark="static int SWB_FamilyIndex()"
    change(bench,mark,'''// Ask the engine about the current connection, including advertised RGB restrictions.
static bool SWB_JA(bool rgb=false) {
    if(!ST_IsPersonalFrontend())return false;
    static int frame=-1;
    static stcReply_t reply={};
    if(frame!=uiInfo.uiDC.realTime){
        stcRequest_t request={};request.op=1200;reply={};
        trap->Controls(&request,&reply);
        frame=uiInfo.uiDC.realTime;
    }
    return rgb?reply.b:reply.a;
}
static const char *SWB_JAStyle(int slot){return slot?"ui_stJaStyle2":"ui_stJaStyle1";}
'''+mark)
    mark="stCrystalDrafts[0], stCrystalDrafts[1], ST_WHITE_CORE_DRAFT"
    change(bench,mark,mark+',"ui_stJaStyle1","ui_stJaStyle2"')
    mark="ST_CrystalParse(saved, colors);"
    change(bench,mark,mark+'''
        if(SWB_JA()) {
            int savedRGB=SWB_JA(true)?(int)trap->Cvar_VariableValue(saber?"st_jaRGB2":"st_jaRGB1"):ST_CRYSTAL_DEFAULT;
            std::fill(colors,colors+MAX_BLADES,savedRGB);
            trap->Cvar_Set(SWB_JAStyle(saber),va("%d",(int)trap->Cvar_VariableValue(saber?"st_jaStyle2":"st_jaStyle1")));
        }''')
    mark="return ST_IsPersonalFrontend() && (action==SWB_Hand"
    change(bench,mark,'''if(SWB_JA(true) && (action==SWB_Channel || action==SWB_Hex || action==SWB_ResetRgb ||
        action==SWB_WhiteCore || (action==SWB_Color && value==6)))return false;
    '''+mark)
    mark="if(SWB_Locked(control.action,control.value)){UI_RequiresTrials();return;}"
    change(bench,mark,'''if(SWB_Locked(control.action,control.value)){
        if(SWB_JA() && !SWB_JA(true) && (control.action==SWB_Channel || control.action==SWB_Hex ||
            control.action==SWB_ResetRgb || control.action==SWB_WhiteCore || (control.action==SWB_Color && control.value==6)))
            UI_PersonalNotice("RGB sabers are disabled by this JA+ server.");
        else UI_RequiresTrials();
        return;
    }''')
    mark="UI_UpdateSaberCvars();\n\t\tif(!ST_IsPersonalFrontend())"
    change(bench,mark,'''UI_UpdateSaberCvars();
        if(SWB_JA(true))for(int i=0;i<2;++i){
            int colors[MAX_BLADES];
            ST_CrystalParse(UI_Cvar_VariableString(stCrystalDrafts[i]),colors);
            trap->Cvar_Set(i?"st_jaRGB2":"st_jaRGB1",va("%d",colors[0]));
            trap->Cvar_Set(i?"st_jaStyle2":"st_jaStyle1",UI_Cvar_VariableString(SWB_JAStyle(i)));
        }
        if(!ST_IsPersonalFrontend())''')
    mark="case SWB_WhiteCore:"
    change(bench,mark,mark+'''
        if(SWB_JA(true)){
            int style=(int)trap->Cvar_VariableValue(SWB_JAStyle(swb.second));
            trap->Cvar_Set(SWB_JAStyle(swb.second),va("%d",style<6 || style>=10?6:style+1));
            SWB_StoreRgb(SWB_CurrentRgb(),true);
            break;
        }''')
    crystal=ui/"ui_st_crystal_controls.inc"
    mark="if(ST_IsPersonalFrontend()){UI_RequiresTrials();return;}"
    change(crystal,mark,'''if(ST_IsPersonalFrontend() && !SWB_JA(true)){
        if(SWB_JA())UI_PersonalNotice("RGB sabers are disabled by this JA+ server.");
        else UI_RequiresTrials();
        return;
    }''')
    change(crystal,"colors[swb.blade] = rgb;","if(SWB_JA())std::fill(colors,colors+MAX_BLADES,rgb);\n    else colors[swb.blade]=rgb;")
    change(crystal,"if (updateFallback && swb.blade == 0 && rgb > 0)","if (updateFallback && !SWB_JA() && swb.blade == 0 && rgb > 0)")
    mark="const bool whiteCore = trap->Cvar_VariableValue(ST_WHITE_CORE_DRAFT) != 0;"
    change(crystal,mark,'''if(SWB_JA()){
        static const char *styles[]={"Normal","Flame","Electric","Flame 2","Electric 2"};
        int index=std::max(0,std::min(4,(int)trap->Cvar_VariableValue(SWB_JAStyle(swb.second))-6));
        SWB_Button({437,391,177,23},va("JA+ blade: %s",styles[index]),SWB_WhiteCore);
        return;
    }
    '''+mark)
    mark="if (count > 1) {"
    change(crystal,mark,"if (count > 1 && !SWB_JA()) {")


def patch_cgame(source, target):
    # Keep the bundled base cgame and its build tree pristine.
    if not target.exists():
        shutil.copytree(source, target)
    cg = target / "codemp/cgame"
    for name in ["cg_local.h", "cg_players.c", "cg_ents.c", "cg_main.c","cg_servercmds.c","cg_consolecmds.c"]:
        shutil.copyfile(source / "codemp/cgame" / name, cg / name)
    for name in ["ja_render.inc", "ja_hook.inc","ja_identity.h"]:
        shutil.copyfile(FILES / name, cg / name)
    commands=cg/"cg_consolecmds.c"
    mark="static consoleCommand_t\tcommands[] = {"
    change(commands,mark,'''static void JA_LightReport(void) {
        vec3_t point,ambient,direct,direction;
        if(!cg.snap || !cgs.jaSession)return;
        VectorCopy(cg.snap->ps.origin,point);
        if(trap->R_LightForPoint(point,ambient,direct,direction)) {
            trap->Print("JA+ lighting %s at %.0f %.0f %.0f: ambient %.1f %.1f %.1f, direct %.1f %.1f %.1f\\n",
                cgs.mapname,point[0],point[1],point[2],ambient[0],ambient[1],ambient[2],direct[0],direct[1],direct[2]);
        } else trap->Print("JA+ map has no entity lighting grid.\\n");
    }
    '''+mark+'\n    {"st_jaLight",JA_LightReport},')
    change(cg/"cg_local.h","int\t\t\t\ticolor1;", "int jaPacked[2];\n\tint\t\t\t\ticolor1;")
    mark="qhandle_t\tsaberBlurShader;"
    change(cg/"cg_local.h",mark,mark+"\n    qhandle_t jaGlow[5],jaLine[5],jaTrail[5],jaHook;")
    mark="qboolean\t\tjediVmerc;"
    change(cg/"cg_local.h",mark,mark+"\n    int jaSession,jaRGBAllowed;")
    parser=cg/"cg_servercmds.c"
    change(parser,'#include "cg_local.h"','#include "cg_local.h"\n#include "ja_identity.h"')
    mark='cgs.jediVmerc = atoi( Info_ValueForKey( info, "g_jediVmerc" ) );'
    change(parser,mark,mark+'''
    cgs.jaSession=JA_MatchesServer(info,CG_ConfigString(CS_SYSTEMINFO));
    cgs.jaRGBAllowed=cgs.jaSession && JA_ServerAllowsRGB(info);''')
    players=cg/"cg_players.c"
    change(players,'#include "cg_local.h"','#include "cg_local.h"\n#include "ja_render.inc"')
    mark="newInfo.icolor2 = atoi(v);"
    change(players,mark,mark+'''
    newInfo.jaPacked[0]=JA_ReadRGB(Info_ValueForKey(configstring,"c3"));
    newInfo.jaPacked[1]=JA_ReadRGB(Info_ValueForKey(configstring,"c4"));''')
    sig="void CG_DoSaber( vec3_t origin, vec3_t dir, float length, float lengthMax, float radius, saber_colors_t color, int rfx, qboolean doLight )"
    change(players,sig,"static "+sig.replace("CG_DoSaber","JA_DoSaber").replace("doLight )","doLight, int packed )"))
    mark="if (doLight)\n\t{\t// always add a light"
    change(players,mark,'''if (packed>=0 && (int)color>=6 && (int)color<=10) {
        glow=cgs.media.jaGlow[(int)color-6];
        blade=cgs.media.jaLine[(int)color-6];
    }
    '''+mark)
    mark="CG_RGBForSaberColor( color, rgb );"
    change(players,mark,mark+"\n        if(packed>=0)JA_Vector(packed,rgb,1.f/255);")
    start=players.read_text()
    mark="saber.shaderRGBA[0] = saber.shaderRGBA[1] = saber.shaderRGBA[2] = saber.shaderRGBA[3] = 0xff;"
    if start.count(mark)!=2: raise ValueError("Unexpected blade sections")
    players.write_text(start.replace(mark,mark+"\n    if(packed>=0)JA_Tint(packed,saber.shaderRGBA);"))
    mark="// CG_GetTagWorldPosition"
    change(players,mark,sig+" {\n    JA_DoSaber(origin,dir,length,lengthMax,radius,color,rfx,doLight,-1);\n}\n\n"+mark)
    mark="int scolor = 0;"
    change(players,mark,mark+"\n    int jaPacked=-1;")
    mark="scolor = client->icolor2;\n\t\t}\n\t}"
    change(players,mark,mark+"\n    if(cgs.jaRGBAllowed && cent->currentState.eType!=ET_NPC && scolor>=6 && scolor<=10) jaPacked=client->jaPacked[saberNum];")
    for color in ("RED","BLUE"):
        mark=f"scolor = SABER_{color};"
        change(players,mark,mark+"\n            jaPacked=-1;")
    mark="fx.mShader = cgs.media.saberBlurShader;\n\t\t\t\t\t\t\t}\n\t\t\t\t\t\t\tfx.mKillTime"
    change(players,mark,mark.replace(";",";"+'''
                                if(jaPacked>=0) {
                                    JA_Vector(jaPacked,rgb1,1.f);
                                    fx.mShader=cgs.media.jaTrail[scolor-6];
                                }''',1))
    mark="\n\tCG_DoSaber( org_, axis_[0]"
    change(players,mark,"\n\tJA_DoSaber( org_, axis_[0]")
    mark="(qboolean)(client->saber[saberNum].numBlades < 3 && !(client->saber[saberNum].saberFlags2&SFL2_NO_DLIGHT)) );"
    change(players,mark,mark.replace(")) );",")), jaPacked );"))
    mark="static void CG_DoSaberLight( saberInfo_t *saber )"
    change(players,mark,'''static int JA_HiltLight(const centity_t *cent,const clientInfo_t *ci,int slot) {
        int style=slot?ci->icolor2:ci->icolor1;
        if(!cgs.jaRGBAllowed || cent->currentState.eType==ET_NPC || style<6 || style>10)return -1;
        if(cgs.gametype>=GT_TEAM && cgs.gametype!=GT_SIEGE && !cgs.jediVmerc &&
            (ci->team==TEAM_RED || ci->team==TEAM_BLUE))return -1;
        return ci->jaPacked[slot];
    }
    static void CG_DoSaberLight( saberInfo_t *saber, int packed )''')
    mark="CG_RGBForSaberColor( saber->blade[i].color, rgbs[i] );"
    change(players,mark,mark+"\n            if(packed>=0)JA_Vector(packed,rgbs[i],1.f/255);")
    change(players,"CG_DoSaberLight( &client->saber[saberNum] );","CG_DoSaberLight( &client->saber[saberNum],jaPacked );")
    mark="CG_DoSaberLight( &ci->saber[l] );"
    original=players.read_text()
    if original.count(mark)!=2: raise ValueError("Expected attached and thrown hilt lighting")
    players.write_text(original.replace(mark,"CG_DoSaberLight( &ci->saber[l],JA_HiltLight(cent,ci,l) );"))
    main=cg/"cg_main.c"
    mark='trap->R_RegisterShader( "gfx/effects/sabers/saberBlur" );'
    change(main,mark,mark+'''
    // All assets go through the connected game's normal renderer/filesystem.
    for(int i=0;i<5;++i) {
        const char *glow=i==3?"gfx/effects/sabers/RGBGlow4":"gfx/effects/sabers/RGBGlow";
        cgs.media.jaGlow[i]=trap->R_RegisterShader(glow);
        cgs.media.jaLine[i]=trap->R_RegisterShader(i?va("gfx/effects/sabers/RGBcore%d",i+1):"gfx/effects/sabers/RGBLine");
        cgs.media.jaTrail[i]=(i>0 && i<4)?trap->R_RegisterShader(va("gfx/effects/sabers/RGBtrail%d",i+1)):0;
        if(!cgs.media.jaGlow[i])cgs.media.jaGlow[i]=trap->R_RegisterShader("gfx/effects/whiteGlow");
        if(!cgs.media.jaLine[i])cgs.media.jaLine[i]=trap->R_RegisterShader("gfx/misc/bline_w");
        if(!cgs.media.jaTrail[i])cgs.media.jaTrail[i]=cgs.media.saberBlurShader;
    }
    cgs.media.jaHook=trap->R_RegisterModel("models/items/grapple.md3");''')
    ents=cg/"cg_ents.c"
    mark="s1 = &cent->currentState;\n\tif ( s1->weapon > WP_NUM_WEAPONS"
    change(ents,'#include "cg_local.h"','#include "cg_local.h"\n#include "ja_hook.inc"')
    change(ents,mark,mark.replace("if ( s1", "if (cgs.jaSession && s1->weapon==WP_STUN_BATON) {JA_DrawHook(cent);return;}\n\tif ( s1"))
