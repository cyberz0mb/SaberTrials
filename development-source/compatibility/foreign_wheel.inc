// Use engine drawing and input here because the remote mod owns its UI.
#include "ja_wheel.h"
void CL_JaProfileInit();
int CL_JaAssignment(int slot);

static bool CL_IsJAPlus() {
    if (!Q_stricmp(FS_GetCurrentGameDir(false), "japlus")) return true;
    const char *info = cl.gameState.stringData + cl.gameState.stringOffsets[CS_SERVERINFO];
    char name[MAX_QPATH];
    Q_strncpyz(name, Info_ValueForKey(info, "gamename"), sizeof(name));
    Q_CleanStr(name);
    return !Q_stricmpn(name, "JA+", 3) || !Q_stricmpn(name, "japlus", 6);
}

static int foreignSlot = -1;
static int foreignPage;
static constexpr int wheelSlots = 8;
static float wheelX, wheelY;
static int CL_ForeignCount() {
    return ARRAY_LEN(baseEmotes) + (CL_IsJAPlus() ? ARRAY_LEN(jaEmotes) : 0);
}

static const ForeignEmote &CL_ForeignChoice(int index) {
    return CL_IsJAPlus() ? jawheel::choice(index) : baseEmotes[index];
}

static int CL_PageSize(int count) {
    return Com_Clampi(0, wheelSlots, count - foreignPage * wheelSlots);
}

static void CL_ForeignPlay(int slot) {
    const int count = CL_ForeignCount();
    if (slot < 0 || slot >= count || cls.state != CA_ACTIVE || clc.demoplaying) return;
    const char *command = CL_ForeignChoice(slot).command;
    Com_DPrintf("Emote wheel selected %s\n", command);
    if (CL_IsJAPlus() && slot < (int)ARRAY_LEN(jaEmotes)) CL_AddReliableCommand(command, qfalse);
    else Cmd_ExecuteString(command);
}

static int CL_WheelSize() { return CL_IsJAPlus() ? jawheel::capacity : ARRAY_LEN(baseEmotes); }
static int CL_AssignedIndex(int slot) { return CL_IsJAPlus() ? CL_JaAssignment(slot) : slot; }

void CL_EmoteWheelMove(int dx, int dy) {
    if (CL_TrialsGame()) { UIVM_MouseEvent(dx,dy); return; }
    const int count = CL_PageSize(CL_WheelSize());
    if (count == 0) { foreignSlot = -1; return; }
    wheelX += dx;
    wheelY += dy;
    const float radius = sqrtf(wheelX * wheelX + wheelY * wheelY);
    if (radius > 75) { wheelX *= 75 / radius; wheelY *= 75 / radius; }
    if (radius < 9) { foreignSlot = -1; return; }
    const float turns = atan2f(wheelX, -wheelY) / 6.2831853f;
    foreignSlot = foreignPage * wheelSlots + ((int)floorf(turns * wheelSlots + 0.5f) + wheelSlots) % wheelSlots;
    if (foreignSlot >= foreignPage * wheelSlots + count) foreignSlot = -1;
}

static void CL_ForeignKey(int key) {
    const int total = CL_WheelSize();
    const int pages = (total + wheelSlots - 1) / wheelSlots;
    const bool back = key == A_CURSOR_LEFT || key == A_MWHEELUP || key == A_JOY9;
    const bool forward = key == A_CURSOR_RIGHT || key == A_MWHEELDOWN || key == A_JOY10;
    if (pages > 1 && (back || forward)) {
        foreignPage = (foreignPage + (back ? pages - 1 : 1)) % pages;
        foreignSlot = -1;
        wheelX = wheelY = 0;
        return;
    }
    const int count = CL_PageSize(total);
    if (!count) return;
    const int first = foreignPage * wheelSlots;
    if (key >= A_1 && key <= A_8) {
        foreignSlot = key - A_1 < count ? first + key - A_1 : -1;
        return;
    }
    bool previous = key == A_CURSOR_LEFT || key == A_CURSOR_UP || key == A_MWHEELUP ||
                    key == A_JOY9 || key == A_JOY11 || key == A_JOY13;
    const int localSlot = foreignSlot - first;
    foreignSlot = first + ((localSlot < 0) ? (previous ? count-1 : 0) : (localSlot + (previous ? count-1 : 1)) % count);
}

void CL_DrawForeignWheel() {
    const int total=CL_WheelSize(), count=CL_PageSize(total);
    const int pages=(total+wheelSlots-1)/wheelSlots;
    const float aspect=(cls.glconfig.vidHeight/480.f)/(cls.glconfig.vidWidth/640.f);
    const float cx=320,cy=181;
    const float white[]={.83f,.92f,.98f,1},gold[]={1,.78f,.3f,1},muted[]={.48f,.57f,.66f,1};
    auto art=[&](const char *id,float x,float y,float w,float h){
        CL_PersonalPic(id,x-w*aspect/2,y-h/2,w*aspect,h);
    };
    art("emote_face",cx,cy,246,246);
    if (foreignSlot>=0) art(va("emote_focus%d",foreignSlot%wheelSlots),cx,cy,246,246);
    art("emblem",cx,cy-9,26,26);
    CL_PersonalText(CL_IsJAPlus()?"JA+ Emotes":"Emotes",.5f,cx,cy+5,white,true);
    CL_PersonalText(va("%d / %d",foreignPage+1,pages),.43f,cx,cy+17,gold,true);
    for(int i=0;i<wheelSlots;i++) {
        const int slot=foreignPage*wheelSlots+i;
        const int index=i<count?CL_AssignedIndex(slot):-1;
        const float angle=i*6.2831853f/wheelSlots,dx=sinf(angle)*aspect,dy=-cosf(angle);
        const float x=cx+dx*75,y=cy+dy*75;
        const auto *choice=index>=0?&CL_ForeignChoice(index):nullptr;
        const char *icon="empty";
        if (choice) icon=(CL_IsJAPlus() && index<(int)ARRAY_LEN(jaEmotes))?"gesture":
            !strcmp(choice->command,"gloat")?"celebrate":choice->command;
        art(va("emote_%s",icon),x,y-7,23,23);
        const char *label=choice?choice->label:"Empty";
        const float width=CL_PersonalText(label,.49f,0,0,nullptr,false);
        const float scale=width>0?.49f*std::min(1.f,50*aspect/width):.49f;
        CL_PersonalText(label,scale,x,y+6,slot==foreignSlot?gold:choice?white:muted,true);
        art("emote_number",cx+dx*109,cy+dy*109,20,17);
        CL_PersonalText(va("%d",i+1),.5f,cx+dx*109,cy+dy*109-4,gold,true);
    }
    if (pages>1) CL_PersonalText("Scroll  /  Left or right  /  LB or RB",.56f,cx,310,white,true);
}
