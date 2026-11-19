#include "qcommon/st_emotes.h"

static struct {
    bool editing = false, wheel = false, previewOk = false;
    int group = 0, slot = 0, selected = 0, scroll = 0, focus = 0, field = 0;
    void* previewModel = nullptr;
    float x = 0, y = 0;
    std::string input, status;
    std::vector<stemote::Clip> clips;
    std::vector<SPHit> hits;
} emui;

static bool EM_WheelOpen() { return trap->Cvar_VariableValue("st_emoteWheelOpen") != 0; }

static void EM_Init() {
    const auto stock = stemote::builtins();
    for (int group = 0; group < stemote::groups; ++group) {
        trap->Cvar_Register(nullptr,stemote::nameVar(group).c_str(),va("Group %d",group+1),CVAR_ARCHIVE);
        for (int slot = 0; slot < stemote::slots; ++slot) {
            const char* id = group == 0 && slot < int(stock.size()) ? stock[slot].id.c_str() : "";
            trap->Cvar_Register(nullptr,stemote::slotVar(group,slot).c_str(),id,CVAR_ARCHIVE);
        }
    }
}

static std::string EM_Name() { return SPUI_Var(stemote::nameVar(emui.group).c_str()); }

static std::string EM_Slot(int slot) {
    return SPUI_Var(stemote::slotVar(emui.group,slot).c_str());
}

static bool EM_Available(const stemote::Clip& clip) {
    char offer[MAX_STRING_CHARS] = {};
    trap->GetConfigString(stemote::catalogString,offer,sizeof(offer));
    if (*offer) {
        char settings[MAX_INFO_STRING] = {};
        trap->GetConfigString(CS_SYSTEMINFO,settings,sizeof(settings));
        return stemote::offered(offer,clip) && (!clip.signature || !atoi(Info_ValueForKey(settings,"sv_pure")));
    }
    char info[MAX_INFO_STRING] = {};
    trap->GetConfigString(CS_SERVERINFO,info,sizeof(info));
    const int mode = atoi(Info_ValueForKey(info,"g_gametype"));
    return clip.id == "taunt" || (clip.stock >= 0 && (mode == GT_DUEL || mode == GT_POWERDUEL));
}

static void EM_WheelStart() {
    emui.wheel = true;
    emui.clips = stemote::catalog(trap->Cvar_VariableStringBuffer);
    emui.group = std::max(0,std::min(stemote::groups-1,int(trap->Cvar_VariableValue("st_emoteGroup"))));
    emui.slot = -1;
    emui.x = emui.y = 0;
}

static int EM_Sector(float x,float y) {
    if (x*x+y*y < 350) return -1;
    return int(std::floor(std::atan2(x,-y)*4/3.14159265f+8.5f)) % stemote::slots;
}

static void EM_WheelMove(int dx,int dy) {
    if (!emui.wheel) EM_WheelStart();
    const float aspect = uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
    emui.x += dx/std::max(.6f,aspect);
    emui.y += dy;
    const float radius = std::sqrt(emui.x*emui.x+emui.y*emui.y);
    if (radius > 132) {
        emui.x *= 132/radius;
        emui.y *= 132/radius;
    }
    emui.slot = EM_Sector(emui.x,emui.y);
}

static void EM_WheelKey(int key,qboolean down) {
    if (!down) return;
    if (!emui.wheel || key == A_HOME) EM_WheelStart();
    if (key == A_ENTER && emui.slot >= 0) {
        const auto* clip = stemote::find(emui.clips,EM_Slot(emui.slot));
        if (trap->Cvar_VariableValue("developer")) Com_Printf("ST_EMOTE_CONFIRM %d %s %d\n",emui.slot,
            clip?clip->id.c_str():"(empty)",clip&&EM_Available(*clip));
        if (clip && EM_Available(*clip)) trap->Cvar_Set("st_emoteSelection",clip->id.c_str());
    } else if (key >= A_1 && key <= A_8) emui.slot = key-A_1;
    else if (key == A_MWHEELUP || key == A_JOY9 || key == A_MWHEELDOWN || key == A_JOY10) {
        const int step = key == A_MWHEELUP || key == A_JOY9 ? -1 : 1;
        emui.group = (emui.group+stemote::groups+step)%stemote::groups;
        trap->Cvar_Set("st_emoteGroup",va("%d",emui.group));
        emui.slot = -1;
        emui.x = emui.y = 0;
    } else if (key == A_CURSOR_UP || key == A_JOY11) emui.slot = 0;
    else if (key == A_CURSOR_RIGHT || key == A_JOY14) emui.slot = 2;
    else if (key == A_CURSOR_DOWN || key == A_JOY12) emui.slot = 4;
    else if (key == A_CURSOR_LEFT || key == A_JOY13) emui.slot = 6;
}

static void EM_WheelDraw() {
    if (!emui.wheel) EM_WheelStart();
    const float aspect = uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
    constexpr float centerX = 320, centerY = 181, imageSize = 246;
    const auto art = [&](const char* name,float x,float y,float width,float height,const float* color=nullptr) {
        RUI_Image(name,x-width*aspect/2,y-height/2,width*aspect,height,color);
    };
    art("emote_face",centerX,centerY,imageSize,imageSize);
    if (emui.slot >= 0) art(va("emote_focus%d",emui.slot),centerX,centerY,imageSize,imageSize);
    if (RUI_Motion()) {
        std::vector<stmain::Point> rim;
        for (int i=0;i<=48;++i) {
            const float angle=i*6.2831853f/48;
            rim.push_back({centerX+std::sin(angle)*108*aspect,centerY-std::cos(angle)*108});
        }
        const float phase=stmain::phase(uiInfo.uiDC.realTime,true,5000);
        RUI_Light(rim,phase,ruCyan,3.1f);
        RUI_Light(rim,phase+.5f,ruCyan,3.1f);
    }
    const int emblem = trap->R_RegisterShaderNoMip("ui/assets/sabertrials/main/emblem");
    if (emblem) UI_DrawHandlePic(centerX-13*aspect,centerY-22,26*aspect,26,emblem);
    {
        const auto name = EM_Name();
        STML_Raw raw;
        SCUI_Centered(centerX-30*aspect,centerY+5,60*aspect,11,.46f,name.c_str(),scuText);
    }
    SCUI_Centered(centerX-22*aspect,centerY+17,44*aspect,10,.38f,va("%d / %d",emui.group+1,stemote::groups),scuGold);
    for (int i = 0; i < stemote::slots; ++i) {
        const float angle = i*3.14159265f/4;
        const float dx = std::sin(angle)*aspect, dy = -std::cos(angle);
        const float x = centerX+dx*75, y = centerY+dy*75;
        const auto id = EM_Slot(i);
        const auto* clip = stemote::find(emui.clips,id);
        const bool ready = clip && EM_Available(*clip);
        const bool selected = i == emui.slot;
        const char* icon = !clip ? "empty" : clip->stock<0 ? "gesture" : clip->id.c_str();
        const vec4_t tint={1,1,1,clip&&!ready?.45f:1.f};
        art(va("emote_%s",icon),x,y-6,23,23,tint);
        const char* label = clip ? clip->label.c_str() : id.empty() ? "Empty" : "Missing pack";
        if (clip) {
            STML_Raw raw;
            SCUI_Centered(x-23*aspect,y+6,46*aspect,12,.46f,label,ready?(selected?scuGold:scuText):scuMuted);
        } else SCUI_Centered(x-25*aspect,y+6,50*aspect,12,.43f,label,scuMuted);
        const float numberX=centerX+dx*109, numberY=centerY+dy*109;
        art("emote_number",numberX,numberY,20,17);
        SCUI_Centered(numberX-9*aspect,numberY-7,18*aspect,14,.50f,va("%d",i+1),scuGold);
    }
    if (emui.slot >= 0) {
        const auto id = EM_Slot(emui.slot);
        const auto* clip = stemote::find(emui.clips,id);
        if (clip && !EM_Available(*clip))
            SCUI_Centered(115,303,410,20,.49f,"Unavailable on this server",scuGold);
    }
}

static void EM_Button(float x,float y,float w,float h,const char* label,int id,int arg=0,bool selected=false) {
    const bool hover = SPUI_Over(x,y,w,h) || (!spui.mouse && emui.focus == int(emui.hits.size()));
    RUI_Control(x,y,w,h,"action",selected,hover);
    SCUI_Centered(x+2,y,w-4,h,.53f,label,selected||hover?scuCyan:scuText);
    emui.hits.push_back({x,y,w,h,id,arg});
}

static void EM_EditorOpen() {
    emui.editing = true;
    emui.clips = stemote::catalog(trap->Cvar_VariableStringBuffer);
    emui.group = emui.slot = emui.scroll = emui.selected = emui.field = emui.focus = 0;
    emui.previewOk = false;
    emui.previewModel = nullptr;
    emui.status.clear();
    spui.field = 0;
}

static void EM_CloseEditor() {
    emui.editing = false;
    if (auto* model = Menu_FindItemByName(Menu_GetFocused(),"st_profile_preview")) {
        if (model->typeData.model) model->typeData.model->rotationSpeed = spui.motion?100:0;
        if (model->ghoul2) {
            UI_ClearG2Pointer(model->ghoul2);
            trap->G2API_CleanGhoul2Models(&model->ghoul2);
        }
    }
    // Rebuild the existing profile preview so it restores its walking cycle.
    trap->Cvar_Set("ui_stProfilePreviewAvailable","0");
}

static void EM_Preview(bool restart = false) {
    auto* item = Menu_FindItemByName(Menu_GetFocused(),"st_profile_preview");
    void* model = item ? item->ghoul2 : nullptr;
    if (!restart && model == emui.previewModel) return;
    emui.previewModel = model;
    emui.previewOk = false;
    if (model) {
        const auto& clip = emui.clips[emui.selected];
        char gla[MAX_QPATH] = {};
        trap->G2API_GetGLAName(model,0,gla);
        if (stemote::sharedGla(gla)) {
            emui.previewOk = trap->G2API_SetBoneAnim(model,0,"model_root",clip.first,clip.first+clip.frames,
                BONE_ANIM_OVERRIDE_LOOP,clip.fps*.05f,uiInfo.uiDC.realTime,-1,0);
        }
    }
    emui.status = emui.previewOk ? "" : "Preview unavailable for this model";
}

static void EM_DrawEditor() {
    EM_Preview();
    emui.hits.clear();
    RUI_Shell();
    SCUI_Text(24,53,.89f,"Emotes",scuText);
    for (int group = 0; group < stemote::groups; ++group) {
        const auto label = SPUI_Var(stemote::nameVar(group).c_str());
        EM_Button(23+group*93,88,86,24,label.c_str(),1,group,group==emui.group);
    }
    EM_Button(491,88,125,24,"Rename group",2);
    RUI_Divider(22,121,596);
    SCUI_Text(23,132,.62f,"Emote library",scuText);
    const int shown = 8;
    for (int i = 0; i < shown && i+emui.scroll < int(emui.clips.size()); ++i) {
        const int index = i+emui.scroll;
        EM_Button(22,156+i*27,161,24,emui.clips[index].label.c_str(),3,index,index==emui.selected);
    }
    EM_Button(22,376,77,21,"Previous",9,-shown);
    EM_Button(106,376,77,21,"Next",9,shown);
    SCUI_Text(206,132,.62f,"Wheel slots",scuText);
    for (int i = 0; i < stemote::slots; ++i) {
        const auto id = EM_Slot(i);
        const auto* clip = stemote::find(emui.clips,id);
        EM_Button(204,156+i*27,234,24,va("%d    %s",i+1,clip?clip->label.c_str():id.empty()?"Empty":"Missing pack"),4,i,i==emui.slot);
    }
    EM_Button(204,376,115,21,"Assign to slot",5);
    EM_Button(326,376,112,21,"Clear slot",6);
    const auto& clip = emui.clips[emui.selected];
    SCUI_Centered(466,348,152,21,.58f,clip.label.c_str(),scuText);
    EM_Button(490,376,104,21,"Bind key",8);
    RUI_Divider(22,437,596);
    EM_Button(22,447,73,19,"Back",10);
    EM_Button(455,447,163,19,trap->Cvar_VariableValue("st_emoteWheelToggle")?
        "Wheel activation: Toggle":"Wheel activation: Hold",11);
    if (!emui.status.empty()) SCUI_Fit(105,450,340,.50f,emui.status.c_str(),scuGold);
    if (emui.field == 1) {
        const vec4_t shade = {0,0,0,.5f};
        UI_FillRect(0,0,640,480,shade);
        UI_FillRect(128,181,384,110,scuInk);
        RUI_Control(128,181,384,110,"panel",false,false);
        SCUI_Text(151,202,.62f,"Group name",scuText);
        UI_FillRect(150,226,333,25,scuPanel);
        SCUI_Border(150,226,333,25,scuCyan);
        { STML_Raw raw; SCUI_Fit(157,232,318,.59f,emui.input.c_str(),scuText); }
        SCUI_Text(151,259,.5f,"Enter to save. Esc to cancel.",scuMuted);
    }
}

static void EM_EditorAction(int id,int arg) {
    if (id == 1) { emui.group = arg; emui.slot = 0; }
    if (id == 2) { emui.field = 1; emui.input = EM_Name(); }
    if (id == 3) { emui.selected = arg; EM_Preview(true); }
    if (id == 4) emui.slot = arg;
    if (id == 5 || id == 6) trap->Cvar_Set(stemote::slotVar(emui.group,emui.slot).c_str(),id==5?emui.clips[emui.selected].id.c_str():"");
    if (id == 8) { emui.field = 2; emui.status = "Press an unassigned key or button. Esc cancels."; }
    if (id == 9) emui.scroll = std::max(0,std::min(std::max(0,int(emui.clips.size())-8),emui.scroll+arg));
    if (id == 10) EM_CloseEditor();
    if (id == 11) trap->Cvar_Set("st_emoteWheelToggle",trap->Cvar_VariableValue("st_emoteWheelToggle")?"0":"1");
}

static void EM_EditorKey(int key,qboolean down) {
    if (!down) return;
    if (key == A_ESCAPE) {
        if (emui.field) { emui.field = 0; emui.status.clear(); }
        else EM_CloseEditor();
        return;
    }
    if (emui.field == 1) {
        if (key == A_ENTER && stemote::labelValid(emui.input)) {
            trap->Cvar_Set(stemote::nameVar(emui.group).c_str(),emui.input.c_str());
            emui.field = 0;
        } else if (key == A_BACKSPACE && !emui.input.empty()) emui.input.pop_back();
        else if (key & K_CHAR_FLAG) {
            const char letter = char(key & ~K_CHAR_FLAG);
            if (emui.input.size() < 24 && stemote::labelValid(std::string(1,letter))) emui.input += letter;
        }
        return;
    }
    if (emui.field == 2) {
        if ((key & K_CHAR_FLAG) || key <= 0 || key >= MAX_KEYS) return;
        char binding[1024] = {};
        trap->Key_GetBindingBuf(key,binding,sizeof(binding));
        const auto command = stemote::directBinding(emui.clips[emui.selected]);
        if (*binding && command != binding) {
            emui.status = "That key is already assigned. Choose another.";
            return;
        }
        trap->Key_SetBinding(key,command.c_str());
        emui.status = "Emote bound";
        emui.field = 0;
        return;
    }
    if (key == A_MOUSE1) {
        for (const auto hit : emui.hits) if (SPUI_Over(hit.x,hit.y,hit.w,hit.h)) {
            EM_EditorAction(hit.id,hit.arg);
            break;
        }
    } else if (key == A_MWHEELUP || key == A_MWHEELDOWN) EM_EditorAction(9,key==A_MWHEELUP?-1:1);
    else if (!emui.hits.empty()) {
        if (key == A_ENTER) {
            const auto hit = emui.hits[emui.focus%emui.hits.size()];
            EM_EditorAction(hit.id,hit.arg);
        } else if (key == A_TAB || key == A_CURSOR_DOWN || key == A_CURSOR_UP) {
            spui.mouse = false;
            emui.focus = (emui.focus+int(emui.hits.size())+(key==A_CURSOR_UP?-1:1))%emui.hits.size();
        }
    }
}

qboolean ST_EmoteUIQA() {
    if (!trap->Cvar_VariableValue("developer")) return qfalse;
    char command[32] = {};
    trap->Cmd_Argv(0,command,sizeof(command));
    if (Q_stricmp(command,"st_emoteuiqa")) return qfalse;
    char operation[32], index[16];
    trap->Cmd_Argv(1,operation,sizeof(operation));
    trap->Cmd_Argv(2,index,sizeof(index));
    if (!Q_stricmp(operation,"controls") && SCUI_IsMenu()) {
        if (!scui.active) SCUI_Start();
        SCUI_Click({0,0,0,0,205,5,0});
        int rowIndex = 0;
        auto row = SCUI_Row(STC_ACTIONS,rowIndex,"Communication");
        while (rowIndex < row.count && Q_stricmp(row.name,"+st_emotewheel"))
            row = SCUI_Row(STC_ACTIONS,++rowIndex,"Communication");
        if (rowIndex < row.count) {
            SCUI_Click({0,0,0,0,500,row.a,0});
            SCUI_Call(STC_CAPTURE,1,0,0,nullptr,nullptr);
            Com_Printf("ST_EMOTE_BIND_ROW %s\n",row.label);
        }
    } else if (!Q_stricmp(operation,"conflict") && SCUI_IsMenu() && scui.modal==2) {
        const bool swap = SCUI_CanSwap();
        Com_Printf("ST_EMOTE_BIND_CONFLICT %d\n",swap);
        if (!Q_stricmp(index,"replace") || (swap && !Q_stricmp(index,"swap"))) {
            SCUI_Click({0,0,0,0,!Q_stricmp(index,"swap")?1701:1702,0,0});
            SCUI_Click({0,0,0,0,1302,0,0});
        }
    } else if (!Q_stricmp(operation,"open") && SPUI_IsMenu()) {
        EM_EditorOpen();
    } else if (!Q_stricmp(operation,"rename") && emui.editing) {
        if (emui.field) EM_EditorKey(A_ESCAPE,qtrue);
        else EM_EditorAction(2,0);
    } else if (!Q_stricmp(operation,"loop") && emui.editing) {
        float frame = 0, speed = 0;
        int first = 0, end = 0, flags = 0;
        if (emui.previewOk && trap->G2API_GetBoneAnim(emui.previewModel,"model_root",uiInfo.uiDC.realTime,
            &frame,&first,&end,&flags,&speed,nullptr,0)) {
            Com_Printf("ST_EMOTE_UI_LOOP %s %d %.2f\n",emui.clips[emui.selected].id.c_str(),
                (flags & BONE_ANIM_OVERRIDE_LOOP) != 0,frame);
        }
    } else if (!Q_stricmp(operation,"preview") && emui.editing) {
        const int row = atoi(index);
        if (row >= 0 && row < int(emui.clips.size())) EM_EditorAction(3,row);
        Com_Printf("ST_EMOTE_UI_PREVIEW %d %d\n",row,emui.previewOk);
    } else if (!Q_stricmp(operation,"assign") && emui.editing) {
        EM_EditorAction(1,4);
        EM_EditorAction(4,7);
        EM_EditorAction(5,0);
        Com_Printf("ST_EMOTE_UI_ASSIGN %s\n",EM_Slot(7).c_str());
    } else if (!Q_stricmp(operation,"close") && emui.editing) {
        EM_CloseEditor();
    } else if (!Q_stricmp(operation,"resume")) {
        UI_SetActiveMenu(UIMENU_NONE);
    }
    return qtrue;
}
