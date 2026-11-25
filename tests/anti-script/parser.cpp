// Execute real OpenJK command buffers, tokenization, exec, vstr and wait.
// The virtual filesystem only exposes the fixtures named below.
#include "client/client.h"
#include "client_trace.h"
#include <algorithm>
#include <cstdarg>
#include <iostream>
#include <map>
#include <vector>
TestCls cls; TestCl cl; TestClc clc;
static std::map<std::string,std::string> files,variables;
static std::vector<std::string> reads,reports,actions;
static std::string mode="1";
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
const char* Info_ValueForKey(const char*,const char* key){CHECK(std::string(key)=="sv_stAntiScript");return mode.c_str();}
void CL_AddReliableCommand(const char* command,int){reports.emplace_back(command);}
char* va(const char* fmt,...){static char b[2048];va_list a;va_start(a,fmt);vsnprintf(b,sizeof(b),fmt,a);va_end(a);return b;}
void FS_ReadFile(const char* path,void** out){reads.emplace_back(path);auto it=files.find(path);*out=it==files.end()?nullptr:CopyString(it->second.c_str());}
char* Cvar_VariableString(const char* key){return variables[key].data();}
bool Cvar_Command(){return false;}
void CL_ForwardCommandToServer(const char*){}
static void set(){variables[Cmd_Argv(1)]=Cmd_Argv(2);}
static void record(){actions.emplace_back(Cmd_Argv(0));}
static void frame(){cl.serverTime+=40;cls.realtime+=40;Cbuf_Execute();CL_ASFrame();}
static void advance(){for(int i=0;i<12;++i)frame();}
int main(){
    try{
        Cmd_Init();Cbuf_Init();CL_ASFrame();
        Cmd_AddCommand("set",set,nullptr);
        for (const char* key:{"+attack","-attack","+forward","-forward","say","bind","saberAttackCycle"})
            Cmd_AddCommand(key,record,nullptr);
        files["preferences.cfg"]=R"cfg(set sensitivity 1.2
bind x "+attack"
say "wait; +attack; -attack"
set hud "saberAttackCycle"
vstr hud
// +attack; wait; -attack
)cfg";
        files["parent.cfg"]="execq preferences.cfg\nexec child.cfg";
        files["child.cfg"]=R"cfg(set step "+attack; wait; -attack; wait; +forward; wait; -forward"
vstr step)cfg";
        files["unused.cfg"]="+attack; wait; -attack";
        Cbuf_AddText("exec preferences.cfg\n");advance();CHECK(reports.empty());
        Cbuf_ASBound("+attack 1 100\n",Cbuf_ASOrigin());frame();
        Cbuf_ASBound("-attack 1 200\n",Cbuf_ASOrigin());frame();CHECK(reports.empty());
        Cbuf_ASBound("exec parent.cfg\n",Cbuf_ASOrigin());advance();
        CHECK(std::find(reads.begin(),reads.end(),"unused.cfg")==reads.end());
        CHECK(reads.size()==4);
        CHECK(std::any_of(reports.begin(),reports.end(),[](auto& s){return s.find(" 0145 ")!=s.npos;}));
        for(auto& s:reports)CHECK(s.find("sensitivity")==s.npos && s.find("cfg")==s.npos);
        auto count=reports.size();
        mode="0";frame();Cbuf_AddText("exec child.cfg\n");advance();CHECK(reports.size()==count);
        CHECK(std::count(actions.begin(),actions.end(),"+forward")==2);
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
