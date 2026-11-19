#include "st_chat_layout.h"

static bool SSUI_ChatSetting(int index){
 return !strcmp(ssSettings[index].group,"Chat") && ssSettings[index].tab==2;
}

static void SSUI_ChatPic(float x,float y,float w,float h,float u,float v,float u2,float v2,
                        qhandle_t shader,const float* tint){
 if(!shader)return;
 trap->R_SetColor(tint);
 trap->R_DrawStretchPic(x,y,w,h,u,v,u2,v2,shader);
 trap->R_SetColor(NULL);
}

static void SSUI_ChatPreview(){
 float values[4]={};
 int next=0;
 for(int i=0;i<SS_COUNT&&next<4;++i)
  if(SSUI_ChatSetting(i))values[next++]=SSUI_Call(101,i).number;
 const auto layout=ST_ChatLayout(values[0],values[1],values[2],values[3]);
 const float x=315, s=layout.size, w=layout.width*.54f, h=layout.height*.80f, y=404-h;
 const float aspect=uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;
 const float left=x+6.5f*s, messageScale=.45f*s, timeScale=.33f*s;
 const float textX=left+Text_Width("[21:37]",timeScale,FONT_SMALL2)+8*aspect*s;
 vec4_t timeColor={.51f,.77f,.89f,1}, textColor={1,1,1,1};
 const vec4_t backdrop={.034f,.081f,.102f,1};
 const vec4_t stripe={.045f,.10f,.125f,1};
 UI_FillRect(x,213,298,196,backdrop);
 UI_FillRect(x,250,298,16,stripe);
 UI_FillRect(x,340,298,16,stripe);
 SCUI_Text(x,188,.59f,"Live preview",scuMuted);
 ST_ChatDrawFrame(SSUI_ChatPic,trap->R_RegisterShaderNoMip(ST_CHAT_FILL),
   trap->R_RegisterShaderNoMip(ST_CHAT_FRAME),x,y,w,h,.54f*s,.80f*s,layout.opacity);
 SSUI_ChatPic(x,y-8.8f*s,81.6f*aspect*s,20.8f*s,0,0,1,1,trap->R_RegisterShaderNoMip(ST_CHAT_HEADER),NULL);
 SCUI_Text(x+25.6f*aspect*s,y-4*s,.49f*s,"CHAT",ruWhite);
 static const char* messages[]={"^7Hisoka: ^2Meet by the stairs.",
  "^7Sousuke Aizen: ^2Just passing through.","^7Akaza: ^2I'll be there soon.",
  "^7Hisoka: ^2See you there.","^7Akaza: ^2Ready when you are."};
 const int rows=std::min(5,std::max(1,int((layout.height-20*s)/(16*s))));
 for(int i=0;i<rows;++i){
  const float textY=y+(10+12.8f*i)*s;
  Text_Paint(left,textY+1,timeScale,timeColor,i<2?"[21:37]":"[21:38]",0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_SMALL2);
  UI_FillRect(textX-4*aspect*s,textY,.4f,8*s,timeColor);
  std::string message=messages[i];
  const float available=x+w-7*s-textX;
  if(Text_Width(message.c_str(),messageScale,FONT_SMALL2)>available){
   while(message.size()>18&&Text_Width((message+"...").c_str(),messageScale,FONT_SMALL2)>available)message.pop_back();
   if(message.back()=='^')message.pop_back();
   message+="...";
  }
  Text_Paint(textX,textY,messageScale,textColor,message.c_str(),0,0,ITEM_TEXTSTYLE_OUTLINED,FONT_SMALL2);
 }
}
