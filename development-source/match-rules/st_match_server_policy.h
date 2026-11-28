// Match Rules server decisions, shared by the live adapter and native tests.
// GPL-2.0; see LICENSE.txt.
#ifndef ST_MATCH_SERVER_POLICY_H
#define ST_MATCH_SERVER_POLICY_H
#include "st_match_rules.h"
#include <map>
namespace stmatch {
inline bool serverRule(int id) {
 return id>=0 && id<RuleCount && std::string(rules[id].cvar)!="ui_dedicated";
}
inline bool rotation(const std::string& value,std::vector<std::string>& maps) {
 maps.clear();if(value.size()>RotationLimit)return false;
 for(unsigned char c:value)if(c!=' '&&(c<33||c>126))return false;
 std::istringstream in(value);std::string map;
 while(in>>map){if(!mapName(map)||maps.size()==32)return false;maps.push_back(map);}return true;
}
inline bool teamAllowed(int type,int count,int team) {
 if(team==0)return true;if(type==8||type==7)return team==1||team==2;
 if(type!=6)return false;return team==1||team==2||(team>=4&&team<=count+1);
}
inline bool entryAllowed(int type,int oldTeam,int team,bool switching,bool locked,int lockedTeam,int cap,int occupants) {
 if(team==3)return true; // Spectating is always permitted.
 if(type!=6&&type!=8)return true;
 if(type==6&&locked&&team!=lockedTeam)return false;
 if(!switching&&oldTeam!=0&&oldTeam!=3&&team!=oldTeam)return false;
 return !cap||occupants<cap||team==oldTeam;
}
inline int forceCap(int mode,int configured,int level) {
 return mode==2?std::min(std::max(0,configured),std::max(0,level)):level;
}
inline int freeSpeed(int mode,int configured,bool enabled,int level) {
 return forceCap(mode,configured,enabled?3:level);
}
inline int forceMask(int mode,const std::array<int,ForceCount>& caps) {
 if(mode==1)return 0;if(mode!=2)return 163833;
 int mask=0;for(int i=0;i<ForceCount;++i)if(caps[i]==0)mask|=1<<i;return mask;
}
inline int weaponMask(int mode,int custom) {
 return mode==2?custom:mode==0?524274:0;
}
inline int spawnHealth(int type,int configured,int normal) {return type!=7&&configured>0?configured:normal;}
inline int spawnShield(int type,int configured,int normal) {return type!=7&&configured>=0?configured:normal;}
inline int respawnAt(int type,int normal,int death,int delay) {
 return type==3||type==4||type==7?normal:std::max(normal,death+std::max(0,delay));
}
struct Draft {
 std::map<std::string,std::string> edits;
 bool armed=false;
 bool set(const std::string& name,const std::string& value) {
  int n=0,id=find(name);if(!serverRule(id)||!integer(value,n)||!valid(id,n))return false;
  edits[name]=std::to_string(n);armed=false;return true;
 }
 bool force(int index,int cap) {
  if(index<0||index>=ForceCount||cap<0||cap>3)return false;
  edits["st_matchForceCap"+std::to_string(index)]=std::to_string(cap);armed=false;return true;
 }
 bool weapons(int mask) {
  if(mask<0||mask>=(1<<WeaponCount)||(mask&12))return false;
  edits["st_matchWeaponDisable"]=std::to_string(mask);armed=false;return true;
 }
 bool text(const std::string& kind,const std::string& value) {
  std::vector<std::string> maps;
  if(kind=="rotation"){if(!rotation(value,maps))return false;}
  else if(kind=="map"){if(!mapName(value))return false;}
  else if(kind=="hostname"){if(!safeText(value,100))return false;}
  else if(kind=="password"){if(!safeText(value,64))return false;}
  else return false;
  edits[kind=="rotation"?"st_matchRotation":kind=="hostname"?"sv_hostname":kind=="password"?"g_password":"mapname"]=value;
  armed=false;return true;
 }
 bool restart() const {
  for(const auto& item:edits){int id=find(item.first);
   if((id>=0&&rules[id].restart)||item.first=="mapname"||item.first=="st_matchRotation"||item.first=="st_matchWeaponDisable"||item.first.find("st_matchForceCap")==0)return true;
  }return false;
 }
 void clear(){edits.clear();armed=false;}
};
}
#endif
