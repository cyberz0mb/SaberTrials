/* UI and cgame watch only non-secret presentation cvars. No login authority. */
#include "st_presentation_policy.inc"
typedef void (*STPReadCvar)(const char*,char*,int);
static STPNotice stpNotice;
static void STP_ObserveNotices(STPReadCvar read,int now) {
 static int initialized;
 static char previous[8][256];
 static const char*keys[]={"ui_stAccountStatus","st_uiHudStatus","st_uiPortraitStatus","st_uiInputStatus","st_uiPhotoStatus","ui_ste55","ui_ste11","st_uiPresentationNotice"};
 int i;char value[256];
 for(i=0;i<8;i++){
  read(keys[i],value,sizeof(value));
  if(initialized&&value[0]&&strcmp(value,previous[i])){
   if(i==0){
    if(!strcmp(value,"Signed out."))STP_NoticePush(&stpNotice,"Logged out.",0,now);
    else {char signedIn[8],name[128],notice[192];read("ui_stAccountSignedIn",signedIn,sizeof(signedIn));
     if(!strcmp(value,"Signed in with Discord.")&&!strcmp(signedIn,"1")){read("ui_stAccountName",name,sizeof(name));snprintf(notice,sizeof(notice),"Logged in as %.100s.",name);STP_NoticePush(&stpNotice,notice,0,now);}
     else STP_NoticePush(&stpNotice,value,1,now);
    }
   }else if(i==6){if(previous[i][0])STP_NoticePush(&stpNotice,!strcmp(value,"Unready")?"Ready selected.":"Ready cleared.",0,now);}
   else if(i>=5)STP_NoticePush(&stpNotice,value,i==7?0:1,now);
   else if(strstr(value,"applied."))STP_NoticePush(&stpNotice,value,0,now);
   else if(!strncmp(value,"Enter ",6)||!strncmp(value,"Use ",4))STP_NoticePush(&stpNotice,value,2,now);
  }
  strncpy(previous[i],value,sizeof(previous[i])-1);previous[i][sizeof(previous[i])-1]=0;
 }
 initialized=1;
}
