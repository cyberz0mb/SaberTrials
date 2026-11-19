#ifndef ST_LOCK_LOGIC_H
#define ST_LOCK_LOGIC_H
#include <math.h>
/* Match the existing scaled player render-origin lift on both sides. This
 * changes only model/bolt coordinates, never player movement or lock rules. */
static inline void ST_LockModelOrigin(const float base[3],const float scale[3],float out[3]) {
    out[0]=base[0];out[1]=base[1];out[2]=base[2]+24.0f*((scale[2]?scale[2]:1.0f)-1.0f);
}
static inline float ST_LockUniformScale(const float scale[3]) {
    float u=scale[0]?scale[0]:1.0f;
    int i;
    if(!isfinite(u)||u<=0)return 0;
    for(i=1;i<3;i++)if(!isfinite(scale[i])||fabsf((scale[i]?scale[i]:1.0f)-u)>.0001f)return 0;
    return u;
}
/* Map the opponent's unscaled yaw-local skeleton into this actor's frame.
 * This uses authoritative/snapshot transforms, never another draw's bone cache. */
static inline int ST_LockOpponentTransform(const float actor[3],float yaw,const float scale[3],
    const float opponent[3],float opponentYaw,const float opponentScale[3],float out[3][4]) {
    float own=ST_LockUniformScale(scale),other=ST_LockUniformScale(opponentScale);
    float c,s,d,dc,ds,ratio,x,y;
    int i;
    if(!own||!other||!isfinite(yaw)||!isfinite(opponentYaw))return 0;
    for(i=0;i<3;i++)if(!isfinite(actor[i])||!isfinite(opponent[i]))return 0;
    c=cosf(yaw*.01745329251994329577f);s=sinf(yaw*.01745329251994329577f);
    d=(opponentYaw-yaw)*.01745329251994329577f;dc=cosf(d);ds=sinf(d);ratio=other/own;
    x=opponent[0]-actor[0];y=opponent[1]-actor[1];
    out[0][0]=ratio*dc;out[0][1]=-ratio*ds;out[0][2]=0;out[0][3]=(c*x+s*y)/own;
    out[1][0]=ratio*ds;out[1][1]=ratio*dc;out[1][2]=0;out[1][3]=(-s*x+c*y)/own;
    out[2][0]=0;out[2][1]=0;out[2][2]=ratio;out[2][3]=(opponent[2]-actor[2])/own;
    return 1;
}
/* Canonical lock frame progress. No changes to game rules or frame counters. */
static inline float ST_LockProgress(int frame,int first,int count,int incrementsToWin) {
    float p=count>0?(float)(frame-first)/(float)count:.5f;
    if(p<0)p=0; if(p>1)p=1;
    return incrementsToWin?p:1.0f-p;
}
/* Endpoints in the actor's yaw-local, unscaled G2 frame. The pair uses the
 * lower entity ID as A, so each side reconstructs exactly the same world path. */
static inline int ST_LockContacts(const float a[3],const float b[3],
    const float actor[3],float yaw,const float scale[3],float first[3],float last[3]) {
    float dx=b[0]-a[0],dy=b[1]-a[1],len=sqrtf(dx*dx+dy*dy),c,s;
    int endpoint,j;
    if(!isfinite(len)||len<.001f||!isfinite(yaw))return 0;
    c=cosf(yaw*.01745329251994329577f);s=sinf(yaw*.01745329251994329577f);
    for(endpoint=0;endpoint<2;endpoint++) {
        float offset=endpoint?4.0f:-4.0f;
        float x=(a[0]+b[0])*.5f+offset*dx/len-actor[0];
        float y=(a[1]+b[1])*.5f+offset*dy/len-actor[1];
        float *out=endpoint?last:first;
        out[0]=c*x+s*y;out[1]=-s*x+c*y;
        out[2]=(a[2]+b[2])*.5f+32.0f-actor[2];
        for(j=0;j<3;j++) {
            if(!isfinite(out[j])||!isfinite(scale[j])||scale[j]<0)return 0;
            if(scale[j]!=0)out[j]/=scale[j];
        }
    }
    return 1;
}
#endif
