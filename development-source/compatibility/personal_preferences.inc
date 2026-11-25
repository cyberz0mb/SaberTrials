// OpenJK archives to the current mod. Carry explicit personal UI edits back to
// the launch profile without importing any of the server mod's config or binds.
static bool sharePreference(const char *name) {
    static const char *shared[]={"st_chatSize","st_chatWidth","st_chatHeight","st_chatOpacity",
        "st_chatColor","st_translate","st_translateOriginal","st_translateSource","st_translateTarget",
        "st_personalChat","st_personalHud","st_hudScale","st_hudOpacity","st_hudPulse",
        "st_menuLanguage","st_netMode","st_netStats","st_emoteWheelToggle"};
    if(std::none_of(std::begin(shared),std::end(shared),[&](const char *n){return !strcmp(name,n);}))return true;
    const std::string value=Cvar_VariableString(name);
    if(value.empty() || value.size()>20 || value.find_first_not_of("-0123456789.")!=std::string::npos)return false;
    const std::string path=JA_ProfilePath(Q3CONFIG_CFG);
    auto read=[&](std::string &text){
        errno=0;std::ifstream input(path,std::ios::binary|std::ios::ate);
        if(!input)return errno==ENOENT;
        const auto length=input.tellg();
        if(length<0 || length>4*1024*1024)return false;
        text.resize(size_t(length));input.seekg(0);if(length)input.read(&text[0],length);
        return bool(input);
    };
    std::string original;
    if(!read(original))return false;
    const std::string prefix=std::string("seta ")+name+" \"",tag=" // Saber Trials personal menu";
    std::string merged;size_t begin=0;
    while(begin<original.size()) {
        const size_t end=original.find('\n',begin);
        const size_t length=end==std::string::npos?original.size()-begin:end+1-begin;
        const std::string line=original.substr(begin,length);
        if(line.compare(0,prefix.size(),prefix) || line.find(tag)==std::string::npos)merged+=line;
        begin+=length;
    }
    if(!merged.empty()&&merged.back()!='\n')merged+="\r\n";
    merged+=prefix+value+"\""+tag+"\r\n";
    if(merged==original)return true;
    const std::string temp="personal-menu-"+std::to_string(reinterpret_cast<uintptr_t>(&personalExports))+"-"+std::to_string(Sys_Milliseconds())+".tmp";
    fileHandle_t f=FS_SV_FOpenFileWrite(("SaberTrials/"+temp).c_str());
    if(!f)return false;
    bool written=FS_Write(merged.data(),int(merged.size()),f)==(int)merged.size();FS_FCloseFile(f);
    std::string current;
    if(written && read(current) && current==original && STC_AtomicReplace(JA_ProfilePath(temp.c_str()),path))return true;
    std::remove(JA_ProfilePath(temp.c_str()).c_str());return false;
}
