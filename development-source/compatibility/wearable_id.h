// TaystJK hats and capes use a decimal saber color followed by an item name.
// Base JKA servers relay up to 15 characters in each color field.
#ifndef ST_WEARABLE_ID_H
#define ST_WEARABLE_ID_H
static inline int ST_WearableName(const char *name) {
    int i;
    if (!name || !((*name >= 'a' && *name <= 'z') || (*name >= 'A' && *name <= 'Z'))) return 0;
    for (i=0; name[i]; ++i) {
        const char c=name[i];
        if (i>=14 || !((c>='a' && c<='z') || (c>='A' && c<='Z') ||
            (c>='0' && c<='9') || c=='_' || c=='-')) return 0;
    }
    return 1;
}
static inline const char *ST_WearableSuffix(const char *color) {
    const char *s=color;
    while (*s>='0' && *s<='9') ++s;
    return s!=color && ST_WearableName(s) ? s : "";
}
static inline void ST_OutfitKey(const char *model, char *key, int capacity) {
    const char hex[]="0123456789abcdef";
    char id[MAX_QPATH];
    int i, pos;
    Q_strncpyz(id,model && *model ? model : "kyle",sizeof(id));
    if (!strchr(id,'/')) Q_strcat(id,sizeof(id),"/default");
    Q_strlwr(id);
    Q_strncpyz(key,"st_outfit_",capacity);
    pos=(int)strlen(key);
    for(i=0;id[i] && pos+2<capacity;++i) {
        unsigned char c=(unsigned char)id[i];
        key[pos++]=hex[c>>4];key[pos++]=hex[c&15];
    }
    key[pos]=0;
}
#endif
