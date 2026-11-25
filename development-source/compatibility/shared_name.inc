// One display name per client home. Store the name as data, including color codes.
static bool sharedNameLoaded;
static bool sharedNameStarted;
static std::string savedPlayerName;
static constexpr const char *sharedNameFile="player-name.txt";

bool CL_HasSharedName(){return sharedNameLoaded || sharedNameStarted;}

static bool validSharedName(const std::string &value){
    return !value.empty() && value.size()<MAX_INFO_VALUE &&
        value.find_first_of("\\\r\n;\"") == std::string::npos && value.find('\0')==std::string::npos;
}

void CL_LoadSharedName(){
    Cvar_Get("name","Padawan",CVAR_USERINFO|CVAR_ARCHIVE_ND,"Player name");
    std::ifstream file(JA_ProfilePath(sharedNameFile),std::ios::binary|std::ios::ate);
    if(!file)return;
    const auto length=file.tellg();
    if(length<=0 || length>=MAX_INFO_VALUE)return;
    std::string value(static_cast<size_t>(length),'\0');
    file.seekg(0);
    if(!file.read(&value[0],length) || !validSharedName(value))return;
    Cvar_Set("name",value.c_str());
    savedPlayerName=value;
    sharedNameLoaded=true;
}

void CL_SaveSharedName(const char *name){
    if(!sharedNameStarted || savedPlayerName==name || !validSharedName(name))return;
    const std::string temp="player-name-"+std::to_string(GetCurrentProcessId())+".tmp";
    const std::string tempPath=JA_ProfilePath(temp.c_str());
    const std::string path=JA_ProfilePath(sharedNameFile);
    fileHandle_t file=FS_SV_FOpenFileWrite(("SaberTrials/"+temp).c_str());
    if(file){
        const int length=static_cast<int>(strlen(name));
        const bool written=FS_Write(name,length,file)==length;
        FS_FCloseFile(file);
        if(written && STC_AtomicReplace(tempPath,path)){savedPlayerName=name;return;}
        std::remove(tempPath.c_str());
    }
    Com_Printf("Could not save the shared player name.\n");
}

void CL_StartSharedName(){
    sharedNameStarted=true;
    CL_SaveSharedName(Cvar_VariableString("name"));
}
