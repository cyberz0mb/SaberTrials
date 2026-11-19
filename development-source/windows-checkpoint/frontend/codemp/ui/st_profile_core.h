/* Native Profile catalog and draft contracts. GPL-2.0-only. */
#ifndef ST_PROFILE_CORE_H
#define ST_PROFILE_CORE_H
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
namespace sp {
enum Theme { Anime=1, SciFi=2, Horror=4, Fantasy=8, Comics=16, Uncategorized=32 };
inline std::string lower(std::string s){for(char& c:s)c=char(std::tolower((unsigned char)c));return s;}
inline std::string trim(std::string s){size_t a=s.find_first_not_of(" \r\n"),b=s.find_last_not_of(" \r\n");return a==std::string::npos?"":s.substr(a,b-a+1);}
inline bool atom(const std::string& s){if(s.empty()||s.size()>48)return false;for(unsigned char c:s)if(!std::isalnum(c)&&c!='_'&&c!='-'&&c!=' ')return false;return true;}
inline bool display(const std::string& s){if(s.size()>96)return false;for(unsigned char c:s)if(c<32||c==127)return false;return true;}
inline unsigned themeBit(const std::string& s){auto n=lower(trim(s));return n=="anime"?Anime:n=="sci-fi"?SciFi:n=="horror"?Horror:n=="fantasy"?Fantasy:n=="comics"?Comics:0;}
struct Metadata {std::string name,universe,group;unsigned themes=0;};
inline bool parseMetadata(std::string text,Metadata& out){
 if(text.size()>4096)return false;
 if(text.compare(0,3,"\xef\xbb\xbf")==0)text.erase(0,3);
 Metadata next;std::istringstream input(text);std::string line;
 while(std::getline(input,line)){
  line=trim(line);if(line.empty()||line[0]=='#'||line[0]==';')continue;
  size_t split=line.find('=');if(split==std::string::npos)return false;
  auto key=lower(trim(line.substr(0,split))),value=trim(line.substr(split+1));
  if(!atom(key))return false;
  if(!value.empty()&&value[0]=='"'){if(value.size()<2||value.back()!='"')return false;value=value.substr(1,value.size()-2);}
  if(!display(value))return false;
  if(key=="displayname")next.name=value;
  else if(key=="universe")next.universe=value;
  else if(key=="group"){if(!value.empty()&&!atom(value))return false;next.group=lower(value);}
  else if(key=="themes"){
   next.themes=0;std::istringstream tags(value);std::string tag;
   while(std::getline(tags,tag,','))next.themes|=themeBit(tag);
  }
 }
 out=next;return true;
}
inline bool validSkin(const std::string& id){
 auto slash=id.find('/');if(slash==std::string::npos||id.find('/',slash+1)!=std::string::npos)return false;
 auto model=id.substr(0,slash),skin=id.substr(slash+1);
 if(!atom(model)||!atom(skin))return false;
 auto s=lower(skin);
 if(s=="menu"||s.compare(0,4,"fpls")==0||s.compare(0,5,"head_")==0||s.compare(0,6,"torso_")==0||s.compare(0,6,"lower_")==0)return false;
 return ("models/players/"+model+"/model.glm").size()<64&&("models/players/"+model+"/model_"+skin+".skin").size()<64;
}
inline std::string title(std::string s){bool upper=true;for(char& c:s){if(c=='_'||c=='-'){c=' ';upper=true;}else{if(upper)c=char(std::toupper((unsigned char)c));upper=false;}}return s;}
inline std::string favoriteKey(const std::string& key){std::uint64_t h=14695981039346656037ULL;for(unsigned char c:lower(key)){h^=c;h*=1099511628211ULL;}char text[40];std::snprintf(text,sizeof(text),"st_profileFav_%016llx",(unsigned long long)h);return text;}
struct Skin {std::string id,model,skin,label,icon;int appearance=0;};
struct Model {std::string key,name,universe;unsigned themes=0;bool base=false,favorite=false;std::vector<Skin> skins;};
struct Filter {std::string search;int collection=0;unsigned themes=0;bool reverse=false,favorites=false;};
struct Catalog {
 std::vector<Model> models;size_t skinCount=0;std::set<std::string> seen;std::map<std::string,int> groups;
 bool add(const std::string& id,bool base,const Metadata& meta,const std::string& icon=""){
  if(skinCount>=32768||!validSkin(id)||!seen.insert(lower(id)).second)return false;
  auto slash=id.find('/');auto folder=id.substr(0,slash),skin=id.substr(slash+1);
  auto key=std::string(base?"base/":"dlc/")+lower(meta.group.empty()?folder:meta.group);
  int row;auto found=groups.find(key);
  if(found==groups.end()){row=int(models.size());groups[key]=row;Model m;m.key=key;m.name=meta.name.empty()?title(folder):meta.name;m.universe=meta.universe;m.themes=meta.themes;m.base=base;models.push_back(m);}
  else row=found->second;
  Skin variant;variant.id=id;variant.model=folder;variant.skin=skin;variant.label=meta.group.empty()?title(skin):title(folder)+" / "+title(skin);variant.icon=icon;
  variant.appearance=lower(skin)=="red"?1:lower(skin)=="blue"?2:0;
  auto& list=models[row].skins;list.push_back(variant);
  ++skinCount;return true;
 }
 void finalize(){for(auto& model:models)std::stable_sort(model.skins.begin(),model.skins.end(),[](const Skin& a,const Skin& b){if(a.appearance!=b.appearance)return a.appearance<b.appearance;if(lower(a.skin)=="default"&&lower(b.skin)!="default")return true;if(lower(b.skin)=="default"&&lower(a.skin)!="default")return false;return lower(a.id)<lower(b.id);});}
 std::vector<int> rows(const Filter& f)const{
  std::vector<int> result;auto query=lower(f.search);
  for(size_t i=0;i<models.size();++i){const auto& m=models[i];
   if((f.collection==1&&!m.base)||(f.collection==2&&m.base)||(f.favorites&&!m.favorite))continue;
   if(f.themes&&!((m.themes?m.themes:unsigned(Uncategorized))&f.themes))continue;
   std::string search=lower(m.name+" "+m.universe);for(const auto& s:m.skins)search+=" "+lower(s.id+" "+s.label);
   if(!query.empty()&&search.find(query)==std::string::npos)continue;
   result.push_back(int(i));
  }
  std::stable_sort(result.begin(),result.end(),[&](int a,int b){auto x=lower(models[a].name),y=lower(models[b].name);if(x==y){x=models[a].key;y=models[b].key;}return f.reverse?x>y:x<y;});return result;
 }
 std::vector<int> variants(int model,int appearance)const{std::vector<int> result;if(model<0||model>=int(models.size()))return result;const auto& list=models[model].skins;for(size_t i=0;i<list.size();++i)if(list[i].appearance==appearance)result.push_back(int(i));return result;}
 bool find(const std::string& id,int& row,int& variant)const{for(size_t i=0;i<models.size();++i)for(size_t j=0;j<models[i].skins.size();++j)if(lower(id)==lower(models[i].skins[j].id)){row=int(i);variant=int(j);return true;}row=variant=-1;return false;}
};
struct Identity {
 std::string model,name,red,green,blue;
 bool operator==(const Identity& o)const{return model==o.model&&name==o.name&&red==o.red&&green==o.green&&blue==o.blue;}
 bool operator!=(const Identity& o)const{return !(*this==o);}
};
struct Draft {
 Identity base,value;
 void open(const Identity& live){base=value=live;}
 bool dirty()const{return value!=base;}
 bool canApply(const Identity& live)const{return base==live;}
 void cancel(){value=base;}
};
}
#endif
