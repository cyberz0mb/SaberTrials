// Saber Trials Controls draft and non-executing config format. GPL-2.0-only.
#ifndef ST_CONTROLS_CORE_H
#define ST_CONTROLS_CORE_H
#include <map>
#include <set>
#include <string>
#include <vector>
#include <functional>
#include <algorithm>
#include <cctype>
namespace stc {
inline std::string lower(std::string s){for(char& c:s)c=(char)std::tolower((unsigned char)c);return s;}
inline std::string trim(const std::string& s){auto a=s.find_first_not_of(" \t\r\n");return a==std::string::npos?"":s.substr(a,s.find_last_not_of(" \t\r\n")-a+1);}
inline std::string profileName(std::string s){s=trim(s);if(lower(s).size()>=4 && lower(s).substr(s.size()-4)==".cfg")s.resize(s.size()-4);return trim(s);}
inline bool validName(const std::string& input){
 auto s=profileName(input);if(s.empty()||s.size()>40||!std::isalnum((unsigned char)s[0]))return false;
 for(unsigned char c:s)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c==' '||c=='_'||c=='-'))return false;
 auto n=lower(s);for(auto x:{"autoexec","default","mpdefault","openjk","jampconfig","server","staff-setup","openjk_server","controls-test","purple-test","setup-test","con","prn","aux","nul"})if(n==x)return false;
 if(n.size()==4&&(n.substr(0,3)=="com"||n.substr(0,3)=="lpt")&&n[3]>='1'&&n[3]<='9')return false;
 return true;
}
inline bool validVar(const std::string& s){
 if(s.empty()||s.size()>128)return false;for(unsigned char c:s)if(!std::isalnum(c)&&c!='_')return false;
 auto n=lower(s);if(n=="com_maxfps")return true;for(auto prefix:{"sv_","g_","bot_","fs_","net_","rcon","vm_","com_"})if(n.find(prefix)==0)return false;
 for(auto secret:{"password","token","secret","credential","session","account","auth"})if(n.find(secret)!=std::string::npos)return false;
 return true;
}
struct Snapshot {
 std::map<int,std::string> binds;
 std::map<std::string,std::string> vars;
 bool operator==(const Snapshot& b)const{return binds==b.binds&&vars==b.vars;}
 bool operator!=(const Snapshot& b)const{return !(*this==b);}
};
template<class K> inline std::string get(const std::map<K,std::string>& m,const K& key){auto p=m.find(key);return p==m.end()?"":p->second;}
template<class K> inline std::set<K> keys(const std::map<K,std::string>& a,const std::map<K,std::string>& b){std::set<K> out;for(auto& x:a)out.insert(x.first);for(auto& x:b)out.insert(x.first);return out;}
enum Conflict {Cancel,Replace,Swap};
struct Draft {
 Snapshot base,value;
 void open(const Snapshot& s){base=value=s;}
 void cancel(){value=base;}
 bool dirty()const{return value!=base;}
 bool move(int from,int to,Conflict choice){
  if(from==to)return true;auto source=get(value.binds,from),target=get(value.binds,to);if(source.empty())return false;
  if(!target.empty()&&choice==Cancel)return false;
  value.binds.erase(from);value.binds[to]=source;if(!target.empty()&&choice==Swap)value.binds[from]=target;return true;
 }
 bool canApply(const Snapshot& live)const{
  for(int k:keys(base.binds,value.binds))if(get(base.binds,k)!=get(value.binds,k)&&get(base.binds,k)!=get(live.binds,k))return false;
  for(auto& k:keys(base.vars,value.vars))if(get(base.vars,k)!=get(value.vars,k)&&get(base.vars,k)!=get(live.vars,k))return false;
  return true;
 }
};
inline std::string quote(const std::string& s){std::string out="\"";for(char c:s){switch(c){case '\\':out+="\\\\";break;case '"':out+="\\\"";break;case '\n':out+="\\n";break;case '\r':out+="\\r";break;default:out+=c;}}return out+'"';}
inline std::string serialize(const Snapshot& s,const std::function<std::string(int)>& keyName){
 std::string out="// SaberTrials personal config v1\n// Load through Setup > Saved Configs for review.\nunbindall\n";
 for(auto& p:s.binds)if(!p.second.empty())out+="bind "+quote(keyName(p.first))+" "+quote(p.second)+"\n";
 for(auto& p:s.vars)if(validVar(p.first))out+="seta "+quote(p.first)+" "+quote(p.second)+"\n";
 return out;
}
inline bool parse(const std::string& text,const std::function<int(const std::string&)>& keyCode,Snapshot& output,std::string& error,bool* replaces=nullptr){
 if(text.size()>4*1024*1024){error="Config exceeds 4 MB.";return false;}
 const bool escapedFormat=text.find("// SaberTrials personal config v1\n")==0||text.find("// SaberTrials personal config v1\r\n")==0;
 if(text.find(char(0))!=std::string::npos){error="Config contains a NUL byte.";return false;}
 Snapshot parsed;std::vector<std::string> tokens;std::string token;bool quoted=false,escape=false,inToken=false,comment=false,clear=false;int line=1;
 auto flush=[&](){if(inToken){tokens.push_back(token);token.clear();inToken=false;}};
 auto command=[&]()->bool{
  flush();if(tokens.empty())return true;auto op=lower(tokens[0]);
  if(op=="unbindall"&&tokens.size()==1){parsed.binds.clear();clear=true;}
  else if((op=="bind"&&tokens.size()==3)||(op=="unbind"&&tokens.size()==2)){
   int k=keyCode(tokens[1]);if(k<0){error="Unknown key: "+tokens[1];return false;}
   if(op=="unbind"||tokens[2].empty()){if(clear)parsed.binds.erase(k);else parsed.binds[k]="";}else parsed.binds[k]=tokens[2];
  }else if((op=="seta"||op=="set")&&tokens.size()==3){if(!validVar(tokens[1])){error="Config contains a non-personal setting: "+tokens[1];return false;}parsed.vars[lower(tokens[1])]=tokens[2];}
  else{error="Only bind, unbind, unbindall, set and seta can be reviewed. Rejected: "+tokens[0];return false;}
  tokens.clear();return true;
 };
 for(size_t i=0;i<text.size();++i){char c=text[i];
  if(comment){if(c!='\n')continue;comment=false;}
  if(quoted){
   if(escape){if(c!='n'&&c!='r'&&c!='\\'&&c!='"'){error="Unsupported escape in versioned config.";return false;}token+=(c=='n'?'\n':c=='r'?'\r':c);escape=false;}
   else if(c=='\\'&&escapedFormat)escape=true;else if(c=='"')quoted=false;else token+=c;
   continue;
  }
  if(c=='/'&&i+1<text.size()&&text[i+1]=='/'){flush();comment=true;++i;continue;}
  if(c=='"'){if(inToken){error="Unexpected quote at line "+std::to_string(line);return false;}quoted=true;inToken=true;continue;}
  if(c==';'||c=='\n'||c=='\r'){if(!command()){error+=" (line "+std::to_string(line)+")";return false;}if(c=='\n')++line;continue;}
  if(c==' '||c=='\t'){flush();continue;}
  if(!token.empty()&&tokens.size()>4096){error="Too many tokens.";return false;}token+=c;inToken=true;
 }
 if(quoted||escape){error="Unterminated quoted value.";return false;}
 if(!command())return false;output=parsed;if(replaces)*replaces=clear;error.clear();return true;
}
}
#endif
