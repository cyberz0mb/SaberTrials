// All chat producers (chat field, console, binds and client modules) converge here.
static std::string CL_OutgoingChat(const char *command) {
    const auto prefix=ST_ChatColorPrefix();
    if (prefix.empty()) return command;
    const std::string line(command);
    size_t end=line.find_first_of(" \t");
    if (end==std::string::npos) return line;
    const auto verb=line.substr(0,end);
    const bool tell=!Q_stricmp(verb.c_str(),"tell");
    if (!tell && Q_stricmp(verb.c_str(),"say") && Q_stricmp(verb.c_str(),"say_team")) return line;
    size_t body=line.find_first_not_of(" \t",end);
    if (tell && body!=std::string::npos) {
        end=line.find_first_of(" \t",body);
        body=end==std::string::npos?end:line.find_first_not_of(" \t",end);
    }
    if (body==std::string::npos) return line;
    bool quoted=line[body]=='"';
    if (quoted) ++body;
    end=line.find_last_not_of("\r\n");
    if (end==std::string::npos || end<body) return line;
    ++end;
    if (quoted && line[end-1]=='"') --end;
    if (end<=body || Q_IsColorString(line.c_str()+body)) return line;
    return line.substr(0,body)+ST_ChatColorized(line.substr(body,end-body).c_str())+line.substr(end);
}
