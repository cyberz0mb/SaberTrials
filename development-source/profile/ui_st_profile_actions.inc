/* Profile edits are staged; existing navigation/team scripts remain native. */
static bool SPUI_TeamGame(){char info[MAX_INFO_STRING];trap->GetConfigString(CS_SERVERINFO,info,sizeof(info));return atoi(Info_ValueForKey(info,"g_gametype"))>=GT_TEAM;}
static bool SPUI_ForceAvailable(){if(!spui.wide)return false;char info[MAX_INFO_STRING];trap->GetConfigString(CS_SERVERINFO,info,sizeof(info));int gametype=atoi(Info_ValueForKey(info,"g_gametype"));return gametype!=GT_HOLOCRON&&gametype!=GT_JEDIMASTER&&!UI_AllForceDisabled(atoi(Info_ValueForKey(info,"g_forcePowerDisable")))&&!(UI_TrueJediEnabled()&&uiJediNonJedi==FORCE_NONJEDI);}
static void SPUI_Cancel(){spui.draft.cancel();spui.field=0;spui.status.clear();SPUI_SyncSelection();}
static bool SPUI_Apply(){
 if(!spui.draft.canApply(SPUI_Live())){spui.status="Player settings changed outside this menu. Reopen Profile to refresh.";return false;}
 if(spui.draft.value.name.empty()){spui.status="Enter a player name.";return false;}
 if(spui.draft.value.model!=spui.draft.base.model){
  if(!sp::validSkin(spui.draft.value.model)){spui.status="This character selection is unavailable.";return false;}
  auto id=spui.draft.value.model;auto slash=id.find('/');auto folder=id.substr(0,slash),skin=id.substr(slash+1);
  if(!SPUI_Exists("models/players/"+folder+"/model.glm")||!SPUI_Exists("models/players/"+folder+"/model_"+skin+".skin")){spui.status="The selected model files are no longer available.";return false;}
  trap->Cvar_Set("model",id.c_str());
 }
 if(spui.draft.value.name!=spui.draft.base.name)trap->Cvar_Set("name",spui.draft.value.name.c_str());
 trap->Cvar_Set("ui_Name",spui.draft.value.name.c_str());
 spui.draft.open(SPUI_Live());spui.field=0;spui.status.clear();return true;
}
static bool SPUI_Appearance(int appearance){
 if(spui.selected<0||spui.variant<0)return false;auto list=spui.catalog.variants(spui.selected,appearance);
 const auto& skins=spui.catalog.models[spui.selected].skins;std::string folder=sp::lower(skins[spui.variant].model);
 for(int index:list)if(sp::lower(skins[index].model)==folder){SPUI_Select(spui.selected,index);return true;}
 spui.status="This outfit has no matching team skin.";return false;
}
static void SPUI_Navigate(int destination){
 menuDef_t* menu=Menu_GetFocused();if(!menu)return;spui.field=0;spui.modal=0;spui.active=false;
 const char* action=destination==510?"sp_action_saber":destination==511?"sp_action_force":destination==421?"sp_action_custom":destination==512?"sp_action_join":destination==513?"sp_action_spectate":destination==514?"sp_action_red":destination==515?"sp_action_blue":NULL;
 if(action){
  itemDef_t* item=Menu_FindItemByName(menu,action);
  if(item&&item->action){
   extern qboolean gTouchedForce;
   if(destination>=512&&destination<=515&&!gTouchedForce){
    // The native setForce script sends a team command only when Force was edited.
    const char* teams[]={"free","s","red","blue"};
    trap->Cmd_ExecuteText(EXEC_APPEND,va("cmd team %s\n",teams[destination-512]));
   }
   Item_RunScript(item,item->action);
  }
  return;
 }
 Menus_CloseByName(spui.menu.c_str());
 if(spui.wide)Menus_OpenByName("ingame");
 else Menus_OpenByName(destination==520?"multiplayermenu":destination==522?"controlsMenu":destination==523?"setup_menu":"main");
}
static void SPUI_RequestNavigation(int destination){
 if(spui.draft.dirty()){spui.destination=destination;spui.modal=1;spui.field=0;spui.focus=1000;}
 else SPUI_Navigate(destination);
}
static void SPUI_Click(int id,int arg){
 const int keyboard=trap->Cvar_VariableValue("st_virtualKeyboard");
 if(id==102||(id==101&&(keyboard==1||(keyboard==0&&trap->Cvar_VariableValue("st_uiPadClick")&&
    !trap->Cvar_VariableValue("st_physicalKeyboard"))))){SPN_Open();return;}
 if(id==100||id==101){spui.field=id;spui.edit=id==100?spui.filter.search:spui.draft.value.name;spui.caret=int(spui.edit.size());spui.replace=id==101;return;}
 spui.field=0;
 if(id>=110&&id<=112){spui.filter.collection=id-110;SPUI_Filter();}
 else if(id==120){spui.filter.reverse=!spui.filter.reverse;SPUI_Filter();}
 else if(id==121){spui.filter=sp::Filter();SPUI_Filter();}
 else if(id>=130&&id<136){spui.filter.themes^=spThemeBits[id-130];SPUI_Filter();}
 else if(id==137){spui.filter.favorites=!spui.filter.favorites;SPUI_Filter();}
 else if(id>=2000&&id<40000)SPUI_Select(arg);
 else if(id>=40000&&id<80000){auto& m=spui.catalog.models[arg];m.favorite=!m.favorite;auto key=sp::favoriteKey(m.key);trap->Cvar_Register(NULL,key.c_str(),"0",CVAR_ARCHIVE);trap->Cvar_Set(key.c_str(),m.favorite?"1":"0");int scroll=spui.scroll;SPUI_Filter();spui.scroll=scroll;}
 else if(id==410||id==411){
  if(spui.selected>=0){int appearance=spui.catalog.models[spui.selected].skins[spui.variant].appearance;auto list=spui.catalog.variants(spui.selected,appearance);auto at=std::find(list.begin(),list.end(),spui.variant);if(!list.empty()){int next=int(at-list.begin())+(id==410?-1:1);next=(next+int(list.size()))%int(list.size());SPUI_Select(spui.selected,list[next]);}}
 }
 else if(id==412){if(spui.selected>=0){int current=spui.catalog.models[spui.selected].skins[spui.variant].appearance;for(int i=1;i<=3;++i)if(SPUI_Appearance((current+i)%3))break;}}
 else if(id==420){spui.motion=!spui.motion;menuDef_t* m=Menu_GetFocused();if(itemDef_t* item=Menu_FindItemByName(m,"st_profile_preview")){if(item->typeData.model)item->typeData.model->rotationSpeed=spui.motion?100:0;}}
 else if(id==500||id==510||id==511||id==421||id==520||id==522||id==523)SPUI_RequestNavigation(id);
 else if(id==501)SPUI_Cancel();
 else if(id==502)SPUI_Apply();
 else if(id==516&&spui.wide&&UI_TrueJediEnabled()){
  // Role changes are an explicit native action, independent of Profile Apply.
  float special=0;UI_OwnerDrawHandleKey(UI_JEDI_NONJEDI,0,&special,A_MOUSE1);
 }
 else if(id==512){spui.modal=2;spui.focus=SPUI_TeamGame()?1011:1010;spui.hits.clear();}
 else if(id>=1010&&id<=1013){if((id==1010&&SPUI_TeamGame())||((id==1011||id==1012)&&!SPUI_TeamGame()))return;spui.modal=0;SPUI_RequestNavigation(id==1010?512:id==1011?514:id==1012?515:513);}
 else if(id==1000){if(SPUI_Apply())SPUI_Navigate(spui.destination);}
 else if(id==1001){SPUI_Cancel();SPUI_Navigate(spui.destination);}
 else if(id==1002){spui.focus=spui.modal==2?512:500;spui.modal=0;}
 else if(id==150||id==151){int total=(int(spui.rows.size())+spui.columns-1)/spui.columns;spui.scroll=std::max(0,std::min(std::max(0,total-spui.visibleRows),spui.scroll+(id==150?-1:1)));}
}
