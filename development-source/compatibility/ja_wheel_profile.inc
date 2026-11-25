// Included by the engine after its personal-config file helpers.
#include "ja_wheel.h"
#include <array>
#include <fstream>
#include <sstream>

using JaLayout = std::array<int,jawheel::capacity>;
static JaLayout jaLayout;
static const char jaProfile[] = "ja-emote-wheel.txt";

static std::string JA_ProfilePath(const char *name) {
    return FS_BuildOSPath(Cvar_VariableString("fs_homepath"),"SaberTrials",name);
}

static JaLayout JA_ReadLayout() {
    JaLayout layout;
    for (int i=0; i<jawheel::capacity; ++i) layout[i] = i < jawheel::count ? i : -1;
    std::ifstream file(JA_ProfilePath(jaProfile));
    std::string header;
    if (!std::getline(file,header) || header != "JA-WHEEL-1") return layout;
    for (int &entry : layout) {
        std::string id;
        if (!(file >> id)) break;
        entry = jawheel::find(id.c_str());
    }
    return layout;
}

static void JA_Publish(const JaLayout &layout) {
    jaLayout = layout;
    for (int i=0; i<jawheel::capacity; ++i) {
        const char *value = layout[i] < 0 ? "-" : jawheel::choice(layout[i]).command;
        Cvar_Get(jawheel::slotVar(i),"-",CVAR_ROM|CVAR_NORESTART);
        Cvar_Set(jawheel::slotVar(i),value);
    }
}

static bool JA_SaveSlot(int slot,int index) {
    if (slot<0 || slot>=jawheel::capacity || index < -1 || index>=jawheel::count) return false;
    JaLayout next = JA_ReadLayout();
    next[slot] = index;
    std::string data = "JA-WHEEL-1\n";
    for (int entry : next) {
        data += entry < 0 ? "-" : jawheel::choice(entry).command;
        data += '\n';
    }
    const std::string temp = "ja-emote-wheel-" + std::to_string(reinterpret_cast<uintptr_t>(&jaLayout)) + ".tmp";
    fileHandle_t file = FS_SV_FOpenFileWrite(("SaberTrials/"+temp).c_str());
    bool saved = false;
    if (file) {
        saved = FS_Write(data.data(),(int)data.size(),file) == (int)data.size();
        FS_FCloseFile(file);
        saved = saved && STC_AtomicReplace(JA_ProfilePath(temp.c_str()),JA_ProfilePath(jaProfile));
        if (!saved) std::remove(JA_ProfilePath(temp.c_str()).c_str());
    }
    if (saved) JA_Publish(next);
    Cvar_Set("ui_stJaWheelSaved",saved ? "1" : "0");
    return saved;
}

static void JA_Assign() {
    if (!CL_TrialsGame() || Cmd_Argc()!=3) return;
    char *end=nullptr;
    const char *arg=Cmd_Argv(1);
    const long number=strtol(arg,&end,10);
    if (!*arg || *end || number<1 || number>jawheel::capacity) return;
    const char *id=Cmd_Argv(2);
    const int index=jawheel::find(id);
    if (index>=0 || !strcmp(id,"-")) JA_SaveSlot(number-1,index);
}

void CL_JaProfileInit() {
    JA_Publish(JA_ReadLayout());
    Cvar_Get("ui_stJaWheelSaved","0",CVAR_ROM|CVAR_NORESTART);
    Cmd_AddCommand("st_jaWheelAssign",JA_Assign);
}

int CL_JaAssignment(int slot) {
    return slot >= 0 && slot < jawheel::capacity ? jaLayout[slot] : -1;
}
