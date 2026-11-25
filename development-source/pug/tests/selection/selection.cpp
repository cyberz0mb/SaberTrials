#include <iostream>
#include "st_match_rules.h"
enum { GT_DUEL=3, GT_TEAM=6 };
#include "st_game_format.h"
#include "st_browser.h"
int main() {
    std::string error;
    for (int display : {0,3,4,6,7,8,10,11}) {
        int base = ST_BaseMode(display), format = ST_ModeFormat(display);
        if (ST_DisplayMode(base,format) != display) return 1;
        stmatch::Preset selected, loaded;
        selected.set("g_gametype",base);
        selected.set("st_gameFormat",format);
        if (!stmatch::decode(stmatch::encode(selected),loaded,error) ||
            loaded.get("st_gameFormat") != format || loaded.get("g_gametype") != base) return 2;
        std::cout << display << " -> " << base << "/" << format << "\n";
    }
    auto legacy=stmatch::encode(stmatch::Preset());
    auto start=legacy.find("rule st_gameFormat ");
    if (start==std::string::npos) return 3;
    legacy.erase(start,legacy.find('\n',start)-start+1);
    stmatch::Preset loaded;
    if (!stmatch::decode(legacy,loaded,error) || loaded.get("st_gameFormat")!=0) return 4;
    loaded.set("st_gameFormat",2);
    if (stmatch::validate(loaded,error)) return 5;
    if (stb_number("10",11)!=10 || stb_number("11",11)!=11) return 6;
    std::cout << "Legacy v1 accepted. Incompatible format rejected. Discovery IDs accepted.\n";
}
