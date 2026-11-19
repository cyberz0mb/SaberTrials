#ifndef ST_PAIRED_LOCK_CLEARANCE_H
#define ST_PAIRED_LOCK_CLEARANCE_H
#include "paired_lock_math.h"
namespace stlock {
struct Capsule {V a,b;double radius;Capsule(V A,V B,double R):a(A),b(B),radius(R){}};
struct LockGeometry {
 std::vector<Capsule> bodies;std::vector<Blade> blades;
 V forward,lateral,origin;int hand,role;
 LockGeometry():forward(1,0,0),lateral(0,1,0),hand(0),role(0){}
};
inline double pointSegmentSquared(V p,V a,V b){V d=b-a;double n=dot(d,d),t=n>1e-20?clamp(dot(p-a,d)/n,0,1):0;V q=p-a-d*t;return dot(q,q);}
inline double segmentSegmentSquared(V p,V q,V a,V b){
 V d=q-p,e=b-a,r=p-a;double A=dot(d,d),E=dot(e,e),f=dot(e,r),s=0,t=0;
 if(A<=1e-20&&E<=1e-20)return dot(r,r);
 if(A<=1e-20)t=clamp(f/E,0,1);
 else{double c=dot(d,r);if(E<=1e-20)s=clamp(-c/A,0,1);else{double B=dot(d,e),den=A*E-B*B;if(den>1e-20)s=clamp((B*f-c*E)/den,0,1);t=(B*s+f)/E;if(t<0){t=0;s=clamp(-c/A,0,1);}else if(t>1){t=1;s=clamp((B-c)/A,0,1);}}}
 V z=r+d*s-e*t;return dot(z,z);
}
inline double pointTriangleSquared(V p,V a,V b,V c){
 V ab=b-a,ac=c-a,n=cross(ab,ac);double nn=dot(n,n);
 if(nn>1e-20){double dist=dot(p-a,n);V q=p-n*(dist/nn);V aq=q-a;double d00=dot(ab,ab),d01=dot(ab,ac),d11=dot(ac,ac),d20=dot(aq,ab),d21=dot(aq,ac),den=d00*d11-d01*d01;double v=(d11*d20-d01*d21)/den,w=(d00*d21-d01*d20)/den;if(v>=0&&w>=0&&v+w<=1)return dist*dist/nn;}
 return std::min(pointSegmentSquared(p,a,b),std::min(pointSegmentSquared(p,b,c),pointSegmentSquared(p,c,a)));
}
inline double segmentTriangleSquared(V p,V q,V a,V b,V c){
 V n=cross(b-a,c-a);double den=dot(n,q-p);
 if(std::fabs(den)>1e-16){double t=dot(n,a-p)/den;if(t>=0&&t<=1&&pointTriangleSquared(p+(q-p)*t,a,b,c)<1e-14)return 0;}
 double d=std::min(pointTriangleSquared(p,a,b,c),pointTriangleSquared(q,a,b,c));
 return std::min(d,std::min(segmentSegmentSquared(p,q,a,b),std::min(segmentSegmentSquared(p,q,b,c),segmentSegmentSquared(p,q,c,a))));
}
// Constant hilt rotation + linear translation sweeps every blade into an
// exact parallelogram, so capsule clearance holds between all sampled frames.
inline bool clearSweptSegment(V a0,V b0,V a1,V b1,const std::vector<Capsule>&caps,double radius){
 for(size_t i=0;i<caps.size();i++){const Capsule&c=caps[i];double r=c.radius+radius;
  if(std::min(segmentTriangleSquared(c.a,c.b,a0,b0,b1),segmentTriangleSquared(c.a,c.b,a0,b1,a1))<r*r)return false;
 }return true;
}
inline bool clearWeaponTrack(const LockGeometry&g,const M&a,const M&b){
 for(size_t i=0;i<g.blades.size();i++){const Blade&v=g.blades[i];V a0=point(a,v.origin),a1=point(b,v.origin),d=vector(a,v.direction)*v.length;
  if(!clearSweptSegment(a0,a0+d,a1,a1+d,g.bodies,.7))return false;
 }
 // The real emitter offsets also bound the solid hilt dead span.
 for(size_t i=0;i<g.blades.size();i++)if(!clearSweptSegment(a.p,point(a,g.blades[i].origin),b.p,point(b,g.blades[i].origin),g.bodies,1.2))return false;
 return true;
}
inline double resolveContactLift(V first,V last,const std::vector<Capsule>&caps){
 double minimumRadius=std::numeric_limits<double>::infinity();for(size_t i=0;i<caps.size();i++)minimumRadius=std::min(minimumRadius,caps[i].radius);
 double margin=minimumRadius*.15;bool penetrates=false;
 for(size_t i=0;i<caps.size();i++){double r=caps[i].radius+margin;V a=caps[i].a,b=caps[i].b,f=first,l=last;a.z=b.z=f.z=l.z=0;if(segmentSegmentSquared(f,l,a,b)<r*r)penetrates=true;}
 if(!penetrates)return 0;
 // Keep the contact path outside the vertical footprint of either body.
 // A low contact beneath a leaning head can otherwise force a rising blade
 // through that head, especially when the actor grows but its blade does not.
 // Choose the lowest horizontal plane above the two seed envelopes.
 // Radius-relative padding is invariant under either actor's uniform scale.
 double lift=0;for(size_t i=0;i<caps.size();i++)lift=std::max(lift,std::max(caps[i].a.z,caps[i].b.z)+caps[i].radius+margin-std::min(first.z,last.z));return lift;
}
inline bool clearHandLane(const Weapon&w,const M&a,const M&b,V center,const LockGeometry&g,double margin){
 for(int i=0;i<w.count;i++)if(std::max(dot(point(a,w.grips[i].hiltToWrist.p)-center,g.forward),dot(point(b,w.grips[i].hiltToWrist.p)-center,g.forward))>-margin)return false;
 return true;
}
inline Status solveClearLockTrack(const Actor&a,const Weapon&original,V first,V last,const Config&cfg,const LockGeometry&g,WeaponTrack&out){
 Weapon w=original;V center=(first+last)*.5;
 w.seedHilt.p=center-g.forward*8+g.lateral*(g.hand?6:-6)+V(0,0,g.role?5:-5);
 w.blade.margin=std::min(std::max(w.blade.margin,8.),w.blade.length*.3);
 WeaponPose validation;Status valid=solveWeapon(a,w,center,cfg,validation);if(valid!=Ok&&valid!=NoFeasibleHilt)return valid;
 M seedR=w.seedHilt;seedR.p=V();V sd=unit(vector(seedR,w.blade.direction));V aim=unit(center-w.seedHilt.p),u=perpendicular(aim),v=cross(aim,u);
 WeaponTrack result;double best=std::numeric_limits<double>::infinity();int tested=0;
 auto offer=[&](const M&r){
  V d=vector(r,w.blade.direction);
  for(int bias=-2;bias<=2;bias++){
   ++tested;Weapon shifted=w;shifted.seedHilt.p=w.seedHilt.p+d*(bias*5.);WeaponPose p,q;
   if(!candidate(a,shifted,first,cfg,r,p)||!candidate(a,shifted,last,cfg,r,q)||!safeTrack(a,w,cfg,p,q)||!clearHandLane(w,p.hilt,q.hilt,center,g,5.)||!clearWeaponTrack(g,p.hilt,q.hilt))continue;
   V dp=p.hilt.p-w.seedHilt.p,dq=q.hilt.p-w.seedHilt.p;double cost=dot(dp,dp)+dot(dq,dq);
   for(int ax=0;ax<3;ax++)cost+=cfg.rotationWeight*2*(1-dot(r.c[ax],original.seedHilt.c[ax]));
   if(cost<best){best=cost;result.firstHilt=p.hilt;result.lastHilt=q.hilt;result.firstDepth=p.bladeContact;result.lastDepth=q.bladeContact;result.cost=cost;}
  }
 };
 offer(seedR);if(valid==Ok){M middle=validation.hilt;middle.p=V();offer(middle);}
 const double cone[]={0,15,30,45,60,90,120,150,180};const double roll[]={0,30,-30,60,-60,90,-90,180};
 for(int c=0;c<9;c++)for(int az=0;az<((c&&c<8)?12:1);az++){
  double theta=cone[c]*pi/180,phi=az*2*pi/12;V d=aim*std::cos(theta)+(u*std::cos(phi)+v*std::sin(phi))*std::sin(theta);M aligned=mul(fromTo(sd,d),seedR);
  for(int k=0;k<8;k++)offer(mul(rotation(d,roll[k]*pi/180),aligned));
 }
 // A narrow clearance corridor can lie between the coarse directions.
 // Refine the angular grid only when the ordinary bounded search found none.
 if(!std::isfinite(best))for(int c=0;c<=18;c++)for(int az=0;az<((c&&c<18)?36:1);az++){
  double theta=c*pi/18,phi=az*2*pi/36;V d=aim*std::cos(theta)+(u*std::cos(phi)+v*std::sin(phi))*std::sin(theta);M aligned=mul(fromTo(sd,d),seedR);
  for(int k=0;k<24;k++)offer(mul(rotation(d,k*pi/12),aligned));
 }
 if(!std::isfinite(best))return NoFeasibleHilt;
 for(double step=8;step>=.5;step*=.5){M centerR=result.firstHilt;centerR.p=V();for(int ax=0;ax<3;ax++)for(int sign=-1;sign<=1;sign+=2)offer(mul(rotation(centerR.c[ax],sign*step*pi/180),centerR));}
 result.candidates=tested;out=result;return Ok;
}
inline Status solveClearGuardTrack(const Actor&a,const Weapon&w,V contact,const Config&cfg,const LockGeometry&g,const Weapon&primary,const WeaponTrack&locked,WeaponTrack&out){
 if(w.count!=1)return InvalidInput;int arm=w.grips[0].arm;double side=arm?1:-1;
 LockGeometry protectedGeometry=g;
 for(int i=0;i<primary.count;i++)protectedGeometry.bodies.push_back(Capsule(point(locked.firstHilt,primary.grips[i].hiltToWrist.p),point(locked.lastHilt,primary.grips[i].hiltToWrist.p),2.8));
 V desired=unit(g.forward*.12+g.lateral*(side*.68)+V(0,0,.72));M seedR=w.seedHilt;seedR.p=V();M base=mul(fromTo(vector(seedR,w.blade.direction),desired),seedR);
 double best=std::numeric_limits<double>::infinity();WeaponTrack result;int tested=0;
 for(int pitch=-1;pitch<=1;pitch++)for(int yaw=-1;yaw<=1;yaw++)for(int roll=-2;roll<=2;roll++){
  M r=mul(rotation(g.lateral,pitch*pi/8),mul(rotation(V(0,0,1),yaw*pi/8),mul(rotation(desired,roll*pi/4),base)));
  for(int f=6;f<=14;f+=4)for(int l=6;l<=14;l+=4)for(int z=-10;z<=2;z+=4){
   ++tested;V target=a.arms[arm].shoulder.p+g.forward*f+g.lateral*(side*l)+V(0,0,z);M h=r;h.p=target-vector(r,w.grips[0].hiltToWrist.p);ArmPose pose;
   if(twoBone(a.arms[arm],mul(h,w.grips[0].hiltToWrist),pose)!=Ok||!clearHandLane(w,h,h,contact,g,7.)||!clearWeaponTrack(protectedGeometry,h,h))continue;
   // Keep the guard grip away from both primary grips throughout progress.
   bool ok=true;for(int i=0;i<primary.count;i++)if(pointSegmentSquared(target,point(locked.firstHilt,primary.grips[i].hiltToWrist.p),point(locked.lastHilt,primary.grips[i].hiltToWrist.p))<64)ok=false;
   if(!ok)continue;
   // The stationary guard arm must also clear the moving primary blade.
   std::vector<Capsule>guardArm;guardArm.push_back(Capsule(pose.elbow.p,target,2.3));guardArm.push_back(Capsule(target,target,2.8));
   V p0=point(locked.firstHilt,primary.blade.origin),p1=point(locked.lastHilt,primary.blade.origin),pd=vector(locked.firstHilt,primary.blade.direction)*primary.blade.length;
   if(!clearSweptSegment(p0,p0+pd,p1,p1+pd,guardArm,.7))continue;
   V goal=a.arms[arm].shoulder.p+g.forward*8+g.lateral*(side*9)+V(0,0,-5),delta=target-goal;double cost=dot(delta,delta);
   for(int ax=0;ax<3;ax++)cost+=cfg.rotationWeight*(1-dot(r.c[ax],base.c[ax]));
   if(cost<best){best=cost;result.firstHilt=result.lastHilt=h;result.firstDepth=result.lastDepth=-1;result.cost=cost;}
  }
 }
 if(!std::isfinite(best))return NoFeasibleHilt;result.candidates=tested;out=result;return Ok;
}
}
#endif
