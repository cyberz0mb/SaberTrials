#include "st_main_core.h"
#include <cassert>
#include <cmath>
#include <iostream>
int main(){
 using namespace stmain;
 std::vector<Point> rectangle={{0,0},{10,0},{10,5},{0,5},{0,0}};
 auto near=[](float a,float b){return std::fabs(a-b)<.001f;};
 assert(near(length(rectangle,2,1),50));
 auto p=sample(rectangle,.4f,2,1);assert(near(p.x,10)&&near(p.y,0));
 p=sample(rectangle,.5f,2,1);assert(near(p.x,10)&&near(p.y,5));
 p=sample(rectangle,1.f,2,1);assert(near(p.x,0)&&near(p.y,0));
 p=sample(rectangle,-.5f,2,1);assert(near(p.x,10)&&near(p.y,5));
 assert(phase(0,false,9000)==phase(1234,false,9000));
 assert(phase(0,true,9000)!=phase(1234,true,9000));
 assert(near(phase(9000,true,9000),0));
 assert(near(phase(9500,true,9000),phase(500,true,9000)));
 assert(length({},1,1)==0);assert(sample({},.5f,1,1).x==0);
 std::vector<Point> still={{4,7},{4,7}};p=sample(still,.9f,1,1);assert(p.x==4&&p.y==7);
 std::cout<<"Perimeter corners, wrap, aspect, motion-off and period checks passed\n";
}
