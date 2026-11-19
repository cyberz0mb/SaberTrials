#include "st_profile_core.h"
#include <cassert>
#include <iostream>
int main() {
    sp::Metadata tag;
    assert(sp::parseMetadata("displayName=Monkey D. Luffy\nuniverse=One Piece\nthemes=Anime, Fantasy\ngroup=luffy\n",tag));
    assert(tag.name=="Monkey D. Luffy" && tag.universe=="One Piece");
    assert(tag.themes==(sp::Anime|sp::Fantasy) && tag.group=="luffy");
    auto original=tag;
    assert(!sp::parseMetadata("displayName=Broken\nthis is not metadata\n",tag));
    assert(tag.name==original.name); // Malformed uploads cannot partially replace fallback tags.
    assert(!sp::parseMetadata(std::string(4097,'x'),tag));
    assert(!sp::parseMetadata("group=../../escape\n",tag));
    assert(!sp::parseMetadata("displayName=Name\nuniverse=Bad\tName\n",tag));
    assert(sp::parseMetadata("themes=Unrecognized theme\n",tag) && tag.themes==0);
    assert(sp::validSkin(std::string(29,'m')+"/default")); // Full skin path = 63 bytes.
    assert(!sp::validSkin(std::string(30,'m')+"/default"));
    assert(!sp::validSkin("foo/../bad") && !sp::validSkin("foo/a;quit"));
    assert(!sp::validSkin("foo/head_a1") && !sp::validSkin("foo/menu"));
    sp::Catalog catalog;
    assert(catalog.add("luffy/default",false,original));
    assert(catalog.add("luffy/red",false,original));
    assert(catalog.add("luffy_wano/default",false,original));
    assert(!catalog.add("LUFFY/default",false,original));
    sp::Metadata kyle;kyle.name="Kyle Katarn";kyle.universe="Star Wars";kyle.themes=sp::SciFi;
    assert(catalog.add("kyle/default",true,kyle));
    assert(catalog.add("new_upload/default",false,{}));
    catalog.finalize();
    assert(catalog.models.size()==3 && catalog.skinCount==5);
    sp::Filter f;auto rows=catalog.rows(f);assert(rows.size()==3);
    assert(catalog.models[rows[0]].name=="Kyle Katarn");
    f.reverse=true;assert(catalog.models[catalog.rows(f)[0]].name=="New Upload");
    f={};f.collection=1;assert(catalog.rows(f).size()==1);
    f.collection=2;assert(catalog.rows(f).size()==2);
    f={};f.themes=sp::Anime;rows=catalog.rows(f);assert(rows.size()==1);
    int luffy=rows[0];assert(catalog.variants(luffy,0).size()==2);
    assert(catalog.variants(luffy,1).size()==1 && catalog.variants(luffy,2).empty());
    f.themes=sp::Anime|sp::SciFi;assert(catalog.rows(f).size()==2);
    f.themes=sp::Uncategorized;assert(catalog.rows(f).size()==1);
    f={};f.search="WANO";assert(catalog.rows(f).size()==1);
    f.search="one piece";assert(catalog.rows(f).size()==1);
    f.search="never installed";assert(catalog.rows(f).empty());
    f={};f.favorites=true;assert(catalog.rows(f).empty());
    catalog.models[luffy].favorite=true;assert(catalog.rows(f).size()==1);
    sp::Identity live;live.model="jedi_hm/head_a1|torso_a1|lower_a1";live.name="Current";live.red="17";live.green="20";live.blue="30";
    sp::Draft draft;draft.open(live);draft.value.name="New name";
    assert(draft.canApply(live) && draft.value.model==live.model && draft.value.red=="17");
    auto outside=live;outside.model="kyle/default";assert(!draft.canApply(outside));
    draft.cancel();assert(draft.value.name=="Current" && !draft.dirty());
    assert(sp::favoriteKey("luffy")==sp::favoriteKey("LUFFY"));
    assert(sp::favoriteKey("luffy").size()<64);
    sp::Catalog large;
    for(int i=0;i<12008;++i)assert(large.add("model_"+std::to_string(i)+"/default",false,{}));
    large.finalize();
    sp::Filter massive;assert(large.rows(massive).size()==12008);
    massive.search="model_12007";assert(large.rows(massive).size()==1);
    assert(large.skinCount==12008);
    std::cout << "Profile metadata, catalog, path boundaries, filters and staged identity passed\n";
}
