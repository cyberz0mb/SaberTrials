// Candidate preview build only. Never install this test entry point.
#include "ghoul2/G2.h"
static void ST_HandQA_f(void) {
    char style[16];int hand,attack;
    Q_strncpyz(style,UI_Argv(1),sizeof(style));
    if(!Q_stricmp(style,"navigation")) {
        Menus_CloseAll();Menus_ActivateByName("saberMenu");trap->Key_SetCatcher(KEYCATCH_UI);return;
    }
    if(!Q_stricmp(style,"state")) {
        menuDef_t *menu=Menu_GetFocused();
        char saved[64],second[64];
        trap->Cvar_VariableStringBuffer("saber1",saved,sizeof(saved));
        trap->Cvar_VariableStringBuffer("saber2",second,sizeof(second));
        trap->Print("HAND_NAV label=%s menu=%s saved=%d edit=%d hilt=%s second=%s\n",UI_Argv(2),
            menu?menu->window.name:"none",(int)trap->Cvar_VariableValue("saberHand"),
            (int)trap->Cvar_VariableValue("ui_saberHand"),saved,second);return;
    }
    if(!Q_stricmp(style,"escape")) {
        UI_KeyEvent(A_ESCAPE,qtrue);UI_KeyEvent(A_ESCAPE,qfalse);return;
    }
    if(!Q_stricmp(style,"click")) {
        menuDef_t *menu=Menu_GetFocused();
        itemDef_t *item=menu?Menu_FindItemByName(menu,UI_Argv(2)):NULL;
        if(!item){trap->Print("HAND_NAV missing control %s\n",UI_Argv(2));return;}
        UI_MouseEvent((int)(item->window.rect.x+item->window.rect.w/2-uiInfo.uiDC.cursorx),
            (int)(item->window.rect.y+item->window.rect.h/2-uiInfo.uiDC.cursory));
        UI_KeyEvent(A_MOUSE1,qtrue);UI_KeyEvent(A_MOUSE1,qfalse);return;
    }
    if(!Q_stricmp(style,"geometry")||!Q_stricmp(style,"pose")) {
        menuDef_t* menu=Menu_GetFocused();
        itemDef_t* item=menu?Menu_FindItemByName(menu,"st_hand_preview"):NULL;
        float frame=0,speed=0;int first=0,last=0,flags=0,h,k,n,num,b,blades;
        vec3_t zero={0,0,0},scale={1,1,1};
        if(!item||!item->ghoul2){trap->Print("HAND_GEOMETRY missing preview\n");return;}
        trap->G2API_GetBoneAnim(item->ghoul2,"model_root",uiInfo.uiDC.realTime,&frame,&first,&last,&flags,&speed,NULL,0);
        h=trap->Cvar_VariableValue("ui_saberHand")==1;k=atoi(UI_Argv(2));
        if(!Q_stricmp(style,"pose")) {
            int sample=first+(int)((last-first-1)*(k*.25f));
            // The renderer's clock is frame-based: set on one frame, query on a
            // later one. Mutating and querying repeatedly within a single UI
            // frame would read the already cached pose.
            trap->G2API_SetBoneAnim(item->ghoul2,0,"model_root",sample,sample+1,
                BONE_ANIM_OVERRIDE_FREEZE|(h?BONE_ANIM_MIRROR:0),1,uiInfo.uiDC.realTime,-1,0);
            return;
        }
        num=!Q_stricmp(UI_Cvar_VariableString("ui_saber_type"),"dual")?2:1;
        blades=!Q_stricmp(UI_Cvar_VariableString("ui_saber_type"),"staff")?2:1;
        for(n=0;n<num;n++)for(b=0;b<blades;b++) {
                int blade=trap->G2API_AddBolt(item->ghoul2,n+1,b?"*blade2":"*blade1");
                mdxaBone_t matrix;
                if(blade<0){trap->Print("HAND_GEOMETRY missing bolt\n");return;}
                if(!trap->G2API_GetBoltMatrix(item->ghoul2,n+1,blade,&matrix,zero,zero,uiInfo.uiDC.realTime,NULL,scale)) {
                    trap->Print("HAND_GEOMETRY missing matrix\n");return;
                }
                trap->Print("HAND_GEOMETRY style=%s pose=%d hand=%d hilt=%d blade=%d origin=%.6f,%.6f,%.6f direction=%.6f,%.6f,%.6f\n",
                    UI_Cvar_VariableString("ui_saber_type"),k,h,n,b,
                    matrix.matrix[0][3],matrix.matrix[1][3],matrix.matrix[2][3],
                    -matrix.matrix[0][1],-matrix.matrix[1][1],-matrix.matrix[2][1]);
        }
        return;
    }
    if(!Q_stricmp(style,"toggle")) {
        menuDef_t* menu=Menu_GetFocused();
        itemDef_t* item=menu?Menu_FindItemByName(menu,"hand"):NULL;
        if(!item){trap->Print("HAND_QA missing control\n");return;}
        UI_MouseEvent((int)(item->window.rect.x+item->window.rect.w/2-uiInfo.uiDC.cursorx),
                      (int)(item->window.rect.y+item->window.rect.h/2-uiInfo.uiDC.cursory));
        UI_KeyEvent(A_MOUSE1,qtrue);UI_KeyEvent(A_MOUSE1,qfalse);return;
    }
    if(!Q_stricmp(style,"probe")) {
        menuDef_t* menu=Menu_GetFocused();
        itemDef_t* item=menu?Menu_FindItemByName(menu,"st_hand_preview"):NULL;
        float frame=0,speed=0;int first=0,last=0,flags=0;
        if(!item||!item->ghoul2){trap->Print("HAND_QA missing preview\n");return;}
        trap->G2API_GetBoneAnim(item->ghoul2,"model_root",uiInfo.uiDC.realTime,&frame,&first,&last,&flags,&speed,NULL,0);
        trap->Print("HAND_QA ready style=%s hand=%d mirror=%d frame=%.2f first=%d last=%d support=%d hilt=%d\n",
            UI_Cvar_VariableString("ui_saber_type"),(int)trap->Cvar_VariableValue("ui_saberHand"),!!(flags&BONE_ANIM_MIRROR),frame,first,last,
            (int)trap->Cvar_VariableValue("ui_handSupported"),trap->G2API_HasGhoul2ModelOnIndex(&(item->ghoul2),1));
        return;
    }
    hand=atoi(UI_Argv(2));attack=atoi(UI_Argv(3));
    trap->Cvar_Set("ui_saber_type",style);
    trap->Cvar_Set("ui_saber",!Q_stricmp(style,"staff")?"dual_1":"single_1");
    trap->Cvar_Set("ui_saber2","single_2");
    trap->Cvar_Set("ui_saberHand",hand?"1":"0");
    trap->Cvar_Set("ui_handAttack",attack?"1":"0");
    trap->Cvar_Set("ui_saber_color","blue");trap->Cvar_Set("ui_saber2_color","green");
    trap->Cvar_Set("ui_char_color_red","255");trap->Cvar_Set("ui_char_color_green","255");trap->Cvar_Set("ui_char_color_blue","255");
    Menus_CloseAll();Menus_ActivateByName("st_handedness");trap->Key_SetCatcher(KEYCATCH_UI);
}
