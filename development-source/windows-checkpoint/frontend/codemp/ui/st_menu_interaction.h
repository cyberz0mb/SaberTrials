/* Shared native menu interactions; no game state or configuration writes. */
#ifndef ST_MENU_INTERACTION_H
#define ST_MENU_INTERACTION_H
#include <algorithm>
#include <cmath>
namespace stmenu {
struct Scrollbar {float x,y,w,h,thumb,grab;int maximum;bool visible,dragging;};
inline void configure(Scrollbar& b,float x,float y,float w,float h,float visible,int maximum,float minimum=24){
 maximum=std::max(0,maximum);
 if(b.x!=x||b.y!=y||b.w!=w||b.h!=h||b.maximum!=maximum)b.dragging=false;
 b.x=x;b.y=y;b.w=w;b.h=h;b.maximum=maximum;b.visible=maximum>0&&h>0;
 b.thumb=b.visible?std::min(h,std::max(minimum,h*visible/(visible+maximum))):h;
 if(!b.visible)b.dragging=false;
}
inline float thumbY(const Scrollbar& b,int position){return b.y+(b.h-b.thumb)*std::max(0,std::min(b.maximum,position))/std::max(1,b.maximum);}
inline void move(Scrollbar& b,float y,int& position){
 if(!b.dragging||!b.visible)return;
 float travel=b.h-b.thumb;if(travel<=0){position=0;return;}
 float ratio=std::max(0.f,std::min(1.f,(y-b.y-b.grab)/travel));position=int(std::lround(ratio*b.maximum));
}
inline bool begin(Scrollbar& b,float x,float y,int& position){
 if(!b.visible||x<b.x||x>b.x+b.w||y<b.y||y>b.y+b.h)return false;
 float top=thumbY(b,position);b.grab=y>=top&&y<=top+b.thumb?y-top:b.thumb/2;b.dragging=true;move(b,y,position);return true;
}
inline void pulse(int time,const float* white,const float* cyan,float* out){
 float mix=(1.f-std::cos(float(time%1200)*6.28318530718f/1200.f))*.5f;
 for(int i=0;i<4;++i)out[i]=white[i]+(cyan[i]-white[i])*mix;
}
}
#endif
