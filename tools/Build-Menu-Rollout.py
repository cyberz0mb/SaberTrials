"""Build the remaining MP menu presentation on the installed rich UI."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'dist/rich-menus-01';OUT=ROOT/'dist/menu-rollout-01'
PREVIOUS=ROOT/'dist/rich-menus-install.json';PACKAGE='zzzzzzzzzz_sabertrials_rollout.pk3'
SRC=ROOT/'development-source/rich-menu';INC=SRC/'ui_st_legacy.inc';ART=ROOT/'tools/Generate-Menu-Rollout-Art.ps1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def inputs():return {p.relative_to(ROOT).as_posix():sha(p) for p in (INC,ART)}
def patch(p,old,new):
 s=p.read_text();assert s.count(old)==1,(p,old);p.write_text(s.replace(old,new))
def prepare():
 baseline=read(BASE/'source-receipt.json');assert tree(BASE/'frontend')==baseline['sources']
 previous=read(PREVIOUS);assert all(sha(ROOT/n)==v for n,v in previous['after'].items()),'Installed rich UI drift'
 OUT.mkdir(exist_ok=True);dest=OUT/'frontend'
 if not dest.exists():shutil.copytree(BASE/'frontend',dest)
 ui=dest/'codemp/ui';old=BASE/'frontend/codemp/ui'
 for n in ('ui_main.c','ui_shared.c','ui_sabertrials_presentation.inc','ui_atoms.c','ui_force.c'):shutil.copy2(old/n,ui/n)
 shutil.copy2(INC,ui/INC.name)
 p=ui/'ui_main.c'
 patch(p,'#include "ui_st_main.inc"','#include "ui_st_main.inc"\n#include "ui_st_legacy.inc"')
 patch(p,'\t\tRUI_Background();','\t\tLUI_BeginFrame();\n\t\tRUI_Background();')
 patch(p,'\t\tSPUI_Draw();','\t\tSPUI_Draw();\n\t\tLUI_EndFrame();')
 patch(p,'uie.IsFullscreen\t\t= RUI_IsFullscreen;','uie.IsFullscreen\t\t= LUI_IsFullscreen;')
 patch(p,'case UI_IS_FULLSCREEN:\n\t\treturn RUI_IsFullscreen();','case UI_IS_FULLSCREEN:\n\t\treturn LUI_IsFullscreen();')
 patch(p,'if ( !overlay && menu ) {\n\t\tMenu_Paint(menu, qtrue);\n\t}', 'if ( !overlay && menu ) {\n\t\tLUI_BeginFrame(menu);\n\t\tMenu_Paint(menu, qtrue);\n\t\tLUI_EndFrame();\n\t}')
 patch(p,'uiInfo.uiDC.drawHandlePic\t\t\t\t\t= &UI_DrawHandlePic;','uiInfo.uiDC.drawHandlePic\t\t\t\t\t= &LUI_DrawPic;')
 patch(p,'void Text_Paint(float x, float y, float scale, vec4_t color, const char *text, float adjust, int limit, int style, int iMenuFont)\n{',
  'extern qboolean ST_LegacyText(float,float,float,vec4_t,const char*,int,int,int);\nvoid Text_Paint(float x, float y, float scale, vec4_t color, const char *text, float adjust, int limit, int style, int iMenuFont)\n{\n\tif(ST_LegacyText(x,y,scale,color,text,limit,style,iMenuFont))return;')
 p=ui/'ui_sabertrials_presentation.inc';s=p.read_text();start=s.index('static void ST_UIBrowserPanel(');end=s.index('static void ST_UIPresentation',start)
 p.write_text(s[:start]+'extern void ST_LegacyBrowserPanel(const char* info);\n'+s[end:].replace('ST_UIBrowserPanel(info);','ST_LegacyBrowserPanel(info);'))
 p=ui/'ui_shared.c'
 patch(p,'void Item_Paint(itemDef_t *item)', '''#ifdef UI_BUILD
extern qboolean ST_LegacyShouldPaint(menuDef_t*);
extern qboolean ST_LegacyMenuBegin(menuDef_t*);
extern void ST_LegacyMenuEnd(menuDef_t*);
extern int ST_LegacyItemWindow(itemDef_t*);
extern itemDef_t* ST_LegacySetItem(itemDef_t*);
struct STLegacyItemScope {
 itemDef_t* previous;
 explicit STLegacyItemScope(itemDef_t* item):previous(ST_LegacySetItem(item)){}
 ~STLegacyItemScope(){ST_LegacySetItem(previous);}
};
#endif
void Item_Paint(itemDef_t *item)''')
 patch(p,'\tWindow_Paint(&item->window, parent->fadeAmount , parent->fadeClamp, parent->fadeCycle);', '''#ifdef UI_BUILD
 const int stPaint=ST_LegacyItemWindow(item);
 if(stPaint==2)return;
 STLegacyItemScope stLegacyItemScope(item);
 if(stPaint==0)
#endif
\tWindow_Paint(&item->window, parent->fadeAmount , parent->fadeClamp, parent->fadeCycle);''')
 patch(p,'\t// draw the background if necessary\n\tif (menu->fullScreen)', '''#ifdef UI_BUILD
 if(!ST_LegacyShouldPaint(menu))return;
 if(!ST_LegacyMenuBegin(menu)) {
#endif
\t// draw the background if necessary
\tif (menu->fullScreen)''')
 patch(p,'\tWindow_Paint(&menu->window, menu->fadeAmount, menu->fadeClamp, menu->fadeCycle );','\tWindow_Paint(&menu->window, menu->fadeAmount, menu->fadeClamp, menu->fadeCycle );\n#ifdef UI_BUILD\n }\n#endif')
 patch(p,'\n\tif (debugMode) {\n\t\tvec4_t color;\n\t\tcolor[0] = color[2] = color[3] = 1;', '\n#ifdef UI_BUILD\n ST_LegacyMenuEnd(menu);\n#endif\n\tif (debugMode) {\n\t\tvec4_t color;\n\t\tcolor[0] = color[2] = color[3] = 1;')
 patch(p,'void Item_ListBox_Paint(itemDef_t *item) {','''#ifdef UI_BUILD
extern qboolean ST_LegacyListText(itemDef_t*,float,float,float,const char*);
#endif
void Item_ListBox_Paint(itemDef_t *item) {''')
 native='DC->drawText(x + 4 + listPtr->columnInfo[j].pos, y + listPtr->elementHeight+ textyOffset + item->textaligny, item->textscale, item->window.foreColor, text, 0,listPtr->columnInfo[j].maxChars, item->textStyle, item->iMenuFont);'
 patch(p,native,'''#ifdef UI_BUILD
 int endX=j+1<listPtr->numColumns?listPtr->columnInfo[j+1].pos:item->window.rect.w-SCROLLBAR_SIZE;
 int icons=optionalImage3>=0?3:optionalImage2>=0?2:optionalImage1>=0?1:0;
 float cell=endX-listPtr->columnInfo[j].pos-icons*listPtr->elementHeight-8;
 if(!ST_LegacyListText(item,x+4+listPtr->columnInfo[j].pos,y+listPtr->elementHeight+item->textaligny,cell,text))
#endif
 '''+native)
 patch(p,'int Menu_Count() {','''#if defined(UI_BUILD) && defined(ST_CONTROLS_QA)
void ST_LegacyInventory(){for(int i=0;i<menuCount;++i)Com_Printf("ST_LEGACY_MENU %s %d\\n",Menus[i].window.name,Menus[i].itemCount);}
#endif
int Menu_Count() {''')
 native='DC->drawText(x + 4, y + item->textaligny, item->textscale, item->window.foreColor, text, 0, 0, item->textStyle, item->iMenuFont);'
 patch(p,native,'''#ifdef UI_BUILD
 if(!ST_LegacyListText(item,x+4,y+item->textaligny,item->window.rect.w-SCROLLBAR_SIZE-9,text))
#endif
 '''+native)
 p=ui/'ui_main.c'
 patch(p,'trap->ext.AddCommand("st_mainqa");','trap->ext.AddCommand("st_mainqa");\n trap->ext.AddCommand("st_legacyqa");')
 p=ui/'ui_atoms.c';patch(p,'extern qboolean ST_MainQA(void);','extern qboolean ST_MainQA(void);\nextern qboolean ST_LegacyQA(void);')
 patch(p,'if(ST_MainQA()||ST_ProfileQA()','if(ST_LegacyQA()||ST_MainQA()||ST_ProfileQA()')
 p=ui/'ui_force.c';patch(p,'// Draw the stars spent on the current force power','extern qboolean ST_LegacyForceRanks(const rectDef_t*,int,int,int);\n// Draw the stars spent on the current force power')
 patch(p,'\tif (1)\t// if (val)','\tif(ST_LegacyForceRanks(rect,forceindex,val,max))return;\n\tif (1)\t// if (val)')
 art=OUT/'assets/ui/assets/sabertrials/rollout'
 subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ART),'-Output',str(art)],check=True)
 with zipfile.ZipFile(OUT/PACKAGE,'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((OUT/'assets').rglob('*.png')):
   entry=zipfile.ZipInfo(p.relative_to(OUT/'assets').as_posix(),(2026,11,7,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,p.read_bytes())
 r={'baseline_receipt_sha256':sha(BASE/'source-receipt.json'),'prior_install_sha256':sha(PREVIOUS),'inputs':inputs(),'sources':tree(dest),'assets':tree(OUT/'assets'),'package_sha256':sha(OUT/PACKAGE)}
 (OUT/'source-receipt.json').write_text(json.dumps(r,indent=2));print('Prepared UI-only menu rollout.',flush=True)
def build(qa):
 r=read(OUT/'source-receipt.json');assert r['inputs']==inputs() and r['sources']==tree(OUT/'frontend')
 m=load('rollout_builder',ROOT/'tools/Build-Profile.py');m.OUT=OUT;m.SRC=SRC;original=m.tree;m.tree=lambda p:inputs() if p==m.SRC else original(p);m.build(qa)
 p=OUT/('build-record-qa.json' if qa else 'build-record.json');r=read(p);r['builder_sha256']=sha(Path(__file__));p.write_text(json.dumps(r,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--build',action='store_true');p.add_argument('--qa',action='store_true');a=p.parse_args()
 if a.prepare:prepare()
 if a.build:build(a.qa)
