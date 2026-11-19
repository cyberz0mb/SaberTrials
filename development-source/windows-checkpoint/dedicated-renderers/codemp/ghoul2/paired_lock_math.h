#ifndef ST_PAIRED_LOCK_MATH_H
#define ST_PAIRED_LOCK_MATH_H
// Isolated reference solver: no engine state, animation IDs, timing, or IO.
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace stlock {
static const double pi=3.14159265358979323846;
struct V { double x,y,z; V(double X=0,double Y=0,double Z=0):x(X),y(Y),z(Z){} };
inline V operator+(V a,V b){return V(a.x+b.x,a.y+b.y,a.z+b.z);}
inline V operator-(V a,V b){return V(a.x-b.x,a.y-b.y,a.z-b.z);}
inline V operator*(V a,double b){return V(a.x*b,a.y*b,a.z*b);}
inline V operator/(V a,double b){return a*(1/b);}
inline double dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline V cross(V a,V b){return V(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
inline double length(V a){return std::sqrt(dot(a,a));}
inline double clamp(double a,double lo,double hi){return std::max(lo,std::min(hi,a));}
inline bool finite(V a){return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
inline V unit(V a){double n=length(a);return n>1e-12?a/n:V();}
inline V perpendicular(V a){V b=std::fabs(a.x)<std::fabs(a.y)?V(1,0,0):V(0,1,0);if(std::fabs(a.z)<std::min(std::fabs(a.x),std::fabs(a.y)))b=V(0,0,1);return unit(cross(a,b));}
struct M { V c[3],p; M(){c[0]=V(1,0,0);c[1]=V(0,1,0);c[2]=V(0,0,1);} };
inline V vector(const M&m,V v){return m.c[0]*v.x+m.c[1]*v.y+m.c[2]*v.z;}
inline V point(const M&m,V v){return vector(m,v)+m.p;}
inline M mul(const M&a,const M&b){M o;for(int i=0;i<3;i++)o.c[i]=vector(a,b.c[i]);o.p=point(a,b.p);return o;}
inline M inverse(const M&a){M o;o.c[0]=V(a.c[0].x,a.c[1].x,a.c[2].x);o.c[1]=V(a.c[0].y,a.c[1].y,a.c[2].y);o.c[2]=V(a.c[0].z,a.c[1].z,a.c[2].z);o.p=vector(o,a.p)*-1;return o;}
inline bool affineInverse(const M&a,M&out){
 double det=dot(a.c[0],cross(a.c[1],a.c[2]));if(!std::isfinite(det)||std::fabs(det)<1e-10||!finite(a.p))return false;
 V r0=cross(a.c[1],a.c[2])/det,r1=cross(a.c[2],a.c[0])/det,r2=cross(a.c[0],a.c[1])/det;M m;
 m.c[0]=V(r0.x,r1.x,r2.x);m.c[1]=V(r0.y,r1.y,r2.y);m.c[2]=V(r0.z,r1.z,r2.z);m.p=vector(m,a.p)*-1;out=m;return true;
}
inline bool rigid(const M&m,double e=1e-5){if(!finite(m.p))return false;for(int i=0;i<3;i++){if(!finite(m.c[i])||std::fabs(dot(m.c[i],m.c[i])-1)>e)return false;for(int j=0;j<i;j++)if(std::fabs(dot(m.c[i],m.c[j]))>e)return false;}return dot(cross(m.c[0],m.c[1]),m.c[2])>1-e;}
inline M rotation(V axis,double angle){axis=unit(axis);double c=std::cos(angle),s=std::sin(angle);M o;for(int i=0;i<3;i++){V v=o.c[i];o.c[i]=v*c+cross(axis,v)*s+axis*(dot(axis,v)*(1-c));}return o;}
inline M fromTo(V a,V b){a=unit(a);b=unit(b);V cr=cross(a,b);double sn=length(cr),co=clamp(dot(a,b),-1,1);if(sn<1e-10)return co>0?M():rotation(perpendicular(a),pi);return rotation(cr/sn,std::atan2(sn,co));}
// Compression can introduce slight non-orthogonality. Orthonormalize measured
// input rotations once; never use a transpose as inverse of a scaled matrix.
inline M orthonormal(const M&m){M o;o.p=m.p;o.c[0]=unit(m.c[0]);o.c[1]=unit(m.c[1]-o.c[0]*dot(o.c[0],m.c[1]));o.c[2]=unit(cross(o.c[0],o.c[1]));return o;}
inline void quaternion(const M&in,double q[4]){
 M m=orthonormal(in);double a[3][3]={{m.c[0].x,m.c[1].x,m.c[2].x},{m.c[0].y,m.c[1].y,m.c[2].y},{m.c[0].z,m.c[1].z,m.c[2].z}};
 double trace=a[0][0]+a[1][1]+a[2][2];
 if(trace>0){double s=std::sqrt(trace+1)*2;q[0]=.25*s;q[1]=(a[2][1]-a[1][2])/s;q[2]=(a[0][2]-a[2][0])/s;q[3]=(a[1][0]-a[0][1])/s;}
 else{int i=a[1][1]>a[0][0]?1:0;if(a[2][2]>a[i][i])i=2;int j=(i+1)%3,k=(i+2)%3;double s=std::sqrt(std::max(0.,1+a[i][i]-a[j][j]-a[k][k]))*2;q[0]=(a[k][j]-a[j][k])/s;q[i+1]=.25*s;q[j+1]=(a[j][i]+a[i][j])/s;q[k+1]=(a[k][i]+a[i][k])/s;}
}
// Quaternion nlerp avoids a singular rotation at a 180-degree release blend.
inline M interpolateRigid(const M&a,const M&b,double t){
 double q[4],r[4],s[4],d=0,n=0;quaternion(a,q);quaternion(b,r);for(int i=0;i<4;i++)d+=q[i]*r[i];
 for(int i=0;i<4;i++){s[i]=q[i]*(1-t)+r[i]*t*(d<0?-1:1);n+=s[i]*s[i];}n=std::sqrt(n);for(int i=0;i<4;i++)s[i]/=n;
 double w=s[0],x=s[1],y=s[2],z=s[3];M m;
 m.c[0]=V(1-2*(y*y+z*z),2*(x*y+w*z),2*(x*z-w*y));m.c[1]=V(2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x));m.c[2]=V(2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y));m.p=a.p*(1-t)+b.p*t;return m;
}
enum Status { Ok, InvalidInput, Unreachable, NoFeasibleHilt };
struct Arm { M shoulder,elbow,wrist; V pole; };
struct ArmPose { M shoulder,elbow,wrist; double upperLength,lowerLength; };
inline Status twoBone(const Arm&seed,const M&target,ArmPose&out,double epsilon=1e-4){
 if(!rigid(seed.shoulder)||!rigid(seed.elbow)||!rigid(seed.wrist)||!rigid(target)||!finite(seed.pole))return InvalidInput;
 double a=length(seed.elbow.p-seed.shoulder.p),b=length(seed.wrist.p-seed.elbow.p),d=length(target.p-seed.shoulder.p);
 if(a<epsilon||b<epsilon||d<std::fabs(a-b)+epsilon||d>a+b-epsilon)return Unreachable;
 V dir=unit(target.p-seed.shoulder.p),pole=seed.pole-dir*dot(seed.pole,dir);
 if(length(pole)<1e-6){V e=seed.elbow.p-seed.shoulder.p;pole=e-dir*dot(e,dir);}
 if(length(pole)<1e-6)pole=perpendicular(dir);
 pole=unit(pole);double x=(a*a-b*b+d*d)/(2*d),h=std::sqrt(std::max(0.,a*a-x*x));
 V e=seed.shoulder.p+dir*x+pole*h;
 M ur=fromTo(seed.elbow.p-seed.shoulder.p,e-seed.shoulder.p),lr=fromTo(seed.wrist.p-seed.elbow.p,target.p-e);
 out.shoulder=mul(ur,seed.shoulder);out.shoulder.p=seed.shoulder.p;
 out.elbow=mul(lr,seed.elbow);out.elbow.p=e;out.wrist=target;out.upperLength=a;out.lowerLength=b;return Ok;
}
// Physical joint M = concatenated skin deformation D * bind B.
// GLA local deformation L = inverse(D_parent) * (M_target * inverse(B)).
inline M physicalToLocal(const M&parentDeformation,const M&targetPhysical,const M&inverseBind){return mul(inverse(parentDeformation),mul(targetPhysical,inverseBind));}
// Prefer this overload for actual compressed GLA input: its source matrices can
// contain small quantization errors and need a true affine inverse.
inline Status physicalToLocalChecked(const M&parentDeformation,const M&targetPhysical,const M&inverseBind,M&out){M ip;if(!affineInverse(parentDeformation,ip))return InvalidInput;out=mul(ip,mul(targetPhysical,inverseBind));return Ok;}

struct Blade { V origin,direction; double length,margin; Blade():direction(0,0,1),length(40),margin(1){} };
struct Grip { int arm; M hiltToWrist; Grip():arm(0){} };
struct Weapon { M seedHilt; Blade blade; Grip grips[2]; int count; Weapon():count(1){} };
struct Actor { Arm arms[2]; Weapon weapons[2]; int count; Actor():count(1){} };
struct Config {
 double reachMargin,rotationWeight,wristWeight;
 Config():reachMargin(.05),rotationWeight(8),wristWeight(.25){}
};
struct WeaponPose { M hilt; ArmPose arms[2]; int armIndex[2],count; double bladeContact,contactError,cost; int candidates; };
struct ActorPose { WeaponPose weapons[2]; int count; };
struct PairPose { ActorPose actor[2]; V contact; };
struct WeaponTrack {M firstHilt,lastHilt;double firstDepth,lastDepth,cost;int candidates;};
struct PairTrack {WeaponTrack weapon[2][2];int count[2];V firstContact,lastContact;};
struct Interval {double lo,hi;Interval(double l,double h):lo(l),hi(h){}};
inline void intersect(std::vector<Interval>&is,double lo,double hi){std::vector<Interval> o;for(size_t i=0;i<is.size();i++){double l=std::max(lo,is[i].lo),h=std::min(hi,is[i].hi);if(l<=h)o.push_back(Interval(l,h));}is.swap(o);}
inline void exclude(std::vector<Interval>&is,double lo,double hi){std::vector<Interval> o;for(size_t i=0;i<is.size();i++){if(is[i].lo<=lo)o.push_back(Interval(is[i].lo,std::min(is[i].hi,lo)));if(is[i].hi>=hi)o.push_back(Interval(std::max(is[i].lo,hi),is[i].hi));}is.swap(o);}

// For a fixed hilt rotation R, the contact equation leaves exactly one scalar:
// H.translation = C - R*emitter - t*(R*bladeDirection).
// Each wrist is K - t*d. Intersect its exact two-bone reach intervals, then
// choose the scalar minimizing quadratic displacement from the seed.
inline bool candidate(const Actor&a,const Weapon&w,V contact,const Config&cfg,const M&r,WeaponPose&out){
 V d=unit(vector(r,w.blade.direction)),base=contact-vector(r,w.blade.origin);
 std::vector<Interval> valid(1,Interval(w.blade.margin,w.blade.length-w.blade.margin));
 double optimal=dot(base-w.seedHilt.p,d),weight=1;
 for(int i=0;i<w.count;i++){
  const Arm&arm=a.arms[w.grips[i].arm];V k=base+vector(r,w.grips[i].hiltToWrist.p),off=k-arm.shoulder.p;
  double upper=length(arm.elbow.p-arm.shoulder.p),lower=length(arm.wrist.p-arm.elbow.p);
  double maxR=upper+lower-cfg.reachMargin,minR=std::fabs(upper-lower)+cfg.reachMargin;
  double along=dot(off,d),perp=std::max(0.,dot(off,off)-along*along);
  if(maxR<=minR||perp>maxR*maxR)return false;
  double half=std::sqrt(std::max(0.,maxR*maxR-perp));intersect(valid,along-half,along+half);
  if(perp<minR*minR){double inner=std::sqrt(minR*minR-perp);exclude(valid,along-inner,along+inner);}
  optimal+=cfg.wristWeight*dot(k-arm.wrist.p,d);weight+=cfg.wristWeight;
 }
 if(valid.empty())return false;optimal/=weight;
 double best=std::numeric_limits<double>::infinity();WeaponPose result;
 for(size_t n=0;n<valid.size();n++){
  double t=clamp(optimal,valid[n].lo,valid[n].hi);M h=r;h.p=base-d*t;
  double cost=dot(h.p-w.seedHilt.p,h.p-w.seedHilt.p);
  for(int j=0;j<3;j++)cost+=cfg.rotationWeight*(1-dot(h.c[j],w.seedHilt.c[j]));
  WeaponPose p;p.hilt=h;p.count=w.count;p.bladeContact=t;
  bool ok=true;
  for(int i=0;i<w.count;i++){
   int ai=w.grips[i].arm;M target=mul(h,w.grips[i].hiltToWrist);
   if(twoBone(a.arms[ai],target,p.arms[i])!=Ok){ok=false;break;}
   p.armIndex[i]=ai;V delta=target.p-a.arms[ai].wrist.p;cost+=cfg.wristWeight*dot(delta,delta);
  }
  if(!ok)continue;
  p.contactError=length(point(h,w.blade.origin)+d*t-contact);p.cost=cost;
  if(cost<best){best=cost;result=p;}
 }
 if(!std::isfinite(best))return false;out=result;return true;
}
inline Status solveWeapon(const Actor&a,const Weapon&w,V contact,const Config&cfg,WeaponPose&out){
 if(!finite(contact)||!rigid(w.seedHilt)||w.count<1||w.count>2||!finite(w.blade.origin)||!finite(w.blade.direction)||std::fabs(length(w.blade.direction)-1)>1e-5||!std::isfinite(w.blade.length)||!std::isfinite(w.blade.margin)||w.blade.length<=0||w.blade.margin<0||2*w.blade.margin>=w.blade.length||!std::isfinite(cfg.reachMargin)||!std::isfinite(cfg.wristWeight)||!std::isfinite(cfg.rotationWeight)||cfg.reachMargin<=1e-4||cfg.wristWeight<0||cfg.rotationWeight<0)return InvalidInput;
 for(int i=0;i<w.count;i++){int k=w.grips[i].arm;if(k<0||k>1||!rigid(w.grips[i].hiltToWrist)||!rigid(a.arms[k].shoulder)||!rigid(a.arms[k].elbow)||!rigid(a.arms[k].wrist)||!finite(a.arms[k].pole))return InvalidInput;if(i&&k==w.grips[0].arm)return InvalidInput;}
 M seedR=w.seedHilt;seedR.p=V();V seedDirection=unit(vector(seedR,w.blade.direction));
 V aim=unit(contact-w.seedHilt.p);if(length(aim)<.5)aim=seedDirection;
 V u=perpendicular(aim),v=cross(aim,u);double best=std::numeric_limits<double>::infinity();WeaponPose result;int tested=0;
 auto offer=[&](const M&r){WeaponPose p;++tested;if(candidate(a,w,contact,cfg,r,p)&&p.cost<best){best=p.cost;result=p;}};
 offer(seedR);
 const double cone[]={0,15,30,45,60,90};const double roll[]={0,30,-30,60,-60,90,-90,180};
 for(int c=0;c<6;c++)for(int az=0;az<(c?12:1);az++){
  double theta=cone[c]*pi/180,phi=az*2*pi/12;V d=aim*std::cos(theta)+(u*std::cos(phi)+v*std::sin(phi))*std::sin(theta);
  M aligned=mul(fromTo(seedDirection,d),seedR);
  for(int k=0;k<8;k++)offer(mul(rotation(d,roll[k]*pi/180),aligned));
 }
 if(!std::isfinite(best))return NoFeasibleHilt;
 // Deterministic local improvement of the best rotation. Feasibility remains
 // exact at every evaluation; no arm is stretched to conceal a failed solve.
 for(double step=8;step>=.5;step*=.5){M center=result.hilt;center.p=V();for(int axis=0;axis<3;axis++)for(int sign=-1;sign<=1;sign+=2)offer(mul(rotation(center.c[axis],sign*step*pi/180),center));}
 result.candidates=tested;out=result;return Ok;
}
inline Status solvePair(const Actor actors[2],V contact,const Config&cfg,PairPose&out){
 PairPose result;result.contact=contact;
 for(int actor=0;actor<2;actor++){
  if(actors[actor].count<1||actors[actor].count>2)return InvalidInput;bool used[2]={false,false};result.actor[actor].count=actors[actor].count;
  for(int w=0;w<actors[actor].count;w++){
   const Weapon&wp=actors[actor].weapons[w];if(wp.count<1||wp.count>2)return InvalidInput;
   for(int k=0;k<wp.count;k++){int arm=wp.grips[k].arm;if(arm<0||arm>1||used[arm])return InvalidInput;used[arm]=true;}
   Status s=solveWeapon(actors[actor],wp,contact,cfg,result.actor[actor].weapons[w]);if(s!=Ok)return s;
  }
 }
 out=result;return Ok;
}

// Minimum squared norm on an entire linear segment, not discrete samples.
inline double segmentMinSquared(V p,V q){V delta=q-p;double n=dot(delta,delta),t=n>1e-20?clamp(-dot(p,delta)/n,0,1):0;V v=p+delta*t;return dot(v,v);}
inline bool safeTrack(const Actor&a,const Weapon&w,const Config&cfg,const WeaponPose&first,const WeaponPose&last){
 for(int g=0;g<w.count;g++){
  const Arm&arm=a.arms[w.grips[g].arm];double upper=length(arm.elbow.p-arm.shoulder.p),lower=length(arm.wrist.p-arm.elbow.p);
  double minR=std::fabs(upper-lower)+cfg.reachMargin,maxR=upper+lower-cfg.reachMargin;
  V p=first.arms[g].wrist.p-arm.shoulder.p,q=last.arms[g].wrist.p-arm.shoulder.p;
  if(segmentMinSquared(p,q)<minR*minR-1e-8||std::max(dot(p,p),dot(q,q))>maxR*maxR+1e-8)return false;
  // The seed's preferred elbow plane must not become singular or switch sides
  // anywhere in the interval. A different seed pole is required if it does.
  if(length(arm.pole)<1e-8||segmentMinSquared(cross(arm.pole,p),cross(arm.pole,q))<1e-8)return false;
 }
 return true;
}
inline Status solveWeaponTrack(const Actor&a,const Weapon&w,V firstContact,V lastContact,const Config&cfg,WeaponTrack&out){
 WeaponPose validation;Status valid=solveWeapon(a,w,(firstContact+lastContact)*.5,cfg,validation);if(valid!=Ok)return valid;
 if(!finite(firstContact)||!finite(lastContact))return InvalidInput;
 M seedR=w.seedHilt;seedR.p=V();V sd=unit(vector(seedR,w.blade.direction)),aim=unit((firstContact+lastContact)*.5-w.seedHilt.p);if(length(aim)<.5)aim=sd;
 V u=perpendicular(aim),v=cross(aim,u);WeaponTrack result;double best=std::numeric_limits<double>::infinity();int tested=0;
 auto offer=[&](const M&r){
  ++tested;WeaponPose p,q;if(!candidate(a,w,firstContact,cfg,r,p)||!candidate(a,w,lastContact,cfg,r,q)||!safeTrack(a,w,cfg,p,q))return;
  double cost=p.cost+q.cost;
  if(cost<best){best=cost;result.firstHilt=p.hilt;result.lastHilt=q.hilt;result.firstDepth=p.bladeContact;result.lastDepth=q.bladeContact;result.cost=cost;}
 };
 offer(seedR);M middle=validation.hilt;middle.p=V();offer(middle);
 const double cone[]={0,15,30,45,60,90};const double roll[]={0,30,-30,60,-60,90,-90,180};
 for(int c=0;c<6;c++)for(int az=0;az<(c?12:1);az++){
  double theta=cone[c]*pi/180,phi=az*2*pi/12;V d=aim*std::cos(theta)+(u*std::cos(phi)+v*std::sin(phi))*std::sin(theta);M aligned=mul(fromTo(sd,d),seedR);
  for(int k=0;k<8;k++)offer(mul(rotation(d,roll[k]*pi/180),aligned));
 }
 if(!std::isfinite(best))return NoFeasibleHilt;
 for(double step=8;step>=.5;step*=.5){M center=result.firstHilt;center.p=V();for(int ax=0;ax<3;ax++)for(int sign=-1;sign<=1;sign+=2)offer(mul(rotation(center.c[ax],sign*step*pi/180),center));}
 result.candidates=tested;out=result;return Ok;
}
// Solve this once at lock setup (or bake/cache it for a validated rig/hilt key).
// Both actors use the same pair-space endpoints and canonical progress value.
inline Status solvePairTrack(const Actor actors[2],V firstContact,V lastContact,const Config&cfg,PairTrack&out){
 PairTrack result;result.firstContact=firstContact;result.lastContact=lastContact;
 for(int a=0;a<2;a++){
  if(actors[a].count<1||actors[a].count>2)return InvalidInput;bool used[2]={false,false};result.count[a]=actors[a].count;
  for(int w=0;w<actors[a].count;w++){
   const Weapon&wp=actors[a].weapons[w];if(wp.count<1||wp.count>2)return InvalidInput;
   for(int g=0;g<wp.count;g++){int k=wp.grips[g].arm;if(k<0||k>1||used[k])return InvalidInput;used[k]=true;}
   Status status=solveWeaponTrack(actors[a],wp,firstContact,lastContact,cfg,result.weapon[a][w]);if(status!=Ok)return status;
  }
 }
 out=result;return Ok;
}
// Constant-cost sampling: no candidate search, no arm stretch, no timer changes.
// Hilt orientation is constant and translation/depth are affine, making exact
// blade contact and attachment grip constraints hold between sample frames too.
inline Status samplePairTrack(const Actor actors[2],const PairTrack&track,double progress,PairPose&out){
 if(!std::isfinite(progress)||progress<0||progress>1)return InvalidInput;
 PairPose result;result.contact=track.firstContact+(track.lastContact-track.firstContact)*progress;
 for(int a=0;a<2;a++){
  if(actors[a].count!=track.count[a]||track.count[a]<1||track.count[a]>2)return InvalidInput;result.actor[a].count=track.count[a];
  for(int w=0;w<track.count[a];w++){
   const Weapon&wp=actors[a].weapons[w];const WeaponTrack&t=track.weapon[a][w];if(wp.count<1||wp.count>2||!rigid(t.firstHilt)||!rigid(t.lastHilt)||!std::isfinite(t.firstDepth)||!std::isfinite(t.lastDepth))return InvalidInput;
   for(int k=0;k<wp.count;k++)if(wp.grips[k].arm<0||wp.grips[k].arm>1)return InvalidInput;
   WeaponPose&p=result.actor[a].weapons[w];p.hilt=t.firstHilt;p.hilt.p=t.firstHilt.p+(t.lastHilt.p-t.firstHilt.p)*progress;p.bladeContact=t.firstDepth+(t.lastDepth-t.firstDepth)*progress;p.count=wp.count;p.candidates=0;p.cost=t.cost;
   p.contactError=length(point(p.hilt,wp.blade.origin)+vector(p.hilt,wp.blade.direction)*p.bladeContact-result.contact);
   for(int g=0;g<wp.count;g++){int k=wp.grips[g].arm;p.armIndex[g]=k;Status s=twoBone(actors[a].arms[k],mul(p.hilt,wp.grips[g].hiltToWrist),p.arms[g]);if(s!=Ok)return s;}
  }
 }
 out=result;return Ok;
}
} // namespace stlock
#endif
