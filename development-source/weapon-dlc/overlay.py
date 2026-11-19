"""Wire additive weapons into an existing combined OpenJK source tree."""
from pathlib import Path
import shutil

SOURCE = Path(__file__).resolve().parent


def replace(path, old, new, count=1):
    data = path.read_text()
    assert data.count(old) == count, (path, old[:100], data.count(old), count)
    path.write_text(data.replace(old, new), newline='\n')


def apply(tree, client=False, server=False):
    tree = Path(tree)/'codemp'
    game = tree/'game'
    for name in ('st_dlc_weapons.h', 'bg_st_dlc.inc'):
        shutil.copyfile(SOURCE/name, game/name)
    replace(game/'bg_misc.c', 'const char *bgToggleableSurfaces',
            '#include "bg_st_dlc.inc"\n\nconst char *bgToggleableSurfaces')
    replace(game/'bg_misc.c', 's->time2 = ps->holocronBits;',
            's->time2 = (ps->holocronBits & ((1<<ST_DLC_ENTITY_SHIFT)-1)) |\n'
            '\t\t(ps->stats[ST_DLC_STAT]<<ST_DLC_ENTITY_SHIFT);', 2)
    replace(game/'bg_pmove.c', '\t\tPmoveSingle( pmove );', '\t\tST_DLCPmove( pmove );')
    # These headers are included after each module's own types are declared.
    for header in (game/'g_local.h', tree/'cgame/cg_local.h', tree/'ui/ui_local.h'):
        with header.open('a') as file:
            file.write('\n#include "game/st_dlc_weapons.h"\n')
    if server:
        shutil.copyfile(SOURCE/'g_st_dlc.inc',game/'g_st_dlc.inc')
        replace(game/'g_main.c', 'void G_InitGame( int levelTime, int randomSeed, int restart ) {',
                '#include "g_st_dlc.inc"\n\nvoid G_InitGame( int levelTime, int randomSeed, int restart ) {')
        replace(game/'g_main.c','\tST_Init();','\tST_Init();\n\tST_DLCGameInit();')
        replace(game/'g_active.c','\t\tPmove (&pmove);',
                '\t\tST_DLCUpdateAccess(ent);\n\t\tPmove (&pmove);',2)
        replace(game/'g_missile.c','\tmissile->parent = owner;',
                '\tmissile->parent = owner;\n\tif(owner && owner->client)\n'
                '\t\tmissile->s.time2 = owner->client->ps.stats[ST_DLC_STAT]<<ST_DLC_ENTITY_SHIFT;')
        replace(game/'g_weapon.c','void FireWeapon( gentity_t *ent, qboolean altFire ) {',
                'int st_dlcFiringId, st_dlcFiringAlt;\n'
                'static void ST_DLCBaseFireWeapon( gentity_t *ent, qboolean altFire ) {')
        replace(game/'g_weapon.c','\tmissile->classname = "demp2_alt_proj";',
                '\tmissile->s.time2=ent->client->ps.stats[ST_DLC_STAT]<<ST_DLC_ENTITY_SHIFT;\n'
                '\tmissile->classname = "demp2_alt_proj";')
        replace(game/'g_weapon.c','\t\tefEnt->s.weapon = ent->count*2;',
                '\t\tefEnt->s.weapon = ent->count*2;\n\t\tefEnt->s.time2=ent->s.time2;\n\t\tefEnt->s.eFlags|=EF_ALT_FIRING;')
        replace(game/'g_weapon.c','\t\tG_PlayEffect(EFFECT_EXPLOSION_FLECHETTE, self->r.currentOrigin, v);',
                '\t\tgentity_t *fx=G_PlayEffect(EFFECT_EXPLOSION_FLECHETTE, self->r.currentOrigin, v);\n'
                '\t\tif(fx) { fx->s.time2=self->s.time2; fx->s.eFlags|=EF_ALT_FIRING; }')
        with (game/'g_weapon.c').open('a') as file:
            file.write('''
void FireWeapon(gentity_t *ent,qboolean altFire) {
    int savedId=st_dlcFiringId,savedAlt=st_dlcFiringAlt;
    st_dlcFiringId=ent->client ? ent->client->ps.stats[ST_DLC_STAT] : 0;
    st_dlcFiringAlt=altFire;
    ST_DLCBaseFireWeapon(ent,altFire);
    st_dlcFiringId=savedId; st_dlcFiringAlt=savedAlt;
}
''')
        replace(game/'g_utils.c','\te->s.eType = ET_EVENTS + event;', '''\te->s.eType = ET_EVENTS + event;
    if(st_dlcFiringId && (event==EV_DISRUPTOR_MAIN_SHOT || event==EV_DISRUPTOR_SNIPER_SHOT ||
        event==EV_DISRUPTOR_HIT || event==EV_DISRUPTOR_SNIPER_MISS || event==EV_CONC_ALT_IMPACT)) {
        e->s.time2=st_dlcFiringId<<ST_DLC_ENTITY_SHIFT;
        if(st_dlcFiringAlt) e->s.eFlags|=EF_ALT_FIRING;
    }''',2)
    if client:
        cg=tree/'cgame'
        shutil.copyfile(SOURCE/'cg_st_dlc.inc',cg/'cg_st_dlc.inc')
        replace(cg/'cg_weapons.c','#include "fx_local.h"','#include "fx_local.h"\n#include "cg_st_dlc.inc"')
        replace(cg/'cg_main.c','\tCG_ParseServerinfo();','\tCG_ParseServerinfo();\n\tST_DLCClientInit();')
        replace(cg/'cg_main.c','\tCG_ShutDownG2Weapons();','\tCG_ShutDownG2Weapons();\n\tST_DLCCleanup();')
        replace(cg/'cg_servercmds.c','\tif ( num == CS_MUSIC ) {',
                '\tif ( num == ST_DLC_CONFIGSTRING ) {\n\t\tST_DLCClientInit();\n\t} else if ( num == CS_MUSIC ) {')
        replace(cg/'cg_view.c','trap->SetUserCmdValue( cg.weaponSelect,',
                'trap->SetUserCmdValue( ST_DLCCommandWeapon(cg.weaponSelect),',3)
        for fn,direction in (('CG_NextWeapon_f',1),('CG_PrevWeapon_f',-1)):
            replace(cg/'cg_weapons.c',f'void {fn}( void ) {{',
                    f'void {fn}( void ) {{\n\tif(ST_DLCCycle({direction})) return;')
        # Reset only at the stock assignment, so invalid keys cannot change the selection.
        replace(cg/'cg_weapons.c','\tcg.weaponSelect = num;', '\tst_dlcSelect=0;\n\tcg.weaponSelect = num;',2)
        replace(cg/'cg_weapons.c','\tif (cg.predictedPlayerState.ammo[weaponData[i].ammoIndex] < weaponData[i].energyPerShot &&',
                '\tif (!((cg.predictedPlayerState.stats[ST_DLC_ALLOWED_STAT]&ST_DLC_INFINITE) && ST_DLCGun(i)) &&\n'
                '\t\tcg.predictedPlayerState.ammo[weaponData[i].ammoIndex] < weaponData[i].energyPerShot &&')
        replace(cg/'cg_weapons.c','void CG_OutOfAmmoChange( int oldWeapon )',
                'void ST_DLCOutOfAmmoChange(int oldWeapon)')
        with (cg/'cg_weapons.c').open('a') as file:
            file.write('\nvoid CG_OutOfAmmoChange(int oldWeapon) { st_dlcSelect=0; ST_DLCOutOfAmmoChange(oldWeapon); }\n')
        replace(cg/'cg_weapons.c','void CG_DrawWeaponSelect( void ) {',
                'void CG_DrawWeaponSelect( void ) {\n\tif(ST_DLCCarousel()) return;')
        replace(cg/'cg_weapons.c','\tweapon = &cg_weapons[weaponNum];',
                '\tweapon = ST_DLCWeaponInfo(ST_DLCPlayerId(cent),weaponNum);')
        replace(cg/'cg_weapons.c','\tweapon = &cg_weapons[ ps->weapon ];',
                '\tweapon = ST_DLCWeaponInfo(ps->stats[ST_DLC_STAT],ps->weapon);')
        replace(cg/'cg_weapons.c','\tweap = &cg_weapons[ ent->weapon ];',
                '\tweap = ST_DLCWeaponInfo(ST_DLCEntityId(ent),ent->weapon);')
        replace(cg/'cg_weapons.c','\t\treturn g2WeaponInstances[weapon];',
                '\t\tvoid *dlc=ST_DLCWorld(cent,weapon);\n\t\treturn dlc ? dlc : g2WeaponInstances[weapon];',3)
        replace(cg/'cg_ents.c','\t\tweapon = &cg_weapons[s1->weapon];',
                '\t\tweapon = ST_DLCWeaponInfo(ST_DLCEntityId(s1),s1->weapon);')
        replace(cg/'cg_event.c','\t\tif ( es->emplacedOwner )',
                '\t\tif(ST_DLCImpact(es,position,dir)) { }\n\t\telse if ( es->emplacedOwner )',3)
        for event in ('EV_DISRUPTOR_HIT','EV_DISRUPTOR_SNIPER_MISS'):
            anchor=f'\t\tDEBUGNAME("{event}");\n\t\tByteToDir( es->eventParm, dir );'
            replace(cg/'cg_event.c',anchor,anchor+'\n\t\tif(ST_DLCHitscanImpact(es,WP_DISRUPTOR,position,dir)) break;')
        for func,alt,extra in (('FX_DisruptorMainShot',0,''),('FX_DisruptorAltShot',1,', cent->currentState.shouldtarget')):
            anchor=f'\t\t{func}( cent->currentState.origin2, cent->lerpOrigin{extra} );'
            replace(cg/'cg_event.c',anchor,
                    f'\t\tif(!ST_DLCBeam(es,WP_DISRUPTOR,{alt},cent->currentState.origin2,cent->lerpOrigin))\n'+anchor)
        replace(cg/'cg_event.c','\t\t\tCG_MissileHitWall(WP_CONCUSSION, es->owner, position, dir, IMPACTSOUND_DEFAULT, qtrue, 0);',
                '\t\t\tif(!ST_DLCHitscanImpact(es,WP_CONCUSSION,position,dir))\n'
                '\t\t\tCG_MissileHitWall(WP_CONCUSSION, es->owner, position, dir, IMPACTSOUND_DEFAULT, qtrue, 0);')
        replace(cg/'cg_event.c','\t\t\tvec3_t spot;',
                '\t\t\tvec3_t spot;\n\t\t\tqboolean dlcBeam=ST_DLCBeam(es,WP_CONCUSSION,1,es->origin2,position);')
        replace(cg/'cg_event.c','\t\t\tfor (dist = 0.0f; dist < shotDist; dist += 64.0f)',
                '\t\t\tif(!dlcBeam)\n'
                '\t\t\tfor (dist = 0.0f; dist < shotDist; dist += 64.0f)')
        replace(cg/'cg_event.c','\t\t\tFX_ConcAltShot(es->origin2, spot);',
                '\t\t\tif(!dlcBeam) FX_ConcAltShot(es->origin2, position);')
        replace(cg/'cg_event.c','\t\tcase EFFECT_EXPLOSION_DEMP2ALT:\n\t\t\tFX_DEMP2_AltDetonate',
                '\t\tcase EFFECT_EXPLOSION_DEMP2ALT:\n'
                '\t\t\tif(ST_DLCHitscanImpact(es,WP_DEMP2,cent->lerpOrigin,es->angles)) { eID=-1; break; }\n'
                '\t\t\tFX_DEMP2_AltDetonate')
        replace(cg/'cg_event.c','\t\tcase EFFECT_EXPLOSION_FLECHETTE:',
                '\t\tcase EFFECT_EXPLOSION_FLECHETTE:\n'
                '\t\t\tif(ST_DLCHitscanImpact(es,WP_FLECHETTE,cent->lerpOrigin,es->angles)) { eID=-1; break; }')
        replace(cg/'cg_consolecmds.c','\t{ "tcmd",', '\t{ "st_weaponinfo", ST_DLCInspect },\n\t{ "tcmd",')
        hud=cg/'cg_sabertrials_hud.inc'
        if hud.exists():
            replace(hud,'static const char *ST_HudWeaponName(int weapon) {',
                    'static const char *ST_HudWeaponName(int weapon) {\n'
                    '    static char dlcName[64];\n'
                    '    int id=cg.snap ? cg.snap->ps.stats[ST_DLC_STAT] : 0;\n'
                    '    if(id && ST_DLCBase(id)==weapon && st_dlcWeapons[id].available) {\n'
                    '        Q_strncpyz(dlcName,st_dlcWeapons[id].name,sizeof(dlcName));\n'
                    '        return Q_strupr(dlcName);\n    }')
            replace(hud,'        if (ammo < 0) Q_strncpyz(number, "--", sizeof(number));',
                    '        if (ammo < 0 || ((ps->stats[ST_DLC_ALLOWED_STAT]&ST_DLC_INFINITE) && ST_DLCGun(weapon))) Q_strncpyz(number, "--", sizeof(number));')
