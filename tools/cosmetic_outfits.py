"""Build the cosmetic-only PK3 and stage the Profile and client adapters."""
from pathlib import Path
from shutil import copyfile
from struct import unpack_from
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "development-source/compatibility"
PACK = ROOT / "assets/cosmetics/SaberTrials-Cosmetics.pk3"


def collect(archive):
    PACK.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as origin, ZipFile(PACK, "w") as out:
        for n in sorted(origin.namelist()):
            path=n.lower()
            image=path.startswith(("models/cosmetics/hats/","models/cosmetics/capes/")) and path.endswith((".md3",".tga",".jpg",".png"))
            if not image and path not in ("shaders/japro_capes.shader","shaders/japro_hats.shader"):
                continue
            entry=ZipInfo(path,(2026,1,1,0,0,0))
            out.writestr(entry,origin.read(n),compress_type=ZIP_DEFLATED)


def edit(path, anchor, replacement):
    source=path.read_text()
    if replacement in source: return
    if source.count(anchor)!=1: raise ValueError(f"{path.name}: expected one {anchor[:75]}")
    path.write_text(source.replace(anchor,replacement))


def include(folder, plain):
    copyfile(SOURCE/plain,folder/("st_"+plain))


def stage_engine(tree):
    client=tree/"codemp/client"
    for name in ("wearable_id.h","wearable_wire.inc"): include(client,name)
    main=client/"cl_main.cpp"
    edit(main,'#include "ja_client.inc"','#include "ja_client.inc"\n#include "st_wearable_wire.inc"')
    mark='Info_SetValueForKey( info, ST_BSP_CAPABILITY_KEY, ST_BSP_CAPABILITY );'
    edit(main,mark,mark+'\n        ST_OutfitUserinfo(info);')
    edit(main,'JA_Userinfo(info);','JA_Userinfo(info);\n        ST_OutfitUserinfo(info);')
    edit(main,'\tJA_CheckUserinfo();','''\tJA_CheckUserinfo();
    if (Cvar_VariableIntegerValue("st_outfitRefresh")) {
        Cvar_Set("st_outfitRefresh","0");
        cvar_modifiedFlags |= CVAR_USERINFO;
    }''')
    check='void CL_CheckUserinfo( void ) {'
    edit(main,check,check+'''
    static bool outfitActive;
    bool active=cls.state==CA_ACTIVE;
    if (active && !outfitActive) {
        char key[2*MAX_QPATH+16];
        ST_OutfitKey(Cvar_VariableString("model"),key,sizeof(key));
        if (*Cvar_VariableString(key)) cvar_modifiedFlags |= CVAR_USERINFO;
    }
    outfitActive=active;''')
    # Independently named UI-only models/materials allow local preview of the
    # bundled catalog on every server. World renderer paths still use normal FS.
    win=tree/"codemp/win32"
    dest=win/"outfit-preview"
    dest.mkdir(exist_ok=True)
    table=[];resources=[]
    with ZipFile(PACK) as z:
        for i,n in enumerate(sorted(n for n in z.namelist() if n.startswith("models/")),7100):
            name=n.replace("models/cosmetics/","st_outfits/",1)
            data=z.read(n)
            if n.endswith(".md3"):
                data=bytearray(data)
                surfaces=unpack_from("<i",data,84)[0]
                ofs=unpack_from("<i",data,100)[0]
                for _ in range(surfaces):
                    count=unpack_from("<i",data,ofs+76)[0]
                    start=ofs+unpack_from("<i",data,ofs+92)[0]
                    for j in range(count):
                        at=start+68*j
                        old=bytes(data[at:at+64]).split(b"\0",1)[0]
                        new=old.lower().replace(b"models/cosmetics/",b"st_outfits/",1)
                        if len(new)>=64: raise ValueError(n)
                        data[at:at+64]=new.ljust(64,b"\0")
                    ofs+=unpack_from("<i",data,ofs+104)[0]
            f=f"{i}.bin";(dest/f).write_bytes(data)
            resources.append(f'{i} RCDATA "outfit-preview/{f}"')
            table.append(f'{{"{name}",{i}}},')
    # The engine binary-searches this array, including its earlier gfx entries.
    resources_inc=client/"full_ui_resources.inc"
    original=[line for line in resources_inc.read_text().splitlines() if '"st_outfits/' not in line and line.strip()]
    resources_inc.write_text("\n".join(sorted(original+table,key=str.upper))+"\n")
    (win/"st_wearable_resources.rc").write_text("\n".join(resources)+"\n")
    rc=win/"openjk.rc"
    if '#include "st_wearable_resources.rc"' not in rc.read_text():
        with rc.open("a") as f:f.write('\n#include "st_wearable_resources.rc"\n')
    full=client/"full_ui.inc"
    edit(full,'if(Q_stricmpn(path,"fonts/",6) &&','if(Q_stricmpn(path,"st_outfits/",11) && Q_stricmpn(path,"fonts/",6) &&')


def stage_ui(tree):
    ui=tree/"codemp/ui"
    for name in ("wearable_id.h","wearable_draw.inc","wearable_ui.inc"):include(ui,name)
    with ZipFile(PACK) as z:
        rows=[f'{{{int("/capes/" in n)},"{Path(n).stem}"}},' for n in sorted(z.namelist()) if n.endswith(".md3")]
    (ui/"st_wearable_catalog.inc").write_text("\n".join(rows))
    profile=ui/"ui_st_profile.inc"
    edit(profile,'#include "ui_st_emotes.inc"','#include "st_wearable_ui.inc"\n#include "ui_st_emotes.inc"')
    edit(profile,'if(spui.modal)SPUI_Click(1002,0);','if(outfits.open)ST_OutfitClick(716,0);\n  else if(spui.modal)SPUI_Click(1002,0);')
    # Track navigation away from Profile, including external menu changes.
    edit(profile,'static void SPUI_Start(){','static void ST_ResetOutfits();\nstatic void SPUI_Start(){\n ST_ResetOutfits();')
    edit(profile,'#include "ui_st_emotes.inc"','#include "ui_st_emotes.inc"\nstatic void ST_ResetOutfits(){outfits.open=false;}')
    actions=ui/"ui_st_profile_actions.inc"
    edit(actions,'static void SPUI_Click(int id,int arg){','static void SPUI_Click(int id,int arg){\n if(id==718){ST_OpenOutfits();return;}\n if(outfits.open){ST_OutfitClick(id,arg);return;}')
    draw=ui/"ui_st_profile_draw.inc"
    edit(draw,'if(emui.editing){EM_DrawEditor();return;}','if(outfits.open){ST_OutfitPage();return;}\n if(emui.editing){EM_DrawEditor();return;}')
    edit(draw,'SPUI_Button(22,447,68,18,"Back",500);','SPUI_Button(325,447,94,18,"Cosmetics",718);\n SPUI_Button(22,447,68,18,"Back",500);')
    for word in ('spui.status.c_str()','"Pending changes"'):
        a='spui.wide?157:99,451,258,.45f,'+word if word.startswith('spui') else 'spui.wide?157:99,451,258,.46f,'+word
        edit(draw,a,a.replace(',258,',',162,'))
    shared=ui/"ui_shared.c"
    edit(shared,'\tDC->addRefEntityToScene( &ent );','''#ifndef _CGAME
    extern void ST_DrawOutfitPreview(const itemDef_t *,const refEntity_t *,const vec3_t);
    ST_DrawOutfitPreview(item,&ent,angles);
#endif
\tDC->addRefEntityToScene( &ent );''')


def stage_cgame(tree):
    cg=tree/"codemp/cgame"
    for name in ("wearable_id.h","wearable_draw.inc","wearable_game.inc"): include(cg,name)
    player=cg/"cg_players.c"
    marker='void CG_NewClientInfo( int clientNum, qboolean entitiesInitialized ) {'
    edit(player,marker,'#include "st_wearable_game.inc"\n'+marker)
    marker='configstring = CG_ConfigString( clientNum + CS_PLAYERS );'
    edit(player,marker,marker+'\n\tST_ReadWearables(clientNum,configstring);')
    marker='CG_CheckThirdPersonAlpha( cent, &legs );\n\t\ttrap->R_AddRefEntityToScene(&legs);'
    edit(player,marker,marker+'\n\t\tST_DrawPlayerWearables(cent,&legs);')
