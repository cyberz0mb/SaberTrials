"""Wire offline menu catalogs into the current OpenJK frontend."""
from pathlib import Path
import shutil
import json

SOURCE = Path(__file__).resolve().parent
LANGUAGE_NAMES = ('English', 'Español', 'Русский', '日本語', '简体中文', '繁體中文', 'العربية',
                  'Deutsch', 'Français', 'Italiano', 'Português', 'Português (Brasil)',
                  '한국어', 'हिन्दी', 'Polski', 'Türkçe', 'Українська', 'Nederlands', 'Svenska', 'Suomi')


def edit(path, old, new, count=1):
    text = path.read_text(encoding='utf8')
    assert text.count(old) == count, (path, old, text.count(old))
    path.write_text(text.replace(old, new), encoding='utf8', newline='\n')


def quoted(value):
    # C++, unlike JSON, permits UTF-8 byte escapes for all characters.
    return '"'+''.join(chr(b) if 32 <= b < 127 and b not in (34,92) else f'\\{b:03o}'
                       for b in value.encode('utf8'))+'"'


def apply(engine, frontend):
    for tree in (engine,frontend):
        public = tree/'codemp/ui/ui_public.h'
        edit(public,'#define UI_API_VERSION 285','#define UI_API_VERSION 286')
        edit(public,'} uiImport_t;',
             '\tfloat (*MenuText)(const char *, float, float, float, const float *);\n'
             '\tconst char *(*MenuCatalog)(int, int *);\n} uiImport_t;')
        # Append so the existing camera and preset indices keep their meanings.
        choices = '|'.join(f'{index}={label}' for index,label in enumerate(LANGUAGE_NAMES,1))
        entry = (' {"st_menuLanguage","Menu language","Language","Changes the language of menus.",'
                 +quoted(choices)+',"1",2,2,0,0,CVAR_ARCHIVE | CVAR_NORESTART,1,'+str(len(LANGUAGE_NAMES))+'},\n')
        edit(tree/'codemp/ui/st_setup_catalog.h','};\nstatic const int SS_COUNT=',entry+'};\nstatic const int SS_COUNT=')

    client = engine/'codemp/client'
    shutil.copyfile(SOURCE/'cl_st_menu_font.inc',client/'cl_st_menu_font.inc')
    shutil.copyfile(SOURCE.parent/'translator/st_chat_raster.h',client/'st_chat_raster.h')
    text = client/'cl_cgameapi.cpp'
    edit(text,'#include "cl_st_chat_text.inc"','#include "cl_st_chat_text.inc"\n#include "cl_st_menu_font.inc"')
    ui_api = client/'cl_uiapi.cpp'
    edit(ui_api,'extern IHeapAllocator *G2VertSpaceClient;',
         'extern float STML_MenuText(const char*,float,float,float,const float*);\n'
         'extern const char *STML_MenuCatalog(int,int*);\nextern IHeapAllocator *G2VertSpaceClient;')
    edit(ui_api,'\t\tuii.SE_GetLanguageName',
         '\t\tuii.MenuText = STML_MenuText;\n\t\tuii.MenuCatalog = STML_MenuCatalog;\n\t\tuii.SE_GetLanguageName')
    engine_main = client/'cl_main.cpp'
    edit(engine_main,'static void CL_ShutdownRef( qboolean restarting );',
         'extern void STML_ResetFont();\nstatic void CL_ShutdownRef( qboolean restarting );')
    edit(engine_main,'static void CL_ShutdownRef( qboolean restarting ) {',
         'static void CL_ShutdownRef( qboolean restarting ) {\n\tSTML_ResetFont();')
    edit(engine_main,'\tif(shutdownRef)\n\t\tCL_ShutdownRef( qfalse );',
         '\tif(shutdownRef)\n\t\tCL_ShutdownRef( qfalse );\n\telse\n\t\tSTML_ResetFont();')
    for renderer in ('rd-rend2','rd-vanilla'):
        shutil.copyfile(SOURCE.parent/'translator/tr_st_chat.inc',engine/'codemp'/renderer/'tr_st_chat.inc')

    ui = frontend/'codemp/ui'
    shutil.copyfile(SOURCE/'ui_st_menu_language.inc',ui/'ui_st_menu_language.inc')
    main = ui/'ui_main.c'
    edit(main,'#include "ui_shared.h"','#include "ui_shared.h"\n#include "ui_st_menu_language.inc"')
    edit(main,'int Text_Width(const char *text, float scale, int iMenuFont)\n{',
         'int Text_Width(const char *text, float scale, int iMenuFont)\n{\n'
         '\tconst float width = STML_Width(text, scale);\n\tif (width > 0) return (int)ceil(width);')
    edit(main,'if(ST_LegacyText(x,y,scale,color,text,limit,style,iMenuFont))return;',
         'if(ST_LegacyText(x,y,scale,color,text,limit,style,iMenuFont))return;\n'
         '\tif (STML_Draw(x,y,scale,text,color)) return;')
    edit(main,'\tUI_RegisterCvars();','\tUI_RegisterCvars();\n\ttrap->Cvar_Create(stMenuLanguageCvar,"1",CVAR_ARCHIVE | CVAR_NORESTART);')

    rich = ui/'ui_st_rich.inc'
    edit(rich,'static float RUI_Width(const char* s,float scale){','static float RUI_Width(const char* s,float scale){\n s=STML_Translate(s);')
    edit(rich,'static void RUI_Text(float x,float y,float scale,const char* s,const float* color){',
         'static void RUI_Text(float x,float y,float scale,const char* s,const float* color){\n s=STML_Translate(s);\n if(STML_Draw(x,y,scale,s,color))return;')
    controls = ui/'ui_st_controls.inc'
    edit(controls,'char s[512];Q_strncpyz(s,text,sizeof(s));if(RUI_Width(s,scale)>w)',
         'char s[512];text=STML_Translate(text);if(STML_UTF8(text)){const float pixels=RUI_Width(text,scale);'
         'if(pixels>w&&pixels>0)scale*=w/pixels;SCUI_Text(x,y,scale,text,color);return;}'
         'Q_strncpyz(s,text,sizeof(s));if(RUI_Width(s,scale)>w)')
    edit(controls,'SCUI_Fit(x+5,y+4,w-10,.56f,scui.field==id?scui.edit:text,scuText);',
         'if(scui.field==id||id!=10){STML_Raw raw;SCUI_Fit(x+5,y+4,w-10,.56f,scui.field==id?scui.edit:text,scuText);}'
         'else SCUI_Fit(x+5,y+4,w-10,.56f,text,scuText);')
    root = ui/'ui_st_main.inc'
    edit(root,'float height=25,w=height*4*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image(path,66,button.y+7,w,height,smWhite);',
         'const char* labels[]={"Play","Profile","Controls","Setup","Exit"};\n'
         '  const char* label=labels[&button-smButtons];\n'
         '  if(strcmp(label,STML_Translate(label)))SCUI_Label(67,button.y+13,91,.88f,label,smWhite);\n'
         '  else {float height=25,w=height*4*uiInfo.uiDC.yscale/uiInfo.uiDC.xscale;SMUI_Image(path,66,button.y+7,w,height,smWhite);}')
    legacy = ui/'ui_st_legacy.inc'
    edit(legacy,'if(!RUI_Ascii(text)||style==ITEM_TEXTSTYLE_BLINK||style==ITEM_TEXTSTYLE_PULSE){',
         'if((!RUI_Ascii(text)&&!STML_UTF8(text))||style==ITEM_TEXTSTYLE_BLINK||style==ITEM_TEXTSTYLE_PULSE){')

    shared = ui/'ui_shared.c'
    edit(shared,'void Item_Text_AutoWrapped_Paint(itemDef_t *item) {',
         '#ifndef _CGAME\n#include <string>\n#include <vector>\nextern const char *STML_Translate(const char *);\nextern const char *STML_Reference(const char *,const char *);\n'
         'extern std::vector<std::string> STML_Lines(const char *,float,float,int);\n'
         'static const char *STML_ItemLabel(const char *text,const char *label) {\n'
         '\treturn label && *label==\'@\' ? STML_Reference(label,text) : STML_Translate(text);\n}\n#endif\n\n'
         'void Item_Text_AutoWrapped_Paint(itemDef_t *item) {')
    edit(shared,'\t// this needs to go here as it sets extents for cvar types as well\n\tItem_SetTextExtents(item, &width, &height, textPtr);',
         '#ifndef _CGAME\n\tif(item->text){\n\t\ttextPtr=STML_ItemLabel(textPtr,item->text);\n'
         '\t}\n#endif\n'
         '\t// this needs to go here as it sets extents for cvar types as well\n\tItem_SetTextExtents(item, &width, &height, textPtr);')
    edit(shared,'\t\tItem_TextColor(item, &color);\n\t\tDC->drawText(item->textRect.x + item->text2alignx',
         '#ifndef _CGAME\n\t\ttextPtr=STML_ItemLabel(textPtr,item->text2);\n#endif\n'
         '\t\tItem_TextColor(item, &color);\n\t\tDC->drawText(item->textRect.x + item->text2alignx')
    edit(shared,'\t\t\t\tItem_TextColor(item, &color);\n\n\t\t\t\t{// stupid C language',
         '#ifndef _CGAME\n\t\t\t\ttextPtr=STML_ItemLabel(textPtr,item->descText);\n#endif\n'
         '\t\t\t\tItem_TextColor(item, &color);\n\n\t\t\t\t{// stupid C language')
    edit(shared,'\t// this needs to go here as it sets extents for cvar types as well\n\tItem_SetTextExtents(item, &width, &height, textPtr);',
         '\t// Labels are measured in the active language, including when returning to English.\n'
         '#ifndef _CGAME\n\tif(item->text && !item->cvar) item->textRect.w=0;\n#endif\n'
         '\tItem_SetTextExtents(item, &width, &height, textPtr);')
    edit(shared,'\tpsCurrentTextReadPos = psText;\n\tpsReadPosAtLineStart = psCurrentTextReadPos;',
         '#ifndef _CGAME\n'
         '\tconst char *localized=STML_ItemLabel(psText,item->text);\n\tif(localized!=psText){\n'
         '\t\tscrollPtr->iLineCount=0;\n\t\tmemset(scrollPtr->pLines,0,sizeof(scrollPtr->pLines));\n'
         '\t\tfor(const auto& line:STML_Lines(localized,iBoxWidth,item->textscale,MenuFontToHandle(item->iMenuFont))){\n'
         '\t\t\tif(scrollPtr->iLineCount>=MAX_TEXTSCROLL_LINES)break;\n'
         '\t\t\tscrollPtr->pLines[scrollPtr->iLineCount++]=String_Alloc(line.c_str());\n'
         '\t\t}\n\t\treturn;\n\t}\n#endif\n'
         '\tpsCurrentTextReadPos = psText;\n\tpsReadPosAtLineStart = psCurrentTextReadPos;')
    edit(shared,'\tcount = scrollPtr->iLineCount;',
         '#ifndef _CGAME\n\tif(item->text&&!item->cvar){\n'
         '\t\tstatic const char *labels[MAX_MENUITEMS]={};\n\t\tstatic const itemDef_t *owners[MAX_MENUITEMS]={};\n'
         '\t\tstatic int languages[MAX_MENUITEMS]={};\n'
         '\t\tconst unsigned slot=(reinterpret_cast<size_t>(item)>>4)%MAX_MENUITEMS;\n'
         '\t\tconst int language=(int)trap->Cvar_VariableValue("st_menuLanguage");\n'
         '\t\tconst char *label=STML_ItemLabel(item->text,item->text);\n'
         '\t\tif(owners[slot]!=item||labels[slot]!=label||languages[slot]!=language){\n'
         '\t\t\towners[slot]=item;labels[slot]=label;languages[slot]=language;Item_TextScroll_BuildLines(item);\n\t\t}\n\t}\n#endif\n'
         '\tcount = scrollPtr->iLineCount;')

    setup = ui/'ui_st_setup_draw.inc'
    edit(setup,'for(int i=0;i<SS_COUNT;){', 
         'const int languageIndex=SS_COUNT-1;\n'
         ' if(ssui.tab==2){groups.push_back({"Language",y});y+=24;ssui.itemY[languageIndex]=(int)y;'
         'rows.push_back(languageIndex);y+=rowHeight+9;}\n'
         ' for(int i=0;i<languageIndex;){')
    edit(setup,'while(i<SS_COUNT&&ssSettings[i].tab==ssui.tab&&group==ssSettings[i].group)',
         'while(i<languageIndex&&ssSettings[i].tab==ssui.tab&&group==ssSettings[i].group)')
    edit(setup,'std::string(s.label)+" "+s.name+" "+s.help',
         'std::string(STML_Translate(s.label))+" "+s.label+" "+s.name+" "+STML_Translate(s.help)')
    edit(setup,'ssTabs[ssSettings[i].tab],ssSettings[i].label);SCUI_Button',
         'STML_Translate(ssTabs[ssSettings[i].tab]),STML_Translate(ssSettings[i].label));SCUI_Button')
    edit(setup,'SCUI_Fit(x+5,y+5,w-10,.56f,editing?ssui.edit:text,scuText);',
         'if(editing||field!=2){STML_Raw raw;SCUI_Fit(x+5,y+5,w-10,.56f,editing?ssui.edit:text,scuText);}'
         'else SCUI_Fit(x+5,y+5,w-10,.56f,text,scuText);')
    edit(ui/'ui_st_profile_draw.inc','SCUI_Fit(x+4,y+61,cellW-8,.43f,model.name.c_str(),color);',
         '{STML_Raw raw;SCUI_Fit(x+4,y+61,cellW-8,.43f,model.name.c_str(),color);}')
    edit(ui/'ui_st_profile_draw.inc','SCUI_Fit(466,354,152,.61f,title.c_str(),scuText);',
         'if(spui.selected>=0){STML_Raw raw;SCUI_Fit(466,354,152,.61f,title.c_str(),scuText);}'
         'else SCUI_Fit(466,354,152,.61f,title.c_str(),scuText);')
    edit(ui/'ui_st_profile.inc','SCUI_Fit(x+6,y+5,w-12,.54f,value.c_str(),scuText);SPUI_Hit',
         'if(id==101||spui.field==id||!spui.filter.search.empty()){STML_Raw raw;SCUI_Fit(x+6,y+5,w-12,.54f,value.c_str(),scuText);}'
         'else SCUI_Fit(x+6,y+5,w-12,.54f,value.c_str(),scuText);SPUI_Hit')
    edit(ui/'ui_st_profile_draw.inc','char count[80];Com_sprintf(count,sizeof(count),"%d %s",int(spui.rows.size()),spui.rows.size()==1?"model":"models");',
         'const std::string count=STML_FormatNumbers(spui.rows.size()==1?"%d model":"%d models",{int(spui.rows.size())});')
    edit(ui/'ui_st_profile_draw.inc','spui.gridY-19,.56f,count,scuText','spui.gridY-19,.56f,count.c_str(),scuText')
    edit(ui/'ui_st_controls_draw.inc','Com_sprintf(line,sizeof(line),"%d-%d of %d",scui.page*per+1,(scui.page+1)*per<count?(scui.page+1)*per:count,count);SCUI_Text(left,407,.49f,line,scuMuted);',
         'const std::string range=STML_FormatNumbers("%d-%d of %d",{scui.page*per+1,std::min((scui.page+1)*per,count),count});'
         'SCUI_Text(left,407,.49f,range.c_str(),scuMuted);')
