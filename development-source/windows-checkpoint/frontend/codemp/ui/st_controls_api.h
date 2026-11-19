/* Shared native Controls import. GPL-2.0-only. */
#ifndef ST_CONTROLS_API_H
#define ST_CONTROLS_API_H
enum {STC_OPEN=1,STC_STATE,STC_ROWS,STC_BIND,STC_RAW,STC_VAR,STC_APPLY,STC_CANCEL,STC_SAVE,STC_LOAD,STC_RESETVAR,STC_RESETACTION,STC_MOVE,STC_PADDEFAULTS,STC_ACTIONINFO,STC_CAPTURE};
enum {STC_ACTIONS,STC_BINDLIST,STC_SETTINGS,STC_CONFIGS,STC_SERVER,STC_PAD};
typedef struct {int op,a,b,c;char name[128];char text[2048];} stcRequest_t;
typedef struct {int status,count,a,b,c,dirty;float number;char name[128];char label[128];char text[4096];char help[256];} stcReply_t;
/* The native text editor is ASCII; never let byte-wise editing damage UTF-8. */
static int STC_EditableCommand(const char* text){int n=0;for(;text[n];++n)if((unsigned char)text[n]>127||n>=2047)return 0;return 1;}
#endif
