"""Add translation to the current native client, cgame and Setup sources."""
from pathlib import Path
import shutil
import json

SOURCE = Path(__file__).resolve().parent


def replace(path, old, new, count=1):
    text=path.read_text()
    assert text.count(old)==count,(path,old[:80],text.count(old))
    path.write_text(text.replace(old,new),newline='\n')


def apply(path, engine=False):
    tree=Path(path)/'codemp'
    shutil.copyfile(SOURCE/'st_translation_api.h',tree/'qcommon/st_translation_api.h')
    shutil.copyfile(SOURCE/'st_utf8.h',tree/'qcommon/st_utf8.h')
    languages=json.loads((SOURCE/'languages.json').read_text())
    header='#ifndef ST_TRANSLATION_LANGUAGES_H\n#define ST_TRANSLATION_LANGUAGES_H\n'
    for function,key in (('ST_LanguageTag','code'),('ST_LanguageLocale','locale')):
        values=[('PT-BR' if r['code']=='pb' else 'ZH-CN' if r['code']=='zh' else 'ZH-TW' if r['code']=='zt' else r['code'].upper())
                if key=='code' else r[key] for r in languages]
        header+='static const char *'+function+'(int id){static const char *values[]={'+','.join(json.dumps(v) for v in values)+'};return values[id>=1&&id<=17?id-1:0];}\n'
    header+='#endif\n'
    (tree/'qcommon/st_translation_languages.h').write_text(header)
    public=tree/'cgame/cg_public.h'
    replace(public,'#define\tCGAME_API_VERSION\t\t238','#define\tCGAME_API_VERSION\t\t240')
    replace(public,'#include "qcommon/st_mvp_api.h"','#include "qcommon/st_mvp_api.h"\n#include "qcommon/st_translation_api.h"')
    replace(public,'} cgameImport_t;',
        '    unsigned (*ST_TranslateSubmit)(const stTranslationRequest_t *);\n'
        '    qboolean (*ST_TranslatePoll)(stTranslationResult_t *);\n'
        '    qboolean (*ST_ChatLayout)(const stChatLayoutRequest_t *,stChatLayoutResult_t *);\n'
        '    void (*ST_ChatDraw)(int,float,float,int,int);\n} cgameImport_t;')
    shutil.copyfile(SOURCE.parent/'setup/st_setup_catalog.h',tree/'ui/st_setup_catalog.h')
    if engine:
        for name in ('st_translation_api.h','st_translation_core.h','cl_st_translation.inc','cl_st_chat_text.inc','st_chat_raster.h','st_utf8.h','cl_st_chat_input.inc'):
            shutil.copyfile(SOURCE/name,tree/'client'/name)
        (tree/'client/st_translation_languages.h').write_text(header)
        api=tree/'client/cl_cgameapi.cpp'
        replace(api,'#include "FxUtil.h"','#include "FxUtil.h"\n#include "cl_st_translation.inc"\n#include "cl_st_chat_text.inc"')
        replace(api,'\t\tcgi.ST_MvpRead = CL_MvpRead;',
            '\t\tcgi.ST_MvpRead = CL_MvpRead;\n\t\tcgi.ST_TranslateSubmit=STTR_Submit;\n\t\tcgi.ST_TranslatePoll=STTR_Poll;\n'
            '\t\tcgi.ST_ChatLayout=STCT_Layout;\n\t\tcgi.ST_ChatDraw=STCT_Draw;')
        replace(api,'void CL_UnbindCGame( void ) {','void CL_UnbindCGame( void ) {\n    STTR_Reset();STCT_Reset();')
        main=tree/'client/cl_main.cpp'
        replace(main,'void CL_Init( void ) {',
            'extern void STTR_Init();\nextern void STTR_Frame();\nextern void STTR_Reset();\nextern void STTR_Shutdown();\n'
            'void CL_Init( void ) {\n    STTR_Init();')
        # These functions precede CL_Init in this translation unit.
        replace(main,'void CL_Frame ( int msec ) {','extern void STTR_Frame();\nvoid CL_Frame ( int msec ) {\n    STTR_Frame();')
        replace(main,'void CL_Disconnect( qboolean showMainMenu ) {',
            'extern void STTR_Reset();\nvoid CL_Disconnect( qboolean showMainMenu ) {\n    STTR_Reset();')
        replace(main,'void CL_Shutdown( void ) {','void CL_Shutdown( void ) {\n    STTR_Shutdown();')
        replace(tree/'CMakeLists.txt','set(MPEngineDefines ${MPSharedDefines})','set(MPEngineDefines ${MPSharedDefines} ST_UNICODE_CHAT)')
        keys=tree/'client/cl_keys.cpp'
        replace(keys,'void Field_Paste( field_t *edit ) {','#include "cl_st_chat_input.inc"\nvoid Field_Paste( field_t *edit ) {\n    if(edit==&chatField){ST_ChatPaste();return;}')
        replace(keys,'void Field_KeyDownEvent( field_t *edit, int key ) {','void Field_KeyDownEvent( field_t *edit, int key ) {\n    if(edit==&chatField){ST_ChatKey(key);return;}')
        replace(keys,'void Field_CharEvent( field_t *edit, int ch ) {','void Field_CharEvent( field_t *edit, int ch ) {\n    if(edit==&chatField){ST_ChatChar(ch);return;}')
        replace(keys,'void CL_CharEvent( int key ) {','void CL_CharEvent( int key ) {\n'
            '    if(key&0x1000000){unsigned cp=key&0x1fffff;int catcher=Key_GetCatcher();\n'
            '        if((catcher&KEYCATCH_MESSAGE)&&!(catcher&(KEYCATCH_CONSOLE|KEYCATCH_UI|KEYCATCH_CGAME))){ST_ChatInsert(cp);return;}\n'
            '        key=ConvertUTF32ToExpectedCharset(cp);}\n')
        sdl=Path(path)/'shared/sdl/sdl_input.cpp'
        replace(sdl,'Sys_QueEvent( 0, SE_CHAR, encoded, 0, 0, NULL );',
            '#ifdef ST_UNICODE_CHAT\n                                Sys_QueEvent(0,SE_CHAR,0x1000000|utf32,0,0,NULL);\n'
            '#else\n                                Sys_QueEvent( 0, SE_CHAR, encoded, 0, 0, NULL );\n#endif')
        console=tree/'client/cl_console.cpp'
        replace(console,'\t\tField_BigDraw( &chatField, skip * BIGCHAR_WIDTH, v, qtrue, qtrue );',
            '\t\textern qboolean STCT_DrawInput(const char *,int,float,float);\n'
            '\t\tif(!STCT_DrawInput(chatField.buffer,chatField.cursor,skip*BIGCHAR_WIDTH,v))\n'
            '\t\t    Field_BigDraw(&chatField,skip*BIGCHAR_WIDTH,v,qtrue,qtrue);')
        replace(tree/'rd-common/tr_public.h','#define\tREF_API_VERSION 11','#define\tREF_API_VERSION 12')
        replace(tree/'rd-common/tr_public.h','} refexport_t;','    qhandle_t (*ST_ChatUpload)(int,int,int,const byte *);\n} refexport_t;')
        for renderer in ('rd-vanilla','rd-rend2'):
            rd=tree/renderer
            shutil.copyfile(SOURCE/'tr_st_chat.inc',rd/'tr_st_chat.inc')
            shader=rd/'tr_shader.cpp'
            marker='void R_InitShaders(qboolean server)\n{' if renderer=='rd-vanilla' else 'void R_InitShaders( qboolean server ) {'
            replace(shader,marker,('#define ST_CHAT_REND2\n' if renderer=='rd-rend2' else '')+'#include "tr_st_chat.inc"\n'+marker+'\n    ST_ChatResetImages();')
            with (rd/'tr_local.h').open('a') as stream:stream.write('\nqhandle_t RE_STChatUpload(int,int,int,const byte *);\n')
            init=rd/'tr_init.cpp';text=init.read_text();marker='re.UploadCinematic = RE_UploadCinematic;' if renderer=='rd-rend2' else 're.UploadCinematic\t\t\t\t\t\t= RE_UploadCinematic;'
            replace(init,marker,marker+'\n    re.ST_ChatUpload=RE_STChatUpload;')
    else:
        # The Setup module compiles shared game files as C++, unlike cgame.
        shutil.copyfile(SOURCE.parent/'weapon-dlc/bg_st_dlc.inc',tree/'game/bg_st_dlc.inc')
        cg=tree/'cgame'
        shutil.copyfile(SOURCE/'cg_st_translation.inc',cg/'cg_st_translation.inc')
        shutil.copyfile(SOURCE/'cg_st_chat_draw.inc',cg/'cg_st_chat_draw.inc')
        replace(cg/'cg_local.h','\tchar\tstring[MAX_SAY_TEXT];','\tchar\tstring[512];')
        replace(cg/'cg_local.h','\tchar\tstamp[8];','\tchar\tstamp[8];\n'
            '\tunsigned translationTicket;\n\tint translationTarget,translationSource,translationTime,translationChannel;\n\tchar translationPrefix[512],translated[ST_TRANSLATION_TEXT+512];')
        with (cg/'cg_local.h').open('a') as stream:
            stream.write('\nvoid STTR_ReceivedChat(const char *,int,int,const char *);\nvoid STTR_Inspect(void);\n')
        chat=cg/'cg_st_chat_panel.inc'
        replace(chat,'typedef char stChatLine_t[MAX_SAY_TEXT + 3];',
            'typedef char stChatLine_t[4096];\n#include "cg_st_translation.inc"')
        replace(chat,'\tQ_strncpyz(chat->string, chatStr, sizeof(chat->string));',
            '\tmemset(chat,0,sizeof(*chat));\n\tQ_strncpyz(chat->string, chatStr, sizeof(chat->string));')
        text=chat.read_text();start=text.index('static void CG_ChatBox_DrawStrings(void)')
        chat.write_text(text[:start]+'#include "cg_st_chat_draw.inc"\n',newline='\n')
        replace(cg/'cg_draw.c','static void CG_Draw2D( void ) {','static void CG_Draw2D( void ) {\n    STTR_ChatPoll();')
        server=cg/'cg_servercmds.c'
        replace(server,'text[MAX_SAY_TEXT] = {0};','text[512] = {0};')
        text=server.read_text();start=text.index('static void CG_Chat_f( void )');end=text.index('static void CG_RemapShader_f',start)
        section=text[start:end];anchor='CG_ChatBox_AddString( text );'
        section=section.replace('name[MAX_NETNAME]={0}','name[128]={0}')
        assert section.count(anchor)==4
        hooks=['if(trap->Cmd_Argc()>=3)STTR_ReceivedChat(text,atoi(CG_Argv(2)),0,NULL);',
               'if(trap->Cmd_Argc()>=6)STTR_ReceivedChat(text,atoi(CG_Argv(5)),0,message);',
               'if(trap->Cmd_Argc()>=3)STTR_ReceivedChat(text,atoi(CG_Argv(2)),1,NULL);',
               'if(trap->Cmd_Argc()>=6)STTR_ReceivedChat(text,atoi(CG_Argv(5)),1,message);']
        parts=section.split(anchor)
        section=parts[0]+''.join(anchor+'\n            '+hook+part for hook,part in zip(hooks,parts[1:]))
        server.write_text(text[:start]+section+text[end:],newline='\n')
        replace(cg/'cg_consolecmds.c','\t{ "tcmd",','\t{ "st_translatorinfo", STTR_Inspect },\n\t{ "tcmd",')
        draw=tree/'ui/ui_st_setup_draw.inc'
        replace(draw,'SCUI_Fit(x+4,y+14,labelWidth,.44f,s.name,scuCyan);',
            'if(strcmp(s.group,"Translation"))SCUI_Fit(x+4,y+14,labelWidth,.44f,s.name,scuCyan);')
        replace(draw,'else SCUI_Text(24,gy+4,.62f,g.first.c_str(),scuMuted);',
            'else if(g.first=="Translation"){char status[128],title[160];trap->Cvar_VariableStringBuffer("st_translationStatus",status,sizeof(status));'
            'Com_sprintf(title,sizeof(title),"Translation - %s",status);SCUI_Fit(24,gy+4,570,.62f,title,scuMuted);}'
            'else SCUI_Text(24,gy+4,.62f,g.first.c_str(),scuMuted);')
