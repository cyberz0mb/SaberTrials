// JA+ 1.4 uses c1/c2 for the blade type and c3/c4 for little-endian RGB.
static int JA_ReadRGB(const char *value) {
    unsigned packed=0;
    if (!value || !*value) return -1;
    while (*value) {
        if (*value<'0' || *value>'9') return -1;
        packed=packed*10+(*value++-'0');
        if (packed>0xffffff) return -1;
    }
    return packed ? (int)packed : -1;
}

static void JA_Vector(int packed, vec3_t rgb, float scale) {
    for (int i=0;i<3;++i) rgb[i]=((packed>>(8*i))&255)*scale;
}

static void JA_Tint(int packed, byte rgba[4]) {
    for (int i=0;i<3;++i) rgba[i]=(byte)(packed>>(8*i));
}
