// Windows client music panel. Menu actions pass only fixed verbs to the engine.
extern bool ST_MusicQueryEditing(bool finish);
static const char musicMenu[] = "st_music_player";
static char musicOrigin[MAX_QPATH];

static bool MusicIsMenu(const menuDef_t *menu) {
    return menu && menu->window.name && !Q_stricmp(menu->window.name, musicMenu);
}

void ST_MusicRememberOrigin() {
    const menuDef_t *menu = Menu_GetFocused();
    if (MusicIsMenu(menu)) return;
    const bool visible = menu && (trap->Key_GetCatcher() & KEYCATCH_UI);
    Q_strncpyz(musicOrigin, visible ? menu->window.name : "", sizeof(musicOrigin));
}

void ST_MusicClose() {
    if (!MusicIsMenu(Menu_GetFocused())) return;
    ST_MusicQueryEditing(true);
    Menus_CloseByName(musicMenu);
    if (*musicOrigin && Menus_ActivateByName(musicOrigin)) {
        musicOrigin[0] = 0;
        return;
    }
    musicOrigin[0] = 0;
    uiClientState_t client;
    trap->GetClientState(&client);
    if (client.connState < CA_CONNECTED && Menus_ActivateByName("main")) return;
    trap->Key_SetCatcher(trap->Key_GetCatcher() & ~KEYCATCH_UI);
    trap->Key_ClearStates();
    trap->Cvar_Set("cl_paused", "0");
}

static void ST_MusicLoad() {
    if (!Menus_FindByName(musicMenu)) UI_ParseMenu("st_music/ui/player.menu");
    if (!Menus_FindByName(musicMenu)) return;
    menuDef_t *pause = Menus_FindByName("ingame");
    if (!pause || Menu_FindItemByName(pause, "st_music") || pause->itemCount >= MAX_MENUITEMS) return;
    // Only extend the known Trials rail or the stock menu with our Classic extensions.
    // Other mods can supply a different ingame page under the same name.
    const bool classic = ST_ClassicLayout();
    itemDef_t *anchor = Menu_FindItemByName(pause, classic ? "stExtensions" : "about");
    if (!anchor || (!classic && !Menu_FindItemByName(pause, "rail"))) return;
    auto *button = static_cast<itemDef_t *>(UI_Alloc(sizeof(itemDef_t)));
    if (!button) return;
    *button = *anchor;
    button->window.name = "st_music";
    button->text = "Music player";
    // Mirror the first left-column button across the menu's centerline.
    auto &box = button->window.rectClient;
    box.x = pause->window.rect.w - box.x - box.w;
    if (!classic) {
        if (auto *account = Menu_FindItemByName(pause, "account_link")) {
            account->window.rectClient.x = anchor->window.rectClient.x;
            account->window.rectClient.w = box.w;
        }
    }
    button->onFocus = button->leaveFocus = NULL;
    button->action = "exec st_music ;";
    pause->items[pause->itemCount++] = button;
    Menu_PostParse(pause);
}

static bool ST_MusicKey(int key, qboolean down) {
    if (!down || !MusicIsMenu(Menu_GetFocused()) || key <= 0 || key >= MAX_KEYS) return false;
    if (ST_MusicQueryEditing(false)) {
        if (key != A_ENTER && key != A_KP_ENTER) return false;
        ST_MusicQueryEditing(true);
        trap->Cmd_ExecuteText(EXEC_APPEND, "st_musiccmd search\n");
        return true;
    }
    char binding[1024];
    trap->Key_GetBindingBuf(key, binding, sizeof(binding));
    if (!Q_stricmp(binding,"search") || !Q_stricmp(binding,"playnext") ||
        !Q_stricmp(binding,"playprev") || !Q_stricmp(binding,"pausemusic") ||
        !Q_stricmp(binding,"musicvolume -5") || !Q_stricmp(binding,"musicvolume +5")) {
        trap->Cmd_ExecuteText(EXEC_APPEND, va("%s\n", binding));
        return true;
    }
    if (Q_stricmp(binding, "st_music")) return false;
    ST_MusicClose();
    return true;
}

static std::string MusicValue(const char *name) {
    char text[512] = {};
    trap->Cvar_VariableStringBuffer(name, text, sizeof(text));
    return text;
}

static std::string MusicFit(std::string text, float scale, float width) {
    if (RUI_Width(text.c_str(), scale) <= width) return text;
    const float available = width - RUI_Width("...", scale);
    while (!text.empty() && RUI_Width(text.c_str(), scale) > available) {
        size_t cut = text.size() - 1;
        while (cut && (static_cast<unsigned char>(text[cut]) & 0xc0) == 0x80) --cut;
        text.resize(cut);
    }
    return text + "...";
}

static void MusicTime(char *out, size_t size, int seconds) {
    if (seconds >= 3600)
        Com_sprintf(out, size, "%d:%02d:%02d", seconds/3600, seconds/60%60, seconds%60);
    else Com_sprintf(out, size, "%d:%02d", seconds/60, seconds%60);
}

static void MusicStatus(float x, float y, float width, const std::string &status) {
    const float scale = .64f;
    const char *text = status.c_str();
    size_t space = 0, word = 0;
    while ((word = status.find(' ', word)) != std::string::npos) {
        if (RUI_Width(status.substr(0,word).c_str(),scale) > width) break;
        space = word++;
    }
    if (space && RUI_Width(text,scale) > width) {
        RUI_Text(x,y,scale,status.substr(0,space).c_str(),scuMuted);
        RUI_Text(x,y+12,scale,MusicFit(status.substr(space+1),scale,width).c_str(),scuMuted);
    } else RUI_Text(x,y,scale,MusicFit(status,scale,width).c_str(),scuMuted);
}

static void MusicButton(itemDef_t *item, const char *label, bool enabled = true, bool primary = false) {
    const auto &r = item->window.rect;
    if (!enabled) item->window.flags &= ~WINDOW_HASFOCUS;
    const bool focused = (item->window.flags & WINDOW_HASFOCUS) != 0;
    static const vec4_t inactive = {.11f,.15f,.17f,1}, dim = {.46f,.54f,.57f,1};
    if (enabled) RUI_Control(r.x,r.y,r.w,r.h,"field",false,focused);
    else UI_FillRect(r.x,r.y,r.w,r.h,inactive);
    const float *ink = !enabled ? dim : (focused || primary ? ruCyan : ruWhite);
    RUI_ButtonLabel(r.x,r.y,r.w,r.h,.73f,label,ink);
}

static void MusicQuery(const itemDef_t *item, bool local) {
    const auto &r = item->window.rect;
    const bool editing = ST_MusicQueryEditing(false);
    RUI_Control(r.x,r.y,r.w,r.h,"field",false,(item->window.flags & WINDOW_HASFOCUS) != 0);
    std::string query = MusicValue("st_musicQuery");
    if (query.empty() && !editing) {
        RUI_ButtonLabel(r.x,r.y,r.w,r.h,.66f,local ? "Local track name" : "Search the provider's catalog",
                        scuMuted,ITEM_ALIGN_LEFT,7);
        return;
    }
    // Keep the cursor in view even for wide glyphs and mid-string edits.
    size_t caret = std::min(query.size(),size_t(std::max(0,item->cursorPos)));
    size_t offset = 0;
    if (editing) {
        while (offset < caret && RUI_Width(query.substr(offset,caret-offset).c_str(),.7f) > r.w-18)
            ++offset;
    }
    std::string visible = MusicFit(query.substr(offset),.7f,r.w-14);
    RUI_Text(r.x+7,RUI_CaptionY(r.y,r.h,visible.c_str(),.7f),.7f,visible.c_str(),ruWhite);
    if (editing && (uiInfo.uiDC.realTime/450)%2 == 0) {
        float left = r.x+7+RUI_Width(query.substr(offset,caret-offset).c_str(),.7f);
        UI_FillRect(left,r.y+5,1,r.h-10,ruCyan);
    }
}

bool ST_MusicPaint(menuDef_t *menu) {
    if (!MusicIsMenu(menu)) return false;
    const auto &r = menu->window.rect;
    const float x=r.x, y=r.y;
    static const vec4_t surface = {.021f,.038f,.052f,.985f}, rule = {.12f,.23f,.29f,1};
    const std::string source = MusicValue("st_musicSource");
    const bool local = source.empty() || !Q_stricmp(source.c_str(),"Local");
    const std::string title = MusicValue("st_musicTitle"), artist = MusicValue("st_musicArtist");
    const bool playing = trap->Cvar_VariableValue("st_musicPlaying") != 0;
    const bool canToggle = trap->Cvar_VariableValue("st_musicCanToggle") != 0;
    const bool canVolume = trap->Cvar_VariableValue("st_musicCanVolume") != 0;
    UI_FillRect(x,y,r.w,r.h,surface);
    RUI_FieldArt("panel_idle",x,y,r.w,r.h);
    if (RUI_Motion()) {
        const std::vector<stmain::Point> border = {
            {x+3,y+3}, {x+r.w-4,y+3}, {x+r.w-2,y+5}, {x+r.w-2,y+r.h-4},
            {x+r.w-4,y+r.h-2}, {x+3,y+r.h-2}, {x+2,y+r.h-4}, {x+3,y+3}
        };
        RUI_Light(border,stmain::phase(uiInfo.uiDC.realTime,true,8500),ruGold,3.5f);
    }
    UI_FillRect(x+11,y+31,r.w-22,.8f,rule);
    RUI_Image("wordmark",x+14,y+12,100,10);
    RUI_Text(x+123,y+9,.78f,"Music player",ruWhite);
    const float aspect = uiInfo.uiDC.yscale / uiInfo.uiDC.xscale;
    const float cover = 61*std::min(1.f,aspect), discX=x+14+(64-cover)/2;
    const qhandle_t artwork = trap->R_RegisterShaderNoMip("st_music/ui/current_cover");
    if (artwork) {
        UI_FillRect(discX-1,y+37,cover+2,63,rule);
        UI_FillRect(discX,y+38,cover,61,surface);
        trap->R_SetColor(NULL);
        UI_DrawHandlePic(discX,y+38,cover,61,artwork);
    } else {
        SMUI_Image("st_music/ui/record",discX,y+38,cover,61);
        RUI_Image("emblem",discX+cover*.32f,y+57.5f,cover*.36f,22);
    }
    RUI_Text(x+86,y+41,.9f,MusicFit(title.empty() ? (local ? "Local library" : "No active session") : title,
                                    .9f,245).c_str(),ruWhite);
    const std::string subtitle = artist.empty() ? (local ? "Local files" : source) : artist;
    RUI_Text(x+86,y+63,.69f,MusicFit(subtitle,.69f,240).c_str(),scuMuted);
    const int duration = int(std::min(31536000.f,std::max(0.f,trap->Cvar_VariableValue("st_musicDuration"))));
    const int position = int(std::min(31536000.f,std::max(0.f,trap->Cvar_VariableValue("st_musicPosition"))));
    if (duration > 0) {
        char current[20], total[20];
        MusicTime(current,sizeof(current),position);
        MusicTime(total,sizeof(total),duration);
        std::string time = std::string(current)+" / "+total;
        const float timeWidth = RUI_Width(time.c_str(),.57f);
        const float barWidth = 243-timeWidth-9;
        RUI_Text(x+331-timeWidth,y+86,.57f,time.c_str(),scuMuted);
        UI_FillRect(x+86,y+92,barWidth,2,rule);
        UI_FillRect(x+86,y+92,barWidth*std::min(1.f,float(position)/duration),2,ruCyan);
    } else {
        UI_FillRect(x+86,y+92,245,1,rule);
    }
    for (int i=0;i<menu->itemCount;++i) {
        auto *item = menu->items[i];
        const char *n = item->window.name;
        if (!Q_stricmp(n,"source")) {
            std::string choice = "Source   " + (local ? std::string("Local") : source) + "   >";
            MusicButton(item,choice.c_str());
        } else if (!Q_stricmp(n,"previous")) MusicButton(item,"Prev",trap->Cvar_VariableValue("st_musicCanPrevious")!=0);
        else if (!Q_stricmp(n,"toggle")) MusicButton(item,playing?"Pause":"Play",canToggle,canToggle);
        else if (!Q_stricmp(n,"next")) MusicButton(item,"Next",trap->Cvar_VariableValue("st_musicCanNext")!=0);
        else if (!Q_stricmp(n,"query")) MusicQuery(item,local);
        else if (!Q_stricmp(n,"quieter")) MusicButton(item,"-",canVolume);
        else if (!Q_stricmp(n,"louder")) MusicButton(item,"+",canVolume);
        else if (!Q_stricmp(n,"search")) MusicButton(item,local?"Play track":"Find results");
        else if (!Q_stricmp(n,"open")) MusicButton(item,local?"Add local files":("Open "+source).c_str());
        else if (!Q_stricmp(n,"desktop")) MusicButton(item,"Desktop player");
        else if (!Q_stricmp(n,"close_player")) MusicButton(item,"X");
    }
    const int level = (int)trap->Cvar_VariableValue("st_musicVolume");
    RUI_ButtonLabel(x+14,y+178,77,21,.61f,MusicValue("st_musicVolumeLabel").c_str(),scuMuted,ITEM_ALIGN_LEFT,1.f);
    UI_FillRect(x+129,y+188,129,2,rule);
    if (canVolume && level > 0) UI_FillRect(x+129,y+188,129*std::min(100,level)/100.f,2,ruCyan);
    const char *value = canVolume ? va("%d%%",level) : "--";
    RUI_Text(x+299-RUI_Width(value,.64f),y+183,.64f,value,scuMuted);
    MusicStatus(x+15,y+207,r.w-30,MusicValue("st_musicStatus"));
    return true;
}
