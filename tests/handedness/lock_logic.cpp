#include "st_lock_logic.h"
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <initializer_list>
static bool near(float a,float b){return fabsf(a-b)<.0001f;}
int main(){
    float a[3]={10,20,5},b[3]={56,20,5},scale[3]={1,1,1};
    float af[3],al[3],bf[3],bl[3];
    assert(ST_LockContacts(a,b,a,0,scale,af,al));
    assert(ST_LockContacts(a,b,b,180,scale,bf,bl));
    for(int n=0;n<=64;n++){
        float p=n/64.f;
        float ax=a[0]+af[0]*(1-p)+al[0]*p;
        float bx=b[0]-(bf[0]*(1-p)+bl[0]*p);
        assert(near(ax,bx));
    }
    assert(near(af[2],32)); assert(near(bf[2],32));
    assert(near(ST_LockProgress(120,100,40,1),.5));
    assert(near(ST_LockProgress(130,100,40,0),.25));
    assert(near(ST_LockProgress(90,100,40,1),0));
    assert(near(ST_LockProgress(145,100,40,1),1));
    assert(!ST_LockContacts(a,a,a,0,scale,af,al));
    // Each side must reconstruct the other's actual skeleton, even when sizes
    // differ. Verify against independent local -> world -> local calculations.
    for(int angle=0;angle<360;angle+=15)for(float sa: {.75f,1.0f,1.25f})for(float sb: {.75f,1.0f,1.25f}) {
        float as[3]={sa,sa,sa},bs[3]={sb,sb,sb},ab[3][4],ba[3][4];
        float ay=(float)angle,by=ay+137;
        assert(ST_LockOpponentTransform(a,ay,as,b,by,bs,ab));
        assert(ST_LockOpponentTransform(b,by,bs,a,ay,as,ba));
        float v[3]={13,-7,29},w[3],back[3];
        for(int i=0;i<3;i++)w[i]=ab[i][3]+ab[i][0]*v[0]+ab[i][1]*v[1]+ab[i][2]*v[2];
        for(int i=0;i<3;i++)back[i]=ba[i][3]+ba[i][0]*w[0]+ba[i][1]*w[1]+ba[i][2]*w[2];
        for(int i=0;i<3;i++)assert(near(back[i],v[i]));
        float ar=ay*.01745329251994329577f,br=by*.01745329251994329577f;
        assert(near(a[0]+sa*(cosf(ar)*w[0]-sinf(ar)*w[1]),b[0]+sb*(cosf(br)*v[0]-sinf(br)*v[1])));
        assert(near(a[1]+sa*(sinf(ar)*w[0]+cosf(ar)*w[1]),b[1]+sb*(sinf(br)*v[0]+cosf(br)*v[1])));
        assert(near(a[2]+sa*w[2],b[2]+sb*v[2]));
    }
    float badScale[3]={1,2,1},transform[3][4];
    assert(!ST_LockOpponentTransform(a,0,scale,b,180,badScale,transform));
    badScale[1]=NAN;
    assert(!ST_LockOpponentTransform(a,0,badScale,b,180,scale,transform));
    puts("canonical lock progress and shared contact tests passed");
}
