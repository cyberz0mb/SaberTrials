#include "st_match_server_policy.h"
#include <cassert>
#ifdef NDEBUG
#error Match Rules tests require active assertions.
#endif
int main() {
 using namespace stmatch;
 Draft d;
 assert(d.set("fraglimit","25")&&d.restart());
 assert(!d.set("g_gametype","2")&&!d.set("ui_dedicated","1"));
 assert(!d.set("g_password","123")&&!d.set("g_allowVote","1;quit"));
 d.armed=true;assert(d.force(2,0)&&!d.armed);assert(!d.force(18,3));
 assert(!d.weapons(1<<3)&&!d.weapons(-1)&&d.weapons(1<<5));
 assert(!d.text("map","../bad")&&!d.text("rotation","mp/ffa1;quit"));
 assert(!d.text("hostname","bad\nquit")&&!d.text("rotation","mp/ffa1\nmp/ffa2"));
 assert(d.text("rotation","mp/ffa1 mp/ffa2 mp/ffa1"));
 assert(d.text("password","")&&d.text("hostname","Host's server"));
 std::array<int,ForceCount> caps;caps.fill(3);caps[2]=0;caps[1]=1;
 assert(forceMask(2,caps)==(1<<2));assert(forceMask(0,caps)==163833);
 assert(freeSpeed(2,0,true,3)==0&&freeSpeed(2,1,true,0)==1);
 assert(forceCap(2,1,3)==1&&forceCap(2,3,1)==1&&forceCap(1,0,2)==2);
 assert(weaponMask(2,1<<5)==(1<<5)&&weaponMask(0,0)==524274);
 assert(spawnHealth(0,0,125)==125&&spawnShield(0,-1,100)==100);
 assert(spawnHealth(0,250,125)==250&&spawnShield(0,0,100)==0);
 assert(spawnHealth(7,500,80)==80&&spawnShield(7,500,10)==10);
 assert(respawnAt(0,2700,1000,5000)==6000&&respawnAt(3,2700,1000,5000)==2700);
 assert(teamAllowed(6,3,4)&&!teamAllowed(6,3,5)&&!teamAllowed(8,8,4));
 assert(entryAllowed(6,1,3,false,true,1,1,5));
 assert(!entryAllowed(6,1,2,false,false,0,0,0));
 assert(!entryAllowed(6,3,2,true,true,3,0,0));
 assert(!entryAllowed(8,3,1,true,false,0,2,2));
 assert(entryAllowed(8,1,1,false,false,0,2,2));
 d.clear();assert(d.edits.empty()&&!d.armed);assert(d.set("st_allowTeamSwitch","0")&&!d.restart());
 return 0;
}
