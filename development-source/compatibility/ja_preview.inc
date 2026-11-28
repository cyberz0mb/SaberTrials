// Resolve preview clips against the animation pack visible to the current game.
// The remote server still selects the animation when the player uses an emote.
static std::vector<stemote::Clip> EM_JaCatalog() {
    std::vector<stemote::Clip> clips(jawheel::count);
    for (int i=0; i<jawheel::count; ++i) {
        clips[i].id=jawheel::choice(i).command;
        clips[i].label=jawheel::choice(i).label;
    }
    fileHandle_t file=0;
    int length=trap->FS_Open("models/players/_humanoid/animation.cfg",&file,FS_READ);
    if (!file) return clips;
    std::string data;
    if (length>0 && length<=256*1024) {
        data.resize(length);
        trap->FS_Read(&data[0],length,file);
    }
    trap->FS_Close(file);
    std::istringstream lines(data);
    std::string line;
    while (std::getline(lines,line)) {
        std::istringstream row(line);
        std::string animation;
        int first,frames,loop,fps;
        if (!(row>>animation>>first>>frames>>loop>>fps) || first<0 || first>100000 ||
            frames<1 || frames>2000 || fps<1 || fps>200) continue;
        for (int i=0; i<jawheel::count; ++i) {
            if (Q_stricmp(animation.c_str(),jawheel::choice(i).animation)) continue;
            clips[i].first=first;
            clips[i].frames=frames;
            clips[i].fps=fps;
        }
    }
    return clips;
}
