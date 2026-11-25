// Rend2 add-ons can override the same shader names used by the standard package.
// Keep their ordinary color/alpha stages usable without claiming PBR support.
// Return 0 for an unrelated keyword, 1 if consumed, -1 for malformed arguments.
static int ST_VulkanMaterialCompat(const char *keyword, const char **text) {
    if (!Q_stricmp(keyword,"ormMap") || !Q_stricmp(keyword,"normalMap")) {
        const char *argument=COM_ParseExt(text,qfalse);
        if (!argument[0] || !strcmp(argument,"{") || !strcmp(argument,"}")) return -1;
        return 1;
    }
    if (!Q_stricmp(keyword,"normalScale")) {
        // Rend2 accepts one, two, or three values. Leave following commands and
        // braces untouched, even when they occur on the same line.
        for (int i=0;i<3;++i) {
            const char *start=*text;
            const char *argument=COM_ParseExt(text,qfalse);
            if (!argument[0]) return i ? 1 : -1;
            char *end=nullptr;
            strtod(argument,&end);
            if (end==argument || *end) { *text=start; return i ? 1 : -1; }
        }
        return 1;
    }
    return 0;
}
