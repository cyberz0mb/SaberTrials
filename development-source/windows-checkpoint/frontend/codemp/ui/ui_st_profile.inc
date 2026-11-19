/* Approved native Profile browser. GPL-2.0-only. */
#include "st_profile_core.h"
#include "st_profile_tags.h"
#include "st_profile_stock_voices.h"
struct SPHit {float x,y,w,h;int id,arg;};
static struct SPUIState {
 bool active=false,wide=false,built=false,motion=true,replace=false,mouse=false;
 int selected=-1,variant=-1,scroll=0,columns=4,visibleRows=3,focus=100,field=0,caret=0,hover=-1,hoverTime=0,modal=0,destination=0;
 stmenu::Scrollbar scrollbar={};
 float gridX=0,gridY=0,gridW=0,gridH=0,rowH=0;
 std::string menu,edit,status,featureId;bool team=false,sounds=false;
 sp::Catalog catalog;sp::Filter filter;sp::Draft draft;std::vector<int> rows;std::vector<SPHit> hits;
 int themeCounts[6]={0,0,0,0,0,0};
} spui;
static const char* spThemeNames[]={"Anime","Sci-Fi","Horror","Fantasy","Comics","Uncategorized"};
static const unsigned spThemeBits[]={sp::Anime,sp::SciFi,sp::Horror,sp::Fantasy,sp::Comics,sp::Uncategorized};
static bool SPUI_IsMenu(){menuDef_t* m=Menu_GetFocused();return m&&(!Q_stricmp(m->window.name,"playerMenu")||!Q_stricmp(m->window.name,"ingame_player"));}
static std::string SPUI_Var(const char* name){char value[512];trap->Cvar_VariableStringBuffer(name,value,sizeof(value));return value;}
static sp::Identity SPUI_Live(){sp::Identity i;i.model=SPUI_Var("model");i.name=SPUI_Var("name");i.red=SPUI_Var("char_color_red");i.green=SPUI_Var("char_color_green");i.blue=SPUI_Var("char_color_blue");return i;}
static void SPUI_Filter(){spui.scrollbar.dragging=false;spui.rows=spui.catalog.rows(spui.filter);spui.scroll=0;sp::Filter all=spui.filter;all.themes=0;std::fill(spui.themeCounts,spui.themeCounts+6,0);for(int row:spui.catalog.rows(all)){unsigned bits=spui.catalog.models[row].themes;for(int i=0;i<6;++i)if((bits?bits:unsigned(sp::Uncategorized))&spThemeBits[i])++spui.themeCounts[i];}}
static void SPUI_Select(int row,int variant=-1){
 if(row<0||row>=int(spui.catalog.models.size()))return;
 auto& m=spui.catalog.models[row];if(m.skins.empty())return;
 if(variant<0||variant>=int(m.skins.size()))variant=0;
 spui.selected=row;spui.variant=variant;spui.draft.value.model=m.skins[variant].id;spui.status.clear();
 trap->Cvar_Set("ui_stProfileSelection",spui.draft.value.model.c_str());
}
static void SPUI_SyncSelection(){std::string id=spui.draft.value.model;if(id.find('/')==std::string::npos)id+="/default";spui.catalog.find(id,spui.selected,spui.variant);trap->Cvar_Set("ui_stProfileSelection",spui.draft.value.model.c_str());}
#include "ui_st_profile_catalog.inc"
static void SPUI_Start(){
 menuDef_t* menu=Menu_GetFocused();if(!menu)return;
 if(!spui.built)SPUI_BuildCatalog();
 spui.active=true;spui.wide=!Q_stricmp(menu->window.name,"ingame_player");spui.menu=menu->window.name;
 spui.scrollbar={};spui.draft.open(SPUI_Live());spui.scroll=0;spui.focus=100;spui.field=0;spui.modal=0;spui.hover=-1;spui.status.clear();spui.featureId.clear();SPUI_SyncSelection();SPUI_Filter();
 trap->Cvar_Set("ui_Name",spui.draft.value.name.c_str());
}
static void SPUI_BeforePaint(){
 if(!SPUI_IsMenu()){spui.active=false;return;}
 menuDef_t* m=Menu_GetFocused();if(!spui.active||spui.menu!=m->window.name)SPUI_Start();
 if(itemDef_t* item=Menu_FindItemByName(m,"st_profile_preview")){
  const int flags=WINDOW_VISIBLE;
  if(spui.modal)item->window.flags &= ~flags;else item->window.flags|=flags;
 }
}
static bool SPUI_Over(float x,float y,float w,float h){return uiInfo.uiDC.cursorx>=x&&uiInfo.uiDC.cursorx<=x+w&&uiInfo.uiDC.cursory>=y&&uiInfo.uiDC.cursory<=y+h;}
static void SPUI_Hit(float x,float y,float w,float h,int id,int arg=0){SPHit hit={x,y,w,h,id,arg};spui.hits.push_back(hit);}
static void SPUI_Button(float x,float y,float w,float h,const char* text,int id,int arg=0,bool selected=false,bool enabled=true){
 const bool focus=SPUI_Over(x,y,w,h)||(!spui.mouse&&spui.focus==id);
 const bool collection=id>=110&&id<=112;
 const bool centered=collection||(id>=500&&id<=502)||id>=1000;
 const bool modalAction=spui.modal&&id>=1000&&id<=1013;
 vec4_t color;MSUI_Color(color,selected,focus,enabled||selected);
 if(modalAction||(id<520&&w>=32&&(id<130||id==137||id>=410))){
  const bool compact=id==121||id==137||id==412;
  const float width=compact?std::min(w,std::max(34.f,20.f+RUI_Width(text,.53f))):w;
  RUI_Control(centered?x+(w-width)/2:x,y,width,h,collection?"tab":"action",selected,focus&&enabled);
 }
 if(w<22)SCUI_Text(x+(w-RUI_Width(text,.43f))/2,y+std::max(1.f,(h-11)/2),.43f,text,color);
 else if(centered)SCUI_Centered(x,y,w,h,.53f,text,color);
 else SCUI_Label(x+5,y+(h-17*.53f)/2,w-10,.53f,text,color);
 if(enabled)SPUI_Hit(x,y,w,h,id,arg);
}
static void SPUI_Mouse(){
 if(!spui.active)return;
 spui.mouse=true;if(spui.scrollbar.dragging&&!spui.modal){stmenu::move(spui.scrollbar,uiInfo.uiDC.cursory,spui.scroll);spui.hover=-1;return;}int hover=-1;
 for(auto i=spui.hits.rbegin();i!=spui.hits.rend();++i)if(SPUI_Over(i->x,i->y,i->w,i->h)){
  spui.focus=i->id;if(i->id>=2000&&i->id<40000)hover=i->arg;break;
 }
 if(hover!=spui.hover){spui.hover=hover;spui.hoverTime=uiInfo.uiDC.realTime;}
}
static void SPUI_Field(float x,float y,float w,int id,const std::string& text){
 UI_FillRect(x,y,w,23,scuPanel);SCUI_Border(x,y,w,23,spui.field==id?scuCyan:scuLine);
 const auto& value=spui.field==id?spui.edit:text;
 SCUI_Fit(x+6,y+5,w-12,.54f,value.c_str(),scuText);SPUI_Hit(x,y,w,23,id);
 if(spui.field==id&&((uiInfo.uiDC.realTime/400)&1)){
  float caret=x+6+RUI_Width(spui.edit.substr(0,spui.caret).c_str(),.54f);
  if(caret<x+w-6)UI_FillRect(caret,y+5,1,13,scuCyan);
 }
}
static void SPUI_Click(int id,int arg);
#include "ui_st_profile_actions.inc"
#include "ui_st_profile_draw.inc"
static qboolean SPUI_Key(int key,qboolean down){
 if(!SPUI_IsMenu())return qfalse;if(!spui.active)SPUI_Start();if(!down){if(key==A_MOUSE1)spui.scrollbar.dragging=false;return qtrue;}
 if(key==A_ESCAPE||key==A_JOY1){
  if(spui.modal)SPUI_Click(1002,0);
  else if(spui.field){spui.field=0;}
  else SPUI_Click(500,0);return qtrue;
 }
 if(spui.field){
  if(key&K_CHAR_FLAG){unsigned char c=(unsigned char)(key&~K_CHAR_FLAG);if(c>=32&&c!=127&&spui.edit.size()<96){if(spui.replace){spui.edit.clear();spui.caret=0;spui.replace=false;}spui.edit.insert(spui.caret++,1,char(c));}}
  else if(key==A_BACKSPACE){if(spui.caret>0)spui.edit.erase(--spui.caret,1);spui.replace=false;}
  else if(key==A_DELETE){if(spui.caret<int(spui.edit.size()))spui.edit.erase(spui.caret,1);spui.replace=false;}
  else if(key==A_HOME)spui.caret=0;
  else if(key==A_END)spui.caret=int(spui.edit.size());
  else if(key==A_CURSOR_LEFT&&spui.caret>0)--spui.caret;
  else if(key==A_CURSOR_RIGHT&&spui.caret<int(spui.edit.size()))++spui.caret;
  else if(key==A_ENTER||key==A_TAB)spui.field=0;
  if(spui.field==100){spui.filter.search=spui.edit;SPUI_Filter();}
  if(spui.field==101)spui.draft.value.name=spui.edit;
  if(key!=A_MOUSE1)return qtrue;
 }
 if(key==A_MOUSE1){spui.mouse=true;if(!spui.modal&&stmenu::begin(spui.scrollbar,uiInfo.uiDC.cursorx,uiInfo.uiDC.cursory,spui.scroll)){spui.hover=-1;return qtrue;}for(auto i=spui.hits.rbegin();i!=spui.hits.rend();++i)if(SPUI_Over(i->x,i->y,i->w,i->h)){auto hit=*i;spui.focus=hit.id;SPUI_Click(hit.id,hit.arg);break;}return qtrue;}
 if(!spui.modal&&(key==A_MWHEELDOWN||key==A_MWHEELUP)){
  spui.mouse=true;
  int total=(int(spui.rows.size())+spui.columns-1)/spui.columns;
  spui.scroll=std::max(0,std::min(std::max(0,total-spui.visibleRows),spui.scroll+(key==A_MWHEELDOWN?1:-1)));return qtrue;
 }
 if(key==A_TAB||key==A_CURSOR_DOWN||key==A_CURSOR_UP||key==A_CURSOR_LEFT||key==A_CURSOR_RIGHT||key==A_JOY11||key==A_JOY12||key==A_JOY13||key==A_JOY14){
  spui.mouse=false;
  int direction=(key==A_CURSOR_UP||key==A_CURSOR_LEFT||key==A_JOY11||key==A_JOY13)?-1:1;
  if(spui.focus>=2000&&spui.focus<40000&&!spui.modal){
   auto at=std::find(spui.rows.begin(),spui.rows.end(),spui.focus-2000);
   if(at!=spui.rows.end()){
    int step=(key==A_CURSOR_DOWN||key==A_CURSOR_UP||key==A_JOY11||key==A_JOY12)?spui.columns:1;
    int next=int(at-spui.rows.begin())+direction*step;
    if(next>=0&&next<int(spui.rows.size())){spui.focus=2000+spui.rows[next];int row=next/spui.columns;if(row<spui.scroll)spui.scroll=row;if(row>=spui.scroll+spui.visibleRows)spui.scroll=row-spui.visibleRows+1;return qtrue;}
   }
  }
  int at=-1;for(size_t i=0;i<spui.hits.size();++i)if(spui.hits[i].id==spui.focus)at=int(i);
  if(!spui.hits.empty()){at=(at+direction+int(spui.hits.size()))%int(spui.hits.size());spui.focus=spui.hits[at].id;}return qtrue;
 }
 if(key==A_ENTER||key==A_JOY0){for(const auto& hit:spui.hits)if(hit.id==spui.focus){SPUI_Click(hit.id,hit.arg);break;}}
 return qtrue;
}
#ifdef ST_CONTROLS_QA
#include "ghoul2/G2.h"
#include <functional>
static void SPUI_TestScroll(const char* name,float x,float top,float track,float thumb,int maximum,
 const std::function<qboolean(int,qboolean)>& key,const std::function<void()>& mouse,const std::function<int()>& position,const std::function<void()>& paint){
 auto fail=[&](const char* reason){Com_Printf("ST_PROFILE_FAIL %s scrollbar %s\n",name,reason);};
 if(maximum<=0){fail("fixture has no overflow");return;}
 uiInfo.uiDC.cursorx=x;uiInfo.uiDC.cursory=top+thumb/2;key(A_MOUSE1,qtrue);
 mouse();paint();if(position()!=0)fail("thumb grab jumps");
 uiInfo.uiDC.cursorx=650;uiInfo.uiDC.cursory=1000;mouse();paint();if(position()!=maximum)fail("cannot drag to bottom outside track");
 key(A_MOUSE1,qfalse);uiInfo.uiDC.cursory=-100;mouse();if(position()!=maximum)fail("keeps dragging after mouse release");
 uiInfo.uiDC.cursorx=x;uiInfo.uiDC.cursory=top+track-thumb/2;key(A_MOUSE1,qtrue);
 uiInfo.uiDC.cursory=-100;mouse();if(position()!=0)fail("cannot drag back to top");key(A_MOUSE1,qfalse);
 uiInfo.uiDC.cursorx=x;uiInfo.uiDC.cursory=top+track-1;key(A_MOUSE1,qtrue);key(A_MOUSE1,qfalse);if(position()<=0)fail("track click does not scroll");
 uiInfo.uiDC.cursorx=x;uiInfo.uiDC.cursory=top+track-thumb/2;key(A_MOUSE1,qtrue);uiInfo.uiDC.cursory=-100;mouse();key(A_MOUSE1,qfalse);
 Com_Printf("ST_MENU_SCROLL_CHECK %s completed\n",name);
}
static const char* SPUI_Arg(int n){static char args[4][1024];trap->Cmd_Argv(n,args[n%4],sizeof(args[0]));return args[n%4];}
static std::string spQAServer;
static int SPUI_QAConfig(int index,char* buffer,int size){Q_strncpyz(buffer,index==CS_SERVERINFO?spQAServer.c_str():"",size);return int(strlen(buffer));}
qboolean ST_ProfileQA(){
 if(Q_stricmp(SPUI_Arg(0),"st_profileqa"))return qfalse;
 std::string op=SPUI_Arg(1),a=SPUI_Arg(2),b=SPUI_Arg(3);
 auto fail=[](const char* text){Com_Printf("ST_PROFILE_FAIL %s\n",text);};
 if(op=="choose"){int row,variant;if(spui.catalog.find(a,row,variant))SPUI_Select(row,variant);else fail("missing selection");}
 else if(op=="scrollcheck"){
  std::string live=SPUI_Var("model");
  if(a=="profile"){
   SPUI_Draw();int total=(int(spui.rows.size())+spui.columns-1)/spui.columns;
   SPUI_TestScroll("Profile",spui.gridX+spui.gridW-5,spui.gridY+21,spui.gridH-43,std::max(15.f,(spui.gridH-43)*spui.visibleRows/total),total-spui.visibleRows,SPUI_Key,SPUI_Mouse,[]{return spui.scroll;},SPUI_Draw);
  }else if(a=="controls"){
   Menus_CloseAll();Menus_ActivateByName("controlsMenu");scui.active=0;SCUI_Draw();scui.tab=3;scui.fold[3]=1;scui.mouseScroll=0;SCUI_Draw();
   SPUI_TestScroll("Controls",617,203,182,182.f*234/361,127,SCUI_Key,SCUI_Mouse,[]{return scui.mouseScroll;},SCUI_Draw);
  }else if(a=="setup"){
   SCUI_Call(STC_CANCEL,0,0,0,NULL,NULL);scui.active=0;Menus_CloseAll();Menus_ActivateByName("setup_menu");ssui.active=0;SSUI_Draw();ssui.tab=0;ssui.advanced=1;ssui.scroll=0;SSUI_Draw();
   SPUI_TestScroll("Setup",617,237,147,std::max(24.f,147.f*199/(199+ssui.maxScroll)),ssui.maxScroll,SSUI_Key,SSUI_Mouse,[]{return ssui.scroll;},SSUI_Draw);
  }else if(a=="finish"){
   SSUI_End();ssui.active=0;Menus_CloseAll();Menus_ActivateByName("playerMenu");spui.active=false;SPUI_Start();
  }else fail("unknown scrollbar fixture");
  if(SPUI_Var("model")!=live)fail("scrolling changed active model");
 }
 else if(op=="portraitfixture"){int row,variant;if(spui.catalog.find("alora/default",row,variant))spui.catalog.models[row].skins[variant].icon="models/players/alora/profile_test.png";else fail("stock portrait fixture missing");}
 else if(op=="search"){spui.filter.search=a;SPUI_Filter();}
 else if(op=="collection"){spui.filter.collection=atoi(a.c_str());SPUI_Filter();}
 else if(op=="click"){int id=atoi(a.c_str());bool found=false;for(const auto& hit:spui.hits)if(hit.id==id){uiInfo.uiDC.cursorx=hit.x+hit.w/2;uiInfo.uiDC.cursory=hit.y+hit.h/2;SPUI_Key(A_MOUSE1,qtrue);found=true;break;}if(!found)fail("click target missing");}
 else if(op=="appearance")SPUI_Appearance(atoi(a.c_str()));
 else if(op=="text"){for(unsigned char c:a)SPUI_Key(c|K_CHAR_FLAG,qtrue);}
 else if(op=="key")SPUI_Key(atoi(a.c_str()),qtrue);
 else if(op=="favorite"){if(spui.selected>=0)SPUI_Click(40000+spui.selected,spui.selected);else fail("favorite selection missing");}
 else if(op=="assertfavorite"){if(spui.selected<0||spui.catalog.models[spui.selected].favorite!=(a=="1"))fail("favorite state");}
 else if(op=="assertuniverse"){if(spui.selected<0||spui.catalog.models[spui.selected].universe!=a)fail("metadata franchise mismatch");}
 else if(op=="asserttitle"){if(spui.selected<0||spui.catalog.models[spui.selected].name!=a)fail("metadata display name mismatch");}
 else if(op=="assertvoice"){SPUI_Features();if(spui.sounds!=(a=="1"))fail("stock fallback mistaken for custom voice");}
 else if(op=="assertlazyfavorites"){for(const auto& model:spui.catalog.models)if(!SPUI_Var(sp::favoriteKey(model.key).c_str()).empty())fail("scanning creates one cvar per model");}
 else if(op=="sample"){
  menuDef_t* m=Menu_GetFocused();itemDef_t* item=m?Menu_FindItemByName(m,"st_profile_preview"):NULL;
  if(!item||!item->ghoul2)fail("animation instance missing");
  else{float frame=0,speed=0;int first=0,last=0,flags=0;trap->G2API_GetBoneAnim(item->ghoul2,"model_root",uiInfo.uiDC.realTime,&frame,&first,&last,&flags,&speed,NULL,0);auto* model=item->typeData.model;Com_Printf("ST_PROFILE_ANIM frame=%.3f yaw=%.3f loop=%d\n",frame,model->angle+(float)uiInfo.uiDC.realTime/model->rotationSpeed,(flags&BONE_ANIM_OVERRIDE_LOOP)!=0);}
 }
 else if(op=="previewmissing")trap->Cvar_Set("ui_stProfileSelection","missing_profile_fixture/default");
 else if(op=="previewskinmissing")trap->Cvar_Set("ui_stProfileSelection","luffy/missing_profile_fixture");
 else if(op=="forceparity"){
  // Exercise the real ownerdraw handler with private server-info fixtures.
  // Non-Jedi -> Jedi does not issue a join/respawn command in the native code.
  auto savedConfig=trap->GetConfigString;int savedRole=uiJediNonJedi;auto savedDraft=spui.draft;
  int savedRanks[NUM_FORCE_POWERS];std::copy(uiForcePowersRank,uiForcePowersRank+NUM_FORCE_POWERS,savedRanks);
  extern qboolean gTouchedForce;auto touched=gTouchedForce;
  trap->GetConfigString=SPUI_QAConfig;
  for(int gametype:{GT_HOLOCRON,GT_JEDIMASTER}){spQAServer="\\g_gametype\\"+std::to_string(gametype);if(SPUI_ForceAvailable())fail("Force enabled in restricted gametype");}
  spQAServer="\\g_gametype\\0\\g_jediVmerc\\1";uiJediNonJedi=FORCE_NONJEDI;
  spui.draft.open(SPUI_Live());SPUI_Apply();if(uiJediNonJedi!=FORCE_NONJEDI)fail("ordinary Apply changed Jedi role");
  SPUI_Draw();bool role=false;for(const auto& hit:spui.hits)if(hit.id==516)role=true;
  if(!role)fail("native Jedi role selector missing");
  else{SPUI_Click(516,0);if(uiJediNonJedi==FORCE_NONJEDI||!SPUI_ForceAvailable()||uiForcePowersRank[FP_LEVITATION]<1||uiForcePowersRank[FP_SABER_OFFENSE]<1)fail("native Jedi role transition failed");}
  spQAServer="\\g_gametype\\0\\g_forcePowerDisable\\262143";if(SPUI_ForceAvailable())fail("Force enabled while all powers disabled");
  trap->GetConfigString=savedConfig;uiJediNonJedi=savedRole;spui.draft=savedDraft;std::copy(savedRanks,savedRanks+NUM_FORCE_POWERS,uiForcePowersRank);gTouchedForce=touched;
 }
 else if(op=="assertunavailable"){menuDef_t* m=Menu_GetFocused();itemDef_t* item=Menu_FindItemByName(m,"st_profile_preview");if(SPUI_Var("ui_stProfilePreviewAvailable")!="0"||(item&&item->ghoul2))fail("stale preview survived failed load");}
 else if(op=="assertlive"){if(SPUI_Var(a.c_str())!=b)fail("live value mismatch");}
 else if(op=="assertpending"){if(spui.draft.value.model!=a)fail("pending model mismatch");}
 else if(op=="assertrows"){if(spui.rows.size()!=size_t(atoi(a.c_str())))fail("result count");}
 else if(op=="assertdirty"){if(spui.draft.dirty()!=(a=="1"))fail("dirty state");}
 else if(op=="assertlayout"){if(spui.wide!=(a=="wide"))fail("layout context");}
 else if(op=="assertpreview"){if(SPUI_Var("ui_stProfilePreviewAvailable")!="1")fail("preview unavailable");}
 else if(op=="assertstatus"){if(spui.status.find(a)==std::string::npos)fail("status mismatch");}
 else if(op=="focusselected"){spui.focus=2000+spui.selected;spui.mouse=false;}
 else if(op=="assertmenu"){menuDef_t* m=Menu_GetFocused();if(!m||a!=m->window.name)fail("menu destination");}
 else if(op=="reload")SPUI_Start();
 else if(op=="ingame"){spui.active=false;UI_LoadMenus("ui/jampingame.txt",qtrue);Menus_ActivateByName("ingame_player");trap->Key_SetCatcher(KEYCATCH_UI);}
 else if(op=="assertactions"){menuDef_t* m=Menu_GetFocused();for(const char* name:{"sp_action_custom","sp_action_saber","sp_action_force","sp_action_join","sp_action_red","sp_action_blue","sp_action_spectate"}){itemDef_t* item=Menu_FindItemByName(m,name);if(!item||!item->action)fail("legacy action missing");}}
 else if(op=="state")Com_Printf("ST_PROFILE_STATE wide=%d models=%d skins=%d rows=%d dirty=%d selected=%s\n",spui.wide,int(spui.catalog.models.size()),int(spui.catalog.skinCount),int(spui.rows.size()),spui.draft.dirty(),spui.draft.value.model.c_str());
 else fail("unknown QA operation");
 return qtrue;
}
#endif
