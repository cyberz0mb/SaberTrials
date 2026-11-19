/* Profile layout: permanent Theme sidebar offline, compact filters in-game. */
static void SPUI_Tooltip(){
 int row=spui.mouse?spui.hover:(spui.focus>=2000&&spui.focus<40000?spui.focus-2000:-1);
 if(row<0||row>=int(spui.catalog.models.size())||(spui.mouse&&uiInfo.uiDC.realTime-spui.hoverTime<450))return;
 const auto& m=spui.catalog.models[row];std::string theme;
 for(int i=0;i<5;++i)if(m.themes&spThemeBits[i]){if(!theme.empty())theme+=", ";theme+=spThemeNames[i];}
 if(theme.empty())theme="Uncategorized";
 std::vector<std::string> lines;if(!m.universe.empty())lines.push_back("Universe: "+m.universe);lines.push_back("Themes: "+theme);
 float x=spui.mouse?uiInfo.uiDC.cursorx+9:spui.gridX+12,y=spui.mouse?uiInfo.uiDC.cursory+12:spui.gridY+6;
 float width=0;for(const auto& line:lines)width=std::max(width,float(RUI_Width(line.c_str(),.47f)));width=std::min(250.f,width+14);float height=14.f*lines.size()+12;x=std::max(12.f,std::min(628.f-width,x));y=std::max(12.f,std::min(434.f-height,y));
 UI_FillRect(x,y,width,height,scuInk);
 for(size_t i=0;i<lines.size();++i)SCUI_Fit(x+7,y+6+14*i,width-14,.47f,lines[i].c_str(),scuText);
}
static void SPUI_Draw(){
 if(!SPUI_IsMenu())return;if(!spui.active)SPUI_Start();
 spui.hits.clear();
 RUI_Shell();
 if(!spui.wide){
  SPUI_Button(211,17,64,26,"Play",520);SPUI_Button(278,17,64,26,"Profile",0,0,true,false);SPUI_Button(345,17,64,26,"Controls",522);SPUI_Button(412,17,64,26,"Setup",523);
  SCUI_Text(33,57,.95f,"Profile",scuText);
 }
 float identityY=spui.wide?58.f:85.f,toolbarY=spui.wide?92.f:116.f;
 SCUI_Text(22,identityY+5,.56f,"Name",scuMuted);SPUI_Field(66,identityY,202,101,spui.draft.value.name);
 if(spui.wide&&UI_TrueJediEnabled())SPUI_Button(276,identityY,118,22,uiJediNonJedi==FORCE_NONJEDI?"Role: Non-Jedi":"Role: Jedi",516);
 SPUI_Button(402,identityY,65,22,"Customize",421);
 SPUI_Button(473,identityY,62,22,"Sabers",510,0,false,!spui.wide||uiForcePowersRank[FP_SABER_OFFENSE]>0||ui_freeSaber.integer!=0);
 SPUI_Button(541,identityY,77,22,"Force",511,0,false,SPUI_ForceAvailable());
 SPUI_Field(22,toolbarY,260,100,spui.filter.search.empty()&&spui.field!=100?"Search models or outfits...":spui.filter.search);
 SPUI_Button(290,toolbarY,34,23,"All",110,0,spui.filter.collection==0);
 SPUI_Button(324,toolbarY,40,23,"Base",111,0,spui.filter.collection==1);
 SPUI_Button(364,toolbarY,40,23,"DLC",112,0,spui.filter.collection==2);
 SPUI_Button(412,toolbarY,66,23,spui.filter.reverse?"Sort Z-A":"Sort A-Z",120);
 if(spui.wide){
  SPUI_Button(486,toolbarY,59,23,"Favorites",137,0,spui.filter.favorites);
  SPUI_Button(551,toolbarY,67,23,"Reset filters",121);
 }else SPUI_Button(486,toolbarY,132,23,"Reset filters",121);
 spui.columns=spui.wide?5:4;spui.gridX=spui.wide?22.f:147.f;spui.gridW=spui.wide?424.f:299.f;
 spui.gridY=spui.wide?177.f:174.f;spui.gridH=251;spui.rowH=82;spui.visibleRows=3;
 if(spui.wide){
  float x=22;const float widths[]={51,54,56,58,56,86};
  for(int i=0;i<6;++i){SPUI_Button(x,124,widths[i],20,spThemeNames[i],130+i,0,(spui.filter.themes&spThemeBits[i])!=0);x+=widths[i]+4;}
 }else{
  SCUI_Text(22,153,.57f,"Themes",scuText);
  for(int i=0;i<6;++i){float y=176+i*27;bool checked=(spui.filter.themes&spThemeBits[i])!=0;

   bool focus=SPUI_Over(22,y,110,22)||(!spui.mouse&&spui.focus==130+i);
   RUI_Control(22,y,110,22,"action",checked,focus);
   vec4_t color;MSUI_Color(color,checked,focus);
   SCUI_Fit(26,y+5,89,.49f,spThemeNames[i],color);
   char number[16];Com_sprintf(number,sizeof(number),"%d",spui.themeCounts[i]);SCUI_Fit(119,y+5,16,.43f,number,scuMuted);
   SPUI_Hit(22,y,110,22,130+i);
  }
  SPUI_Button(22,357,110,24,"Favorites",137,0,spui.filter.favorites);
  UI_FillRect(138,150,1,278,scuLine);
 }
 char count[80];Com_sprintf(count,sizeof(count),"%d %s",int(spui.rows.size()),spui.rows.size()==1?"model":"models");
 SCUI_Text(spui.gridX,spui.gridY-19,.56f,count,scuText);
 int total=(int(spui.rows.size())+spui.columns-1)/spui.columns;
 spui.scroll=std::max(0,std::min(std::max(0,total-spui.visibleRows),spui.scroll));
 float cellW=(spui.gridW-15-6*(spui.columns-1))/spui.columns;
 if(spui.rows.empty())SCUI_Fit(spui.gridX+4,spui.gridY+30,spui.gridW-20,.54f,"No models match these filters.",scuMuted);
 for(int slot=0;slot<spui.columns*spui.visibleRows;++slot){
  int index=spui.scroll*spui.columns+slot;if(index>=int(spui.rows.size()))break;
  int row=spui.rows[index];const auto& model=spui.catalog.models[row];
  float x=spui.gridX+(slot%spui.columns)*(cellW+6),y=spui.gridY+(slot/spui.columns)*spui.rowH;
  UI_FillRect(x,y+58,cellW,18,scuPanel);
  const vec4_t corner={1,.76f,.24f,.9f};UI_FillRect(x+2,y+2,7,.5f,corner);UI_FillRect(x+2,y+2,.5f,6,corner);
  const auto& skin=model.skins[row==spui.selected&&spui.variant>=0?spui.variant:0];
  if(!skin.icon.empty()){
   int shader=trap->R_RegisterShaderNoMip(skin.icon.c_str());trap->R_SetColor(NULL);
   if(shader){
    float source=SPUI_IconAspect(skin.icon),target=(cellW-2)*uiInfo.uiDC.xscale/(57*uiInfo.uiDC.yscale),s=1,t=1;
    // Center-crop proportionally using the actual pixel aspect of this viewport.
    if(target>source)t=source/target;else s=target/source;
    trap->R_DrawStretchPic(x+1,y+1,cellW-2,57,(1-s)/2,(1-t)/2,(1+s)/2,(1+t)/2,shader);
   }
  }
  vec4_t color;MSUI_Color(color,row==spui.selected,SPUI_Over(x,y,cellW,76)||(!spui.mouse&&spui.focus==2000+row));
  SCUI_Fit(x+4,y+61,cellW-8,.43f,model.name.c_str(),color);
  if(row==spui.selected)UI_FillRect(x+4,y+75,std::min(cellW-8.f,22.f),1,scuCyan);
  SPUI_Hit(x,y,cellW,76,2000+row,row);
  MSUI_Heart(x+cellW-14,y+4,8,model.favorite,SPUI_Over(x+cellW-18,y+2,17,20)||(!spui.mouse&&spui.focus==40000+row));
  SPUI_Hit(x+cellW-18,y+2,17,20,40000+row,row);
 }
 float scrollX=spui.gridX+spui.gridW-10;
 SPUI_Button(scrollX,spui.gridY,10,17,"^",150);
 SPUI_Button(scrollX,spui.gridY+spui.gridH-17,10,17,"v",151);
 stmenu::configure(spui.scrollbar,scrollX,spui.gridY+21,10,spui.gridH-43,float(spui.visibleRows),std::max(0,total-spui.visibleRows),15);
 UI_FillRect(scrollX+4,spui.gridY+21,2,spui.gridH-43,scuLine);
 if(total>spui.visibleRows){float track=spui.gridH-43,h=std::max(15.f,track*spui.visibleRows/total),pos=(track-h)*spui.scroll/(total-spui.visibleRows);UI_FillRect(scrollX+2,spui.gridY+21+pos,6,h,scuCyan);}
 UI_FillRect(455,150,1,278,scuLine);
 RUI_Control(466,150,152,194,"panel",false,false);
 std::string title=spui.selected>=0?spui.catalog.models[spui.selected].name:"Current custom character";
 SCUI_Fit(466,354,152,.61f,title.c_str(),scuText);
 if(SPUI_Var("ui_stProfilePreviewAvailable")=="0")SCUI_Fit(470,250,144,.51f,"Preview unavailable",scuMuted);
 if(spui.selected>=0&&spui.variant>=0){
  const auto& model=spui.catalog.models[spui.selected];const auto& skin=model.skins[spui.variant];
  auto variants=spui.catalog.variants(spui.selected,skin.appearance);
  if(variants.size()>1){SPUI_Button(466,376,18,20,"<",410);SCUI_Fit(489,381,106,.44f,skin.label.c_str(),scuText);SPUI_Button(600,376,18,20,">",411);}
  std::string appearance=skin.appearance==1?"Team skin: Red":skin.appearance==2?"Team skin: Blue":"Team skin: Default";
  bool multiple=false;for(const auto& candidate:model.skins)if(candidate.appearance>0&&sp::lower(candidate.model)==sp::lower(skin.model))multiple=true;
  SPUI_Button(466,400,152,20,appearance.c_str(),412,0,false,multiple);
  SPUI_Features();
  SCUI_Text(466,425,.43f,"Custom sounds",scuMuted);SCUI_Fit(555,425,63,.43f,spui.sounds?"Detected":"No files",scuText);
 }
 SPUI_Button(22,447,68,18,"Back",500);
 if(spui.wide)SPUI_Button(97,447,52,18,"Join",512);
 if(!spui.status.empty())SCUI_Fit(spui.wide?157:99,451,258,.45f,spui.status.c_str(),scuGold);
 else if(spui.draft.dirty())SCUI_Fit(spui.wide?157:99,451,258,.46f,"Pending changes",scuMuted);
 SPUI_Button(426,447,104,18,"Cancel changes",501,0,false,spui.draft.dirty());
 SPUI_Button(538,447,80,18,"Apply",502,0,spui.draft.dirty(),spui.draft.dirty());
 if(!spui.modal){if(spui.mouse)SPUI_Mouse();SPUI_Tooltip();}
 else{
  // Modal painting and hit targets cover the complete surface; no click-through.
  spui.hits.clear();UI_FillRect(145,167,350,152,scuInk);spui.scrollbar.dragging=false;
  RUI_Control(145,167,350,152,"panel",false,false);
  if(spui.modal==1){
   SCUI_Fit(160,184,320,.70f,"Pending changes",scuCyan);
   SCUI_Fit(160,210,320,.52f,"Apply or discard before leaving?",scuMuted);
   RUI_Divider(160,231,320);
   SPUI_Button(160,248,155,24,"Apply and continue",1000,0,true);SPUI_Button(324,248,155,24,"Discard and continue",1001);SPUI_Button(250,284,140,22,"Stay here",1002);
  }else{
   SCUI_Fit(160,184,320,.70f,"Join",scuCyan);
   RUI_Divider(160,210,320);
   if(SPUI_TeamGame()){
    SPUI_Button(184,225,124,24,"Red team",1011);SPUI_Button(332,225,124,24,"Blue team",1012);
    SPUI_Button(184,269,124,24,"Spectate",1013);SPUI_Button(332,269,124,24,"Cancel",1002);
   }else{
    SPUI_Button(184,225,124,24,"Join game",1010,0,true);SPUI_Button(332,225,124,24,"Spectate",1013);
    SPUI_Button(258,269,124,24,"Cancel",1002);
   }
  }
 }
}
