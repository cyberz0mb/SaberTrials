/* Registry for the native Controls editor. GPL-2.0-only. */
#ifndef ST_CONTROLS_CATALOG_H
#define ST_CONTROLS_CATALOG_H
typedef struct {const char *name,*value,*group,*help;double min,max;int kind;} stcSetting_t;
static const stcSetting_t stcSettings[]={
 {"sensitivity","5","Mouse","Mouse sensitivity",0.001,10000,0},
 {"cl_mouseAccel","0","Mouse","Acceleration amount; zero disables it",0,100,0},
 {"m_pitch","0.022","Mouse","Vertical mouse scale; negative means inverted",-100,100,0},
 {"m_filter","0","Mouse","Mouse smoothing",0,1,1},
 {"cl_yawspeed","140","Advanced","Keyboard horizontal turn speed",0,10000,0},
 {"cl_pitchspeed","140","Advanced","Keyboard vertical look speed",0,10000,0},
 {"cl_anglespeedkey","1.5","Advanced","Turn-speed modifier while walk/run is held",0,10000,0},
 {"m_yaw","0.022","Mouse","Horizontal mouse scale",-100,100,0},
 {"cl_mouseAccelStyle","0","Mouse","Acceleration curve: 0 legacy, 1 power",0,1,1},
 {"cl_mouseAccelOffset","5","Mouse","Power acceleration offset",0.001,100000,0},
 {"cl_run","1","Advanced","Always run",0,1,1},
 {"cl_freelook","1","Mouse","Free mouse look",0,1,1},
 {"m_forward","0.25","Mouse","Legacy mouse forward-movement scale",-10000,10000,0},
 {"m_side","0.25","Mouse","Legacy mouse strafe scale",-10000,10000,0},
 {"in_mouse","1","Mouse","Mouse input: 0 off, 1 raw, 2 compatibility; restarts input",0,2,2},
 {"in_nograb","0","Mouse","Release mouse capture in windowed mode",0,1,1},
 {"in_joystick","0","Advanced","Legacy joystick input; restarts input",0,1,1},
 {"in_joystickUseAnalog","0","Advanced","Legacy joystick analog axes",0,1,1},
 {"joy_threshold","0.15","Advanced","Legacy joystick deadzone",0,0.99,0},
 {"st_controllerEnabled","1","Controller","Automatic controller detection",0,2,2},
 {"st_controllerHorizontal","5","Controller","Horizontal look sensitivity",1,30,3},
 {"st_controllerVertical","5","Controller","Vertical look sensitivity",1,30,3},
 {"st_controllerDeadzone","0.15","Controller","Stick deadzone",0,0.95,3},
 {"st_controllerInvert","0","Controller","Invert controller vertical look",0,1,1},
 {"st_controllerLabels","0","Controller","Button labels: 0 Xbox, 1 PlayStation, 2 generic",0,2,2},
 {"st_controllerMenuSpeed","5","Controller","Menu cursor speed",1,10,3},
 {"st_controllerMenuLayout","0","Controller","Menu confirm and back buttons",0,1,2},
 {"st_virtualKeyboard","0","Controller","On-screen keyboard",0,2,2}
};
typedef struct {const char *label,*command,*group,*help;int restricted;} stcAction_t;
static const stcAction_t stcActions[]={
 {"Move forward","+forward","Movement","Move forward",0},{"Move backward","+back","Movement","Move backward",0},
 {"Strafe left","+moveleft","Movement","Move left without turning",0},{"Strafe right","+moveright","Movement","Move right without turning",0},
 {"Jump","+moveup","Movement","Jump / swim upward",0},{"Crouch","+movedown","Movement","Crouch / swim downward",0},
 {"Walk / run","+speed","Movement","Hold to change walking/running speed",0},{"Turn left","+left","Movement","Keyboard turning",0},{"Turn right","+right","Movement","Keyboard turning",0},
 {"Look up","+lookup","Movement","Keyboard vertical look",0},{"Look down","+lookdown","Movement","Keyboard vertical look",0},{"Center view","centerview","Movement","Center your view",0},{"Strafe modifier","+strafe","Movement","Hold for legacy mouse/keyboard strafe",0},
 {"Attack","+attack","Combat","Tap just before impact to parry, with or without holding Block.",0},{"Alternate attack","+altattack","Combat","Alternate weapon action / saber throw",0},
 {"Block","+block","Combat","Hold to guard while moving and aiming. Tap Attack at impact to parry.",0},
 {"Feint","+feint","Combat","Tap during wind-up to cancel. Hold Attack to follow up; release to stop.",0},
 {"Cycle saber style","saberAttackCycle","Combat","Cycle your selected combat loadout",0},{"Holster / draw saber","sv_saberswitch","Combat","Holster or draw your saber",0},{"Use / interact","+use","Combat","Interact with usable world objects",0},
 {"Use inventory item","+button2","Weapons","Use the selected inventory item",0},{"Next item","invnext","Weapons","Select next inventory item",0},{"Previous item","invprev","Weapons","Select previous inventory item",0},
 {"Next weapon","weapnext","Weapons","Select next available weapon",0},{"Previous weapon","weapprev","Weapons","Select previous available weapon",0},
 {"Saber / melee","weapon 1","Weapons","Select saber or melee",0},{"Pistol","weapon 2","Weapons","Select pistol when available",0},{"Blaster rifle","weapon 3","Weapons","Select blaster rifle when available",0},{"Disruptor","weapon 4","Weapons","Select disruptor when available",0},{"Bowcaster","weapon 5","Weapons","Select bowcaster when available",0},{"Repeater","weapon 6","Weapons","Select repeater when available",0},{"DEMP2","weapon 7","Weapons","Select DEMP2 when available",0},{"Flechette","weapon 8","Weapons","Select flechette when available",0},{"Rocket launcher","weapon 9","Weapons","Select rockets when available",0},{"Thermal detonator","weapon 10","Weapons","Select thermal detonators",0},{"Trip mine","weapon 11","Weapons","Select trip mines",0},{"Det pack","weapon 12","Weapons","Select det packs",0},
 {"Use selected Force power","+useforce","Force","Use the selected available Force power",0},{"Next Force power","forcenext","Force","Select next Force power",0},{"Previous Force power","forceprev","Force","Select previous Force power",0},
 {"Force push","force_throw","Force","Use Push when available",0},{"Force pull","force_pull","Force","Use Pull when available",0},{"Force speed","force_speed","Force","Use Speed when available",0},{"Force heal","force_heal","Force","Use Heal when available",0},{"Force sense","force_seeing","Force","Use Sense when available",0},{"Force protect","force_protect","Force","Use Protect when available",0},{"Force absorb","force_absorb","Force","Use Absorb when available",0},{"Force rage","force_rage","Force","Use Rage when available",0},{"Force team heal","force_healother","Force","Use team Heal when available",0},{"Force team energize","force_forcepowerother","Force","Use team Energize when available",0},{"Force grip","+force_grip","Force","Hold for Grip when available",0},{"Force lightning","+force_lightning","Force","Hold for Lightning when available",0},{"Force drain","+force_drain","Force","Hold for Drain when available",0},{"Mind trick","force_distract","Force","Use Mind Trick when available",0},
 {"Chat","messagemode","Communication","Chat with the current audience",0},{"Team chat","messagemode2","Communication","Chat with your team",0},{"Voice commands","voicechat","Communication","Existing voice-command menu; not proximity voice",0},
 {"Open / collapse chat","st_togglechat","Communication","Toggle the chat panel and recent messages",0},
 {"Scoreboard","+scores","Camera / UI","Hold to show match scores",0},{"Record match","st_record","Camera / UI","Toggle existing match recording",0},{"Screenshot","screenshot_png","Camera / UI","Save a PNG screenshot",0},{"Toggle camera view","cg_thirdperson !","Camera / UI","Toggle supported first/third-person view",0},{"Toggle console","toggleconsole","Camera / UI","Open the console",0},
 {"Freeze","freeze","Server Management","Requires server permission. Add a player argument using Edit command if needed.",1},{"Unfreeze","unfreeze","Server Management","Requires server permission. Use the server's target syntax.",1},{"Ghost on","ghost on","Server Management","Requires authenticated server permission",1},{"Ghost off","ghost off","Server Management","Disable authenticated ghost mode",1},{"Tournament status","tournament status","Server Management","Show current tournament status",1},{"Tournament bracket","tournament bracket","Server Management","Show current bracket",1},
 {"Ignore player","ignore","Communication","Aim at a player and press to ignore or unignore their chat",0},
 {"Private chat with target","messagemode3","Communication","Message the player under your crosshair",0},
 {"Private chat with last attacker","messagemode4","Communication","Message the last player who attacked you",0},
 {"Pause menu","togglemenu","Camera / UI","Open or close the in-game menu",0},
 {"Music player","st_music","Camera / UI","Open or close your music player",0},
 {"Next music track","playnext","Camera / UI","Skip to the next track",0},
 {"Previous music track","playprev","Camera / UI","Go to the previous track",0},
 {"Pause music","pausemusic","Camera / UI","Pause the selected music source",0},
 {"Search music","search","Camera / UI","Search by artist, song or album",0},
 {"Music volume down","musicvolume -5","Camera / UI","Lower music volume by 5%",0},
 {"Music volume up","musicvolume +5","Camera / UI","Raise music volume by 5%",0}
};
#define STC_SETTING_COUNT ((int)(sizeof(stcSettings)/sizeof(stcSettings[0])))
#define STC_ACTION_COUNT ((int)(sizeof(stcActions)/sizeof(stcActions[0])))
#endif
