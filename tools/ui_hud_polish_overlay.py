"""Apply the server information, HUD, and legacy text changes to a pinned build."""
import shutil


def wire(frontend, engine, game, source, insert):
    cg = frontend / 'codemp/cgame'
    ui = frontend / 'codemp/ui'
    for folder in (ui, engine/'codemp/ui'):
        shutil.copyfile(source/'setup/st_setup_catalog.h', folder/'st_setup_catalog.h')
        shutil.copyfile(source/'controls/st_controls_catalog.h', folder/'st_controls_catalog.h')
    authored_cg = source/'client-game/codemp/cgame'
    shutil.copyfile(authored_cg/'cg_st_chat_panel.inc', cg/'cg_st_chat_panel.inc')
    options = [line for line in (authored_cg/'cg_xcvar.h').read_text().splitlines()
               if line.startswith(('XCVAR_DEF( st_chatOpacity,', 'XCVAR_DEF( st_chatSize,'))]
    assert len(options) == 2
    insert(cg/'cg_xcvar.h', 'XCVAR_DEF( st_hudStyle,', '\n'.join(options)+'\nXCVAR_DEF( st_hudStyle,')
    insert(cg/'cg_local.h', '#define\tMAX_CHATBOX_ITEMS\t\t5', '#define\tMAX_CHATBOX_ITEMS\t\t24')
    insert(cg/'cg_local.h', '\tchatBoxItem_t\t\tchatItems[MAX_CHATBOX_ITEMS];',
           '\tchatBoxItem_t\t\tchatItems[MAX_CHATBOX_ITEMS];\n\tint\t\t\tchatPanelMode;')
    insert(cg/'cg_consolecmds.c', 'static consoleCommand_t\tcommands[] = {',
           'extern void ST_ToggleChat_f(void);\n\nstatic consoleCommand_t\tcommands[] = {\n\t{ "st_togglechat", ST_ToggleChat_f },')
    path = cg/'cg_draw.c'
    data = path.read_bytes()
    start = data.index(b'#define\tCHATBOX_CUTOFF_LEN')
    end = data.index(b'static void CG_Draw2DScreenTints', start)
    newline = b'\r\n' if b'\r\n' in data else b'\n'
    path.write_bytes(data[:start]+b'#include "cg_st_chat_panel.inc"'+newline*2+data[end:])

    path = cg/'cg_sabertrials_hud.inc'
    data = path.read_bytes()
    if b'const char *label;' in data:
        anchor = '''static const char *ST_HudStyle(int style, int hybrid, qhandle_t *icon, const float **color) {
    const char *label;
    *icon = st_hudMedia.saber; *color = st_hudCyan;'''
        signature = 'static const char *ST_HudStyle(int style, int hybrid, const float **color) {\n    const char *label;'
    else:
        anchor = '''static const char *ST_HudStyle(int style, qhandle_t *icon, const float **color) {
    *icon = st_hudMedia.saber; *color = st_hudCyan;'''
        signature = 'static const char *ST_HudStyle(int style, const float **color) {'
    insert(path, anchor, signature+'\n    *color = st_hudCyan;')
    insert(path, '*icon = st_hudMedia.dual; ', '')
    insert(path, '*icon = st_hudMedia.staff; ', '')
    insert(path, ', &icon, &styleColor)', ', &styleColor)')
    insert(path, '    ST_HudPanel(x, y, 148*s, 55*s, ST_HUD_WEAPON);', '''    if (saber) {
        const clientInfo_t *client = &cgs.clientinfo[ps->clientNum];
        if (client->saber[1].model[0])
            icon = st_hudMedia.dual;
        else if (client->saber[0].type == SABER_STAFF ||
            (client->saber[0].saberFlags & SFL_TWO_HANDED) || client->saber[0].numBlades > 1)
            icon = st_hudMedia.staff;
        else
            icon = st_hudMedia.saber;
    }
    ST_HudPanel(x, y, 148*s, 55*s, ST_HUD_WEAPON);''')

    shutil.copyfile(source/'bot-roles/codemp/ui/st_presentation_draw.inc', ui/'st_presentation_draw.inc')
    insert(game/'codemp/game/g_xcvar.h', 'XCVAR_DEF( sv_fps,',
           'XCVAR_DEF( sv_location, "", NULL, CVAR_ARCHIVE|CVAR_SERVERINFO, qfalse )\nXCVAR_DEF( sv_fps,')
    shutil.copyfile(source/'menu/ui_st_about_server.inc', ui/'ui_st_about_server.inc')
    patch_legacy(ui, insert)


def patch_legacy(ui, insert):
    bridge = ui/'ui_st_legacy.inc'
    insert(bridge, 'qboolean ST_LegacyMenuBegin(menuDef_t* m){',
           '#include "ui_st_about_server.inc"\n\nqboolean ST_LegacyMenuBegin(menuDef_t* m){')
    insert(bridge, '  LUI_Panel(r.x,r.y,r.w,r.h,true);',
           '  LUI_Panel(r.x,r.y,r.w,r.h,true);\n  if(LUI_Name(m->window.name,"ingame_about"))LUI_AboutServer(r);')
    insert(bridge, ' return LUI_Name(name,"apply")', ' return LUI_Name(name,"back")||LUI_Name(name,"apply")')
    insert(bridge, ''' float scale=std::min(i->textscale,i->typeData.listbox->elementHeight*.045f);
 SCUI_Fit(x,y,std::max(8.f,width),scale,s,i->window.foreColor);return qtrue;''',
           ''' const float height=i->typeData.listbox->elementHeight;
 const float scale=std::min(i->textscale,height*.045f);
 SCUI_Fit(x,y+(height-17.f*scale)*.5f,std::max(8.f,width),scale,s,i->window.foreColor);return qtrue;''')
    insert(bridge, ''' if((i->type==ITEM_TYPE_MULTI||i->type==ITEM_TYPE_YESNO)&&!i->window.background&&
    (!i->text||!*i->text||x>=i->textRect.x+i->textRect.w+7)){
  const float width=std::min(std::min(632.f,r.x+r.w)-x+3,std::max(28.f,w+12));
  if(width>=18)RUI_FieldArt(LUI_Focus(i)?"field_focus":"field_idle",x-4,y-2,width,std::max(12.f,17*scale+4));
 }''', ''' if((i->type==ITEM_TYPE_MULTI||i->type==ITEM_TYPE_YESNO)&&!i->window.background&&r.h>=12){
  scale=std::min(scale,(r.h-4.f)/17.f);
  y=r.y+(r.h-17.f*scale)*.5f;
  if(!i->text||!*i->text||x>=i->textRect.x+i->textRect.w+7){
   const float width=std::min(std::min(632.f,r.x+r.w)-x+3,std::max(28.f,RUI_Width(text,scale)+11));
   const float height=std::min(r.h-2.f,std::max(12.f,17.f*scale+6.f));
   if(width>=18)RUI_FieldArt(LUI_Focus(i)?"field_focus":"field_idle",x-4,r.y+(r.h-height)*.5f,width,height);
  }
 }''')
    path = ui/'ui_shared.c'
    insert(path, 'ST_LegacyListText(item,x+4+listPtr->columnInfo[j].pos,y+listPtr->elementHeight+item->textaligny,cell,text)',
           'ST_LegacyListText(item,x+4+listPtr->columnInfo[j].pos,y+listPtr->elementHeight,cell,text)')
    insert(path, 'ST_LegacyListText(item,x+4,y+item->textaligny,item->window.rect.w-SCROLLBAR_SIZE-9,text)',
           'ST_LegacyListText(item,x+4,y+listPtr->elementHeight,item->window.rect.w-SCROLLBAR_SIZE-9,text)')
    insert(bridge, ' if(!RUI_Ascii(text)||style==ITEM_TEXTSTYLE_BLINK',
           ''' if(LUI_Name(m->window.name,"ingame_callvote")&&LUI_Name(i->window.name,"error")&&LUI_Name(text,";"))return qtrue;
 if(!RUI_Ascii(text)||style==ITEM_TEXTSTYLE_BLINK''')
    insert(bridge, ' if(i->type==ITEM_TYPE_OWNERDRAW||LUI_Value(i))w=',
           ''' if(i->type==ITEM_TYPE_OWNERDRAW&&LUI_Name(i->window.name,"humanbotfield")&&r.h>=12){
  scale=std::min(scale,(r.h-3.f)/17.f);
  y=r.y+(r.h-17.f*scale)*.5f;
 }
 if(i->type==ITEM_TYPE_OWNERDRAW||LUI_Value(i))w=''')
