#ifndef ST_TRANSLATION_API_H
#define ST_TRANSLATION_API_H
#define ST_TRANSLATION_TEXT 2048
#define ST_TRANSLATION_LANGUAGES 20
typedef struct {
    int source, target; /* Stable language IDs in languages.json; source 0=detect. */
    char text[512], names[2048];
} stTranslationRequest_t;
typedef struct {
    unsigned ticket;
    int target;
    char text[ST_TRANSLATION_TEXT]; /* UTF-8 display text, never a command. */
} stTranslationResult_t;

typedef struct {
    int slot; /* bounded cache slot, 0..63 */
    const char *text;
    float width, fontSize, lineHeight; /* 640x480 virtual coordinates */
    int language;
} stChatLayoutRequest_t;
typedef struct { int lines; float height; } stChatLayoutResult_t;
#endif
