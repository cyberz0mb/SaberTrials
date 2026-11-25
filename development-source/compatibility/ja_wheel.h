#pragma once

struct ForeignEmote { const char *label; const char *command; const char *animation; };
static const ForeignEmote baseEmotes[] = {
    {"Taunt","taunt","BOTH_ENGAGETAUNT"}, {"Bow","bow","BOTH_BOW"}, {"Meditate","meditate","BOTH_MEDITATE"}, {"Flourish","flourish","BOTH_SHOWOFF_MEDIUM"}, {"Gloat","gloat","BOTH_VICTORY_MEDIUM"}
};
static const ForeignEmote jaEmotes[] = {
    {"Sit","amsit","BOTH_SIT1"}, {"Dance","amdance","BOTH_STEADYSELF1"}, {"Surrender","amsurrender","TORSO_SURRENDER_START"}, {"At ease","amatease","BOTH_STAND4"},
    {"Sit 2","amsit2","BOTH_SIT3"}, {"Taunt (AM)","amtaunt","BOTH_ALORA_TAUNT"}, {"Hug","amhug","BOTH_HUGGER1"}, {"Kneel","amkneel","BOTH_STAND_TO_KNEEL"},
    {"Sit 3","amsit3","BOTH_SIT6"}, {"Sit 4","amsit4","BOTH_SIT2"}, {"Beg","ambeg","BOTH_KNEES1"}, {"Sleep","sleep","BOTH_SLEEP1"},
    {"Wait","amwait","BOTH_STAND2IDLE1"}, {"Hands on hips","amhips","BOTH_STAND8"}, {"Play dead","amdie","BOTH_DEATH1"}, {"Play dead 2","amdie2","BOTH_DEATH2"},
    {"Hello","amhello","BOTH_GESTURE1"}, {"Nod","amnod","BOTH_HEADNOD"}, {"Shake head","amshake","BOTH_HEADSHAKE"}, {"Come on","amcomeon","BOTH_COME_ON1"},
    {"Kiss","amkiss","BOTH_KISSER"}, {"Noisy","amnoisy","BOTH_SONICPAIN_HOLD"}, {"Won","amwon","BOTH_VICTORY_MEDIUM"}, {"Victory","amvictory","BOTH_TAVION_SCEPTERGROUND"},
    {"Breakdance","ambreakdance","BOTH_FORCE_GETUP_B2"}, {"Breakdance 2","ambreakdance2","BOTH_FORCE_GETUP_B4"}, {"Neo","amneo","BOTH_DODGE_BL"}, {"Flip","amflip","BOTH_ALORA_FLIP_1"},
    {"Power","ampower","BOTH_FORCE_RAGE"}, {"Finisher","amfinishinghim","BOTH_FLIP_STAB"}, {"Hilt throw 1","amhiltThrow1","BOTH_SABERTHROW1START"}, {"Hilt throw 2","amhiltThrow2","BOTH_SABERTHROW2START"},
    {"Knock me down","amknockmedown","BOTH_KNOCKDOWN1"}, {"Drop saber","amdropsaber","TORSO_DROPWEAP1"}
};

namespace jawheel {
constexpr int slots = 8;
constexpr int pages = 5;
constexpr int capacity = slots * pages;
constexpr int remoteCount = ARRAY_LEN(jaEmotes);
constexpr int count = remoteCount + ARRAY_LEN(baseEmotes);
static_assert(count <= capacity, "Default layout is too small");

inline const ForeignEmote &choice(int index) {
    return index < remoteCount ? jaEmotes[index] : baseEmotes[index - remoteCount];
}
inline int find(const char *command) {
    for (int i = 0; i < count; ++i)
        if (!Q_stricmp(choice(i).command, command)) return i;
    return -1;
}
inline const char *slotVar(int slot) { return va("ui_stJaWheelSlot%d",slot+1); }
}
