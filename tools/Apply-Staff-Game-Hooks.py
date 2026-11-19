"""One-time maintainer migration of accepted overlays. Refuses duplicate hooks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'development-source/bot-roles/codemp/game'
UPSTREAM=ROOT/'dist/staff-work/OpenJK-1a6a643427aa347553e9073dac5570b33337c4d9/codemp/game'
def edit(file,old,new):
    p=GAME/file
    if not p.exists():p.write_bytes((UPSTREAM/file).read_bytes())
    s=p.read_text()
    if s.count(old)!=1:raise RuntimeError(f'{file}: hook count {s.count(old)} for {old[:50]}')
    p.write_text(s.replace(old,new,1),newline='\n')
edit('g_local.h','extern gameImport_t *trap;','extern gameImport_t *trap;\n#include "g_staff.h"')
for file,marker,guard in [
 ('g_active.c','void ClientThink_real( gentity_t *ent ) {','if (ST_StaffThink(ent)) return;'),
 ('g_active.c','void ClientEndFrame( gentity_t *ent ) {','if (ST_StaffThink(ent)) return;'),
 ('g_active.c','void ClientImpacts( gentity_t *ent, pmove_t *pmove ) {','if (ST_StaffBlocked(ent)) return;'),
 ('g_active.c','void\tG_TouchTriggers( gentity_t *ent ) {','if (ST_StaffBlocked(ent)) return;'),
 ('g_combat.c','void G_Damage( gentity_t *targ, gentity_t *inflictor, gentity_t *attacker, vec3_t dir, vec3_t point, int damage, int dflags, int mod ) {','if (ST_StaffBlocked(targ) || ST_StaffBlocked(attacker) || ST_StaffBlocked(inflictor)) return;'),
 ('g_cmds.c','void Cmd_Kill_f( gentity_t *ent ) {','if (ST_StaffBlocked(ent)) return;'),
 ('g_cmds.c','void SetTeam( gentity_t *ent, char *s ) {','if (ST_StaffBlocked(ent)) return;'),
 ('g_client.c','void ClientSpawn(gentity_t *ent) {','if (ST_StaffBlocked(ent)) return;'),
 ('g_client.c','void ClientDisconnect( int clientNum ) {','ST_StaffClearClient(clientNum);'),
 ('g_items.c','void Touch_Item (gentity_t *ent, gentity_t *other, trace_t *trace) {','if (ST_StaffBlocked(other)) return;'),
 ('g_mover.c','qboolean\tG_TryPushingEntity( gentity_t *check, gentity_t *pusher, vec3_t move, vec3_t amove ) {','if (ST_StaffBlocked(check)) return qtrue;'),
 ('w_force.c','int ForcePowerUsableOn(gentity_t *attacker, gentity_t *other, forcePowers_t forcePower)\n{','if (ST_StaffBlocked(attacker) || ST_StaffBlocked(other)) return 0;'),
 ('w_force.c','qboolean WP_ForcePowerUsable( gentity_t *self, forcePowers_t forcePower )\n{','if (ST_StaffBlocked(self)) return qfalse;'),
 ('w_force.c','void WP_ForcePowersUpdate( gentity_t *self, usercmd_t *ucmd )\n{','if (ST_StaffBlocked(self)) return;'),
]:edit(file,marker,marker+'\n    '+guard)
edit('g_cmds.c','\t//rww - redirect bot commands','''    if (ST_StaffBlocked(ent) && Q_stricmp(cmd,"say") && Q_stricmp(cmd,"say_team") && Q_stricmp(cmd,"tell") && Q_stricmp(cmd,"score")) {
        trap->SendServerCommand(clientNum,"print \\\"Command unavailable while frozen or in ghost mode.\\n\\\"");
        return;
    }
\t//rww - redirect bot commands'''.replace('\\\"','\\"'))
p=ROOT/'development-source/client-game/codemp/cgame/cg_draw.c';s=p.read_text();marker='\tif (ST_PhotoActive()) { ST_PhotoDraw(); return; }';assert s.count(marker)==1
s=s.replace(marker,marker+'''\n    if (cg.snap && cg.snap->ps.stats[15]) {
        CG_DrawProportionalString(320,28,cg.snap->ps.stats[15]==2 ? "STAFF GHOST - NONCOMBAT" : "FROZEN BY STAFF",UI_CENTER|UI_SMALLFONT|UI_DROPSHADOW,colorTable[CT_CYAN]);
    }''',1);p.write_text(s,newline='\n')
print('Applied narrowly scoped staff movement/interaction hooks; installed files unchanged')
