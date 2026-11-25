#include "st_wearable_id.h"
#include "st_wearable_draw.inc"
static struct {
    bool open, reverse;
    int slot, page;
    std::string model, picked[2];
    std::vector<std::string> names[2];
    qhandle_t preview[2];
    stWearBolts_t bolts;
} outfits;

static const char *ST_WearDir(int slot) { return slot ? "capes" : "hats"; }
static void ST_OutfitPreview(int slot) {
    const auto &name=outfits.picked[slot];
    outfits.preview[slot]=0;
    if (name.empty()) return;
    // Local menu art has distinct names from the assets used for world rendering.
    outfits.preview[slot]=trap->R_RegisterModel(va("st_outfits/%s/%s.md3",ST_WearDir(slot),name.c_str()));
    if (!outfits.preview[slot]) outfits.preview[slot]=trap->R_RegisterModel(va("models/cosmetics/%s/%s.md3",ST_WearDir(slot),name.c_str()));
}
static void ST_OpenOutfits() {
    outfits.open=true;outfits.slot=outfits.page=0;outfits.reverse=false;
    outfits.model=spui.draft.value.model;
    outfits.bolts={};
    char key[2*MAX_QPATH+16];
    ST_OutfitKey(outfits.model.c_str(),key,sizeof(key));
    const std::string saved=SPUI_Var(key);
    const size_t comma=saved.find(',');
    for (int slot=0;slot<2;++slot) {
        auto &names=outfits.names[slot];
        names.clear();
        static const struct {int slot; const char *name;} bundled[]={
#include "st_wearable_catalog.inc"
        };
        for (const auto &item:bundled) if (item.slot==slot) names.emplace_back(item.name);
        char files[16384]={};
        int count=trap->FS_GetFileList(va("models/cosmetics/%s",ST_WearDir(slot)),".md3",files,sizeof(files));
        for(const char *p=files;count-->0 && *p;p+=strlen(p)+1) {
            std::string name=p;
            if (name.size()<5 || Q_stricmp(name.c_str()+name.size()-4,".md3")) continue;
            name=sp::lower(name.substr(0,name.size()-4));
            if(ST_WearableName(name.c_str())) names.push_back(name);
        }
        std::sort(names.begin(),names.end());
        names.erase(std::unique(names.begin(),names.end()),names.end());
        const std::string id=comma==std::string::npos ? "" : slot ? saved.substr(comma+1) : saved.substr(0,comma);
        outfits.picked[slot]=ST_WearableName(id.c_str())?id:"";
        ST_OutfitPreview(slot);
    }
    spui.field=0;spui.focus=710;
}
static void ST_OutfitClick(int id,int arg) {
    if(id==710 || id==711){outfits.slot=id-710;outfits.page=0;}
    else if(id==712){outfits.reverse=!outfits.reverse;outfits.page=0;}
    else if(id==713){outfits.picked[outfits.slot].clear();ST_OutfitPreview(outfits.slot);}
    else if(id==714 || id==715)outfits.page+=id==714?-1:1;
    else if(id>=720 && id<727){
        const auto &names=outfits.names[outfits.slot];
        if(arg>=0 && arg<(int)names.size()){outfits.picked[outfits.slot]=names[arg];ST_OutfitPreview(outfits.slot);}
    } else if(id==716 || id==717){
        if(id==717){
            char key[2*MAX_QPATH+16];
            ST_OutfitKey(outfits.model.c_str(),key,sizeof(key));
            trap->Cvar_Register(nullptr,key,"",CVAR_ARCHIVE);
            const auto pair=(outfits.picked[0].empty()?"-":outfits.picked[0])+","+ (outfits.picked[1].empty()?"-":outfits.picked[1]);
            trap->Cvar_Set(key,pair.c_str());
            trap->Cvar_Set("st_outfitRefresh","1");
        }
        outfits.open=false;spui.focus=718;
    }
}
static void ST_OutfitPage() {
    RUI_Shell();SCUI_Text(23,47,.88f,"Cosmetics",scuText);
    SCUI_Fit(24,80,365,.55f,outfits.model.c_str(),scuMuted);
    SPUI_Button(24,108,90,23,"Hats",710,0,outfits.slot==0);
    SPUI_Button(120,108,90,23,"Capes",711,0,outfits.slot==1);
    SPUI_Button(219,108,102,23,outfits.reverse?"Sort Z-A":"Sort A-Z",712);
    const auto &names=outfits.names[outfits.slot];
    const int pages=std::max(1,((int)names.size()+6)/7);
    outfits.page=std::max(0,std::min(outfits.page,pages-1));
    for(int j=0;j<7;++j){
        int k=outfits.page*7+j;if(k>=(int)names.size())break;
        if(outfits.reverse)k=(int)names.size()-1-k;
        SPUI_Button(24,151+j*28,306,25,names[k].c_str(),720+j,k,names[k]==outfits.picked[outfits.slot]);
    }
    SPUI_Button(24,358,74,23,"Previous",714,0,false,outfits.page>0);
    SCUI_Fit(112,363,64,.52f,va("%d / %d",outfits.page+1,pages),scuMuted);
    SPUI_Button(182,358,65,23,"Next",715,0,false,outfits.page+1<pages);
    SPUI_Button(251,358,85,23,"Unequip",713);
    RUI_Control(466,150,152,194,"panel",false,false);
    SCUI_Fit(422,353,196,.52f,va("Hat: %s",outfits.picked[0].empty()?"None":outfits.picked[0].c_str()),scuText);
    SCUI_Fit(422,376,196,.52f,va("Cape: %s",outfits.picked[1].empty()?"None":outfits.picked[1].c_str()),scuText);
    if(!outfits.picked[outfits.slot].empty()&&!outfits.preview[outfits.slot])
        SCUI_Fit(422,403,195,.48f,"Preview unavailable",scuMuted);
    SPUI_Button(24,447,76,21,"Back",716);
    SPUI_Button(483,447,133,21,"Save outfit",717);
}
void ST_DrawOutfitPreview(const itemDef_t *item,const refEntity_t *body,const vec3_t angles){
    if(!outfits.open || !SPUI_IsMenu() || !item->window.name || Q_stricmp(item->window.name,"st_profile_preview")) return;
    for(int i=0;i<2;++i) ST_DrawWearable(body,outfits.preview[i],i,uiInfo.uiDC.realTime,angles,nullptr,&outfits.bolts);
}
