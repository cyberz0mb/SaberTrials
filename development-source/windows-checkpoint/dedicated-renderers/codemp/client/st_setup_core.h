#ifndef ST_SETUP_CORE_H
#define ST_SETUP_CORE_H
#include "st_controls_core.h"
#include <cmath>
#include <cstdlib>
#include <cstring>
namespace ss {
inline bool number(const std::string& v,double low,double high,bool integral,const std::string& base){
 char* end=nullptr;double n=strtod(v.c_str(),&end);
 return !v.empty()&&end&&!*end&&std::isfinite(n)&&(!integral||n==floor(n))&&((n>=low&&n<=high)||v==base);
}
inline const std::vector<const char*>& displayNames(){static const std::vector<const char*> names={"cl_renderer","r_mode","r_customwidth","r_customheight","r_fullscreen"};return names;}
inline bool recoveryValid(const stc::Snapshot& s){
 if(s.vars.size()!=displayNames().size()||!s.binds.empty())return false;
 for(const char* name:displayNames()){
  auto it=s.vars.find(name);if(it==s.vars.end())return false;
  if(!strcmp(name,"cl_renderer")){if(it->second!="rd-vanilla"&&it->second!="rd-rend2")return false;}
  else if(!number(it->second,-2,32768,true,""))return false;
 }return true;
}
inline int restartKind(const std::string& n){
 if(n=="s_khz"||n=="s_useopenal"||n=="s_language")return 2;
 if(n=="cl_renderer"||n=="r_mode"||n=="r_customwidth"||n=="r_customheight"||n=="r_fullscreen"||n=="r_colorbits"||n=="r_texturebits"||n=="r_ext_multisample"||n=="r_ext_compress_textures"||n=="r_picmip"||n=="r_lodbias"||n=="r_subdivisions")return 1;
 return 0;
}
struct DisplayTest{
 int deadline=0;
 void begin(int now){deadline=now+15000;}
 void keep(){deadline=0;}
 bool expired(int now)const{return deadline&&now>=deadline;}
 int remaining(int now)const{return deadline?std::max(0,(deadline-now+999)/1000):0;}
};
}
#endif
