/* Main-menu perimeter animation, independent of renderer/game state. */
#ifndef ST_MAIN_CORE_H
#define ST_MAIN_CORE_H
#include <algorithm>
#include <cmath>
#include <vector>
namespace stmain {
struct Point {float x,y;};
inline float segment(Point a,Point b,float sx,float sy){float x=(b.x-a.x)*sx,y=(b.y-a.y)*sy;return std::sqrt(x*x+y*y);}
inline float length(const std::vector<Point>& path,float sx,float sy){float n=0;for(size_t i=1;i<path.size();++i)n+=segment(path[i-1],path[i],sx,sy);return n;}
inline Point sample(const std::vector<Point>& path,float fraction,float sx,float sy){
 if(path.empty())return {0,0};float total=length(path,sx,sy);if(total<=0)return path.front();
 float distance=(fraction-std::floor(fraction))*total;
 for(size_t i=1;i<path.size();++i){float part=segment(path[i-1],path[i],sx,sy);if(part>0&&distance<=part){float t=distance/part;return {path[i-1].x+(path[i].x-path[i-1].x)*t,path[i-1].y+(path[i].y-path[i-1].y)*t};}distance-=part;}
 return path.back();
}
inline float phase(int time,bool motion,int period){return motion&&period>0?float(time%period)/period:0.f;}
}
#endif
