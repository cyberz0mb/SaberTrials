/* Text-only options and native heart icons. Input fields retain their borders. */
static void MSUI_Color(float* color,bool selected,bool focused,bool enabled=true){
 if(!enabled)memcpy(color,scuMuted,sizeof(vec4_t));
 else if(focused)stmenu::pulse(uiInfo.uiDC.realTime,scuText,scuCyan,color);
 else memcpy(color,selected?scuCyan:scuText,sizeof(vec4_t));
}
// Cache supersampled coverage at the actual screen-pixel size. Drawing binary
// menu-unit rows produces stair steps when the menu is scaled to widescreen.
#include <map>
#include <vector>
static void MSUI_Heart(float x,float y,float width,bool favorite,bool focused){
 struct Mask {std::vector<unsigned char> fill,outline;};static std::map<int,Mask> cache;
 int size=std::max(8,std::min(128,int(std::lround(width*uiInfo.uiDC.xscale))));
 auto found=cache.find(size);
 if(found==cache.end()){
  Mask mask;mask.fill.resize(size*size);mask.outline.resize(size*size);
  auto inside=[&](float px,float py){float u=px/size*2.6f-1.3f,v=1.3f-py/size*2.6f,q=u*u+v*v-1;return q*q*q-u*u*v*v*v<=0;};
  float stroke=std::max(1.f,size*.06f),diagonal=stroke*.70710678f;
  for(int j=0;j<size;++j)for(int i=0;i<size;++i){int fill=0,edge=0;
   for(int sy=0;sy<8;++sy)for(int sx=0;sx<8;++sx){float px=i+(sx+.5f)/8,py=j+(sy+.5f)/8;
    if(!inside(px,py))continue;++fill;
    bool inner=inside(px-stroke,py)&&inside(px+stroke,py)&&inside(px,py-stroke)&&inside(px,py+stroke)&&
     inside(px-diagonal,py-diagonal)&&inside(px+diagonal,py-diagonal)&&inside(px-diagonal,py+diagonal)&&inside(px+diagonal,py+diagonal);
    if(!inner)++edge;
   }
   mask.fill[j*size+i]=(unsigned char)((fill*255+32)/64);mask.outline[j*size+i]=(unsigned char)((edge*255+32)/64);
  }
  found=cache.emplace(size,std::move(mask)).first;
 }
 const auto& pixels=favorite?found->second.fill:found->second.outline;
 vec4_t color;const vec4_t red={.95f,.08f,.15f,1};if(favorite)memcpy(color,red,sizeof(color));else MSUI_Color(color,false,focused);
 float left=std::round(x*uiInfo.uiDC.xscale),top=std::round(y*uiInfo.uiDC.yscale),alpha=color[3];
 for(int j=0;j<size;++j)for(int i=0;i<size;){unsigned char coverage=pixels[j*size+i];int start=i++;
  while(i<size&&pixels[j*size+i]==coverage)++i;
  if(coverage){color[3]=alpha*coverage/255.f;UI_FillRect((left+start)/uiInfo.uiDC.xscale,(top+j)/uiInfo.uiDC.yscale,(i-start)/uiInfo.uiDC.xscale,1.f/uiInfo.uiDC.yscale,color);}
 }
}
