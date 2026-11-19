/* Catalog discovery and data-only upload metadata. GPL-2.0-only. */
static bool SPUI_Exists(const std::string& path){if(path.size()>=MAX_QPATH)return false;fileHandle_t f;int length=trap->FS_Open(path.c_str(),&f,FS_READ);if(f)trap->FS_Close(f);return f&&length>0;}
static bool SPUI_Read(const std::string& path,std::string& text,int maximum=4096){
 if(path.size()>=MAX_QPATH)return false;fileHandle_t f;int length=trap->FS_Open(path.c_str(),&f,FS_READ);
 if(!f)return false;if(length<0||length>maximum){trap->FS_Close(f);return false;}
 std::vector<char> data(length+1,0);if(length)trap->FS_Read(data.data(),length,f);trap->FS_Close(f);text.assign(data.data(),length);return true;
}
static float SPUI_IconAspect(const std::string& path){
 // Read headers once, not the image payload. Preserve non-square DLC icons too.
 static std::map<std::string,float> cache;auto found=cache.find(path);if(found!=cache.end())return found->second;
 unsigned w=0,h=0;fileHandle_t f;int length=trap->FS_Open(path.c_str(),&f,FS_READ);
 if(f){
  std::vector<unsigned char> data(std::max(0,std::min(length,65536)));if(!data.empty())trap->FS_Read(data.data(),int(data.size()),f);trap->FS_Close(f);
  auto be16=[&](size_t p){return unsigned(data[p])*256+data[p+1];};
  if(data.size()>=24&&!memcmp(data.data(),"\x89PNG\r\n\x1a\n",8)){
   auto be32=[&](size_t p){return (unsigned(data[p])<<24)|(unsigned(data[p+1])<<16)|(unsigned(data[p+2])<<8)|data[p+3];};w=be32(16);h=be32(20);
  }else if(data.size()>=4&&data[0]==255&&data[1]==216){
   for(size_t p=2;p+3<data.size();){
    if(data[p++]!=255)break;while(p<data.size()&&data[p]==255)++p;if(p>=data.size())break;unsigned marker=data[p++];
    if(marker==217||marker==218)break;if(marker==216||marker==1||(marker>=208&&marker<=215))continue;
    if(p+2>data.size())break;unsigned n=be16(p);if(n<2||p+n>data.size())break;
    if(marker>=192&&marker<=207&&marker!=196&&marker!=200&&marker!=204&&n>=7){h=be16(p+3);w=be16(p+5);break;}p+=n;
   }
  }else if(data.size()>=18&&sp::lower(path.substr(path.size()-4))==".tga"){w=data[12]+256u*data[13];h=data[14]+256u*data[15];}
 }
 float aspect=w&&h&&w<=65535&&h<=65535?float(w)/h:1.f;cache[path]=aspect;return aspect;
}
static bool SPUI_Base(const std::string& folder){
 // The Saber Trials frontend predates TaystJK's baseModelList. Keep the
 // same explicit original-JKA roster; texture overrides do not change it.
 for(const char* model:{"alora","alora2","bespin_cop","boba_fett","chewbacca","chiss","cultist","desann","galak","gran","human_merc","imperial","imperial_worker","jan","jawa","jedi","jeditrainer","kyle","lando","luke","monmothma","morgan","noghri","prisoner","rax_joris","rebel","rebel_pilot","reborn","reborn_new","reborn_twin","reelo","rodian","rosh_penin","saboteur","shadowtrooper","snowtrooper","stormpilot","stormtrooper","swamptrooper","tavion","tavion_new","trandoshan","tusken","ugnaught","weequay","blank","jedi_hf","jedi_hm","jedi_kdm","jedi_rm","jedi_tf","jedi_zf"})if(!Q_stricmp(folder.c_str(),model))return true;
 return false;
}
static sp::Metadata SPUI_Metadata(const std::string& folder){
 sp::Metadata result;
 if(SPUI_Base(folder)){result.universe="Star Wars";result.themes=sp::SciFi;}
 for(const auto& tag:spTags)if(!Q_stricmp(folder.c_str(),tag.model)){sp::parseMetadata(tag.text,result);break;}
 std::string text;sp::Metadata own;
 if(SPUI_Read("models/players/"+folder+"/st_profile.ini",text)&&sp::parseMetadata(text,own))result=own;
 return result;
}
static void SPUI_BuildCatalog(){
 spui.catalog=sp::Catalog();spui.built=true;
 std::vector<char> dirs(1048576,0),files(1048576,0);
 int nd=trap->FS_GetFileList("models/players","/",dirs.data(),int(dirs.size()));char* dir=dirs.data();
 for(int i=0;i<nd;++i){
  std::string folder=dir;dir+=folder.size()+1;if(!folder.empty()&&folder.back()=='/')folder.pop_back();
  if(!sp::atom(folder)||!SPUI_Exists("models/players/"+folder+"/model.glm"))continue;
  auto meta=SPUI_Metadata(folder);bool base=SPUI_Base(folder);
  std::fill(files.begin(),files.end(),0);int count=trap->FS_GetFileList(("models/players/"+folder).c_str(),"skin",files.data(),int(files.size()));char* file=files.data();
  for(int j=0;j<count;++j){
   std::string name=file;file+=name.size()+1;
   if(name.size()<12||sp::lower(name).compare(0,6,"model_")||sp::lower(name.substr(name.size()-5))!=".skin")continue;
   auto skin=name.substr(6,name.size()-11),id=folder+"/"+skin;if(!sp::validSkin(id))continue;
   std::string icon;
   for(const char* ext:{".jpg",".png",".tga"}){auto path="models/players/"+folder+"/icon_"+skin+ext;if(SPUI_Exists(path)){icon=path;break;}}
   if(icon.empty()&&SPUI_Exists("models/players/"+folder+"/animation.cfg"))continue;
   spui.catalog.add(id,base,meta,icon);
  }
 }
 spui.catalog.finalize();
 // Reading an absent favorite does not create a cvar. Large DLC libraries
 // must not consume the engine's finite cvar table merely by being scanned.
 for(auto& model:spui.catalog.models){auto key=sp::favoriteKey(model.key);model.favorite=trap->Cvar_VariableValue(key.c_str())!=0;}
 Com_Printf("Saber Trials Profile: %d characters, %d skins indexed%s\n",int(spui.catalog.models.size()),int(spui.catalog.skinCount),nd>=4095?"; engine directory limit reached":"");
}
static void SPUI_Features(){
 if(spui.selected<0||spui.variant<0){spui.team=spui.sounds=false;return;}
 const auto& skin=spui.catalog.models[spui.selected].skins[spui.variant];if(spui.featureId==skin.id)return;spui.featureId=skin.id;
 auto prefix="models/players/"+skin.model+"/";
 spui.team=SPUI_Exists(prefix+"model_red.skin")&&SPUI_Exists(prefix+"model_blue.skin");spui.sounds=false;
 std::string text;if(!SPUI_Read(prefix+"sounds.cfg",text))return;
 std::istringstream input(text);std::string voice;input>>voice;
 if(!sp::atom(voice))return;
 for(const char* stock:spStockVoices)if(!Q_stricmp(stock,voice.c_str()))return;
 auto folder="sound/chars/"+voice+"/misc";char files[8192]={0};
 for(const char* ext:{"wav","mp3","ogg"})if(trap->FS_GetFileList(folder.c_str(),ext,files,sizeof(files))>0){spui.sounds=true;break;}
}
