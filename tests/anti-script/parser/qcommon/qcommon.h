// Minimal external engine services for the real codemp/qcommon/cmd.cpp.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>
using byte=unsigned char;
using qboolean=int;
using vmSlots_t=int;
using xcommand_t=void(*)();
using completionFunc_t=void(*)(char*,int);
using callbackFunc_t=void(*)(const char*);
struct cmdList_t {const char* name; const char* description; xcommand_t func; completionFunc_t complete;};
union fileBuffer_t {char* c; void* v;};
constexpr int EXEC_NOW=0, EXEC_INSERT=1, EXEC_APPEND=2, ERR_FATAL=1;
constexpr int qtrue=1,qfalse=0,MAX_QPATH=64,MAX_STRING_TOKENS=1024,BIG_INFO_STRING=8192;
#define S_COLOR_YELLOW ""
#define S_COLOR_WHITE ""
#define S_COLOR_GREY ""
#define S_COLOR_GREEN ""
#define VALIDSTRING(x) ((x) && *(x))
inline const char* vmStrs[]={"test"};
struct Running {int integer;};
inline Running* com_cl_running=nullptr;
inline Running* com_sv_running=nullptr;
void Cmd_Init(); int Cmd_Argc(); char* Cmd_Argv(int); char* Cmd_Args(); char* Cmd_ArgsFrom(int);
void Cmd_ExecuteString(const char*); void Cmd_RemoveCommand(const char*);
void Cmd_SetCommandCompletionFunc(const char*,completionFunc_t);
void Cmd_AddCommand(const char*,xcommand_t,const char*);
void Cbuf_Init(); void Cbuf_AddText(const char*); void Cbuf_InsertText(const char*); void Cbuf_Execute();
void FS_ReadFile(const char*,void**); inline void FS_FreeFile(void* p){std::free(p);}
char* Cvar_VariableString(const char*);
char* va(const char*,...);
bool Cvar_Command(); void CL_ForwardCommandToServer(const char*);
inline bool CL_GameCommand(){return false;} inline bool SV_GameCommand(){return false;}
inline bool UI_GameCommand(){return false;}
inline void Com_Error(int,const char* message){throw std::runtime_error(message);}
inline void Com_Printf(const char*,...){} inline void Com_DPrintf(const char*,...){}
inline void Com_Memcpy(void* d,const void* s,size_t n){std::memcpy(d,s,n);}
inline void* S_Malloc(size_t n){return std::calloc(1,n);}
inline char* CopyString(const char* s){auto n=std::strlen(s)+1;return (char*)std::memcpy(std::malloc(n),s,n);}
inline void Z_Free(void* p){std::free(p);}
inline void Q_strncpyz(char* d,const char* s,size_t n){std::snprintf(d,n,"%s",s);}
inline void Q_strcat(char* d,size_t n,const char* s){auto len=std::strlen(d);Q_strncpyz(d+len,s,n-len);}
inline void COM_DefaultExtension(char* f,size_t n,const char* e){if(!std::strchr(f,'.')) Q_strcat(f,n,e);}
inline int Q_stricmp(const char* a,const char* b){
#ifdef _WIN32
    return _stricmp(a,b);
#else
    return strcasecmp(a,b);
#endif
}
inline void Q_strstrip(char*,const char*,const char*){}
inline bool Com_Filter(const char*,const char*,int){return true;}
inline char* Com_SkipTokens(char* s,int,const char*){return s;}
inline void Field_CompleteCommand(char*,int,int){} inline void Field_CompleteFilename(const char*,const char*,int,int){}
inline void Cvar_CompleteCvarName(char*,int){}
