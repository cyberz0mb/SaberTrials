/* Authoritative style identity shared by all supported HUD variants. */
static const float st_hybridHudGreen[4]={.30f,.94f,.54f,1};
static const float st_hybridHudPurple[4]={.75f,.44f,1,1};
static const float st_hybridHudOrange[4]={1,.55f,.18f,1};
static const char *ST_HybridHudLabel(int style,const float **color) {
    switch(style) {
    case 1:*color=colorTable[CT_ICON_BLUE];return "BLUE";
    case 2:*color=colorTable[CT_YELLOW];return "YELLOW";
    case 3:*color=colorTable[CT_HUD_RED];return "RED";
    case 4:*color=st_hybridHudGreen;return "GREEN";
    case 5:*color=st_hybridHudPurple;return "PURPLE";
    case 6:*color=st_hybridHudOrange;return "ORANGE";
    default:return NULL;
    }
}
