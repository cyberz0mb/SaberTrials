// Client-owned music transport. The frame loop only exchanges small snapshots with
// a worker; launching a player or waiting on Windows media never stalls rendering.
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <sstream>
#include <thread>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#ifdef min
#undef min
#undef max
#endif
#endif

namespace stmusic {
static const char *fields[] = {"st_musicSource", "st_musicTitle", "st_musicArtist", "st_musicStatus",
    "st_musicPlaying", "st_musicCanToggle", "st_musicCanPrevious", "st_musicCanNext", "st_musicPosition", "st_musicDuration"};
static const char *initial[] = {"Local", "", "", "Opening music player...", "0", "0", "0", "0", "0", "0"};
static cvar_t *visible, *autoStart;
static int nextPoll;

#ifdef _WIN32
struct Job { std::string line; bool launch; };
static std::thread worker;
static std::mutex lock;
static std::condition_variable ready;
static std::deque<Job> jobs;
static std::string response, error;
static bool pendingRefresh;
static std::atomic<bool> stopping(false);
static DWORD lastLaunch;
static std::string coverToken;
static const byte *coverView;
static qhandle_t coverShader;
static const int coverSize = 256;

static void setCover(const std::string& token) {
    if (coverToken == token) return;
    if (coverView) UnmapViewOfFile(coverView);
    coverView = nullptr;
    coverToken.clear();
    coverShader = 0;
    if (token.size() != 32 || token.find_first_not_of("0123456789abcdef") != std::string::npos) return;
    const std::wstring name = L"Local\\SaberTrials.Music.Cover." + std::wstring(token.begin(),token.end());
    HANDLE map = OpenFileMappingW(FILE_MAP_READ, FALSE, name.c_str());
    if (!map) return;
    coverView = static_cast<const byte *>(MapViewOfFile(map, FILE_MAP_READ, 0, 0, coverSize * coverSize * 4));
    CloseHandle(map);
    if (coverView) coverToken = token;
}

static bool exchange(const Job& job, std::string& output, std::string& problem) {
    wchar_t module[32768];
    DWORD len = GetModuleFileNameW(nullptr, module, ARRAY_LEN(module));
    if (!len || len >= ARRAY_LEN(module)) { problem = "Cannot locate the music player."; return false; }
    std::wstring dir(module, len);
    dir.erase(dir.find_last_of(L"\\/"));
    DWORD session = 0;
    ProcessIdToSessionId(GetCurrentProcessId(), &session);
    unsigned hash = 2166136261u;
    for (wchar_t c : dir) hash = (hash ^ (c >= L'a' && c <= L'z' ? c-32 : c)) * 16777619u;
    wchar_t name[100];
    swprintf_s(name, L"\\\\.\\pipe\\SaberTrials.Music.%lu.%08x", session, hash);
    DWORD start = GetTickCount();
    HANDLE pipe = INVALID_HANDLE_VALUE;
    while (!stopping && GetTickCount() - start < 5500) {
        pipe = CreateFileW(name, GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
                           SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION, nullptr);
        if (pipe != INVALID_HANDLE_VALUE) break;
        DWORD failure = GetLastError();
        if (failure != ERROR_PIPE_BUSY && failure != ERROR_FILE_NOT_FOUND) break;
        if (failure == ERROR_FILE_NOT_FOUND) {
            if (!job.launch) break;
            if (!lastLaunch || GetTickCount() - lastLaunch > 6000) {
                std::wstring exe = dir + L"\\SaberTrials Music.exe";
                std::wstring cmd = L"\"" + exe + L"\" --game " + std::to_wstring(GetCurrentProcessId());
                STARTUPINFOW si = {}; si.cb = sizeof(si);
                PROCESS_INFORMATION pi = {};
                lastLaunch = GetTickCount();
                if (!CreateProcessW(exe.c_str(), &cmd[0], nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                                    nullptr, dir.c_str(), &si, &pi)) {
                    problem = "Cannot start SaberTrials Music.exe from the client folder.";
                    return false;
                }
                CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
            }
        }
        Sleep(30);
    }
    if (pipe == INVALID_HANDLE_VALUE) { problem = "Music player unavailable. Reopen Music to connect."; return false; }
    DWORD sent = 0;
    bool ok = WriteFile(pipe, job.line.data(), (DWORD)job.line.size(), &sent, nullptr) && sent == job.line.size();
    start = GetTickCount();
    while (ok && !stopping && GetTickCount() - start < 4000 && output.size() < 8192) {
        DWORD available = 0;
        if (!PeekNamedPipe(pipe, nullptr, 0, nullptr, &available, nullptr)) break;
        if (!available) { Sleep(15); continue; }
        char buf[1024];
        DWORD received = 0;
        if (!ReadFile(pipe, buf, std::min<DWORD>(available, sizeof(buf)), &received, nullptr) || !received) break;
        output.append(buf, received);
        if (output.back() == '\n') { CloseHandle(pipe); output.pop_back(); return true; }
    }
    CloseHandle(pipe);
    problem = "Music player did not respond. Check the desktop player.";
    return false;
}

static void run() {
    while (!stopping) {
        Job job;
        {
            std::unique_lock<std::mutex> guard(lock);
            ready.wait(guard, [] { return stopping || !jobs.empty(); });
            if (stopping) break;
            job = jobs.front();
            jobs.pop_front();
        }
        std::string reply, problem;
        bool ok = exchange(job, reply, problem);
        std::lock_guard<std::mutex> guard(lock);
        if (job.line == "refresh\t\tcover1\n") pendingRefresh = false;
        response = ok ? reply : "";
        error = problem;
    }
}

static void post(const std::string& verb, const std::string& source, std::string arg, bool launch = true) {
    // First use opts this profile into reconnecting the helper on its next game launch.
    if (launch && autoStart && autoStart->integer < 0) Cvar_Set("st_musicAutoStart","1");
    arg.erase(std::remove_if(arg.begin(), arg.end(), [](unsigned char c) { return c < 32 || c == 127; }), arg.end());
    if (arg.size() > 1500) { Com_Printf("Music query is too long.\n"); return; }
    std::lock_guard<std::mutex> guard(lock);
    if (verb == "refresh" && pendingRefresh && !launch) return;
    if (jobs.size() >= 24) { Com_Printf("Music player is busy. Try again shortly.\n"); return; }
    if (verb == "refresh") { pendingRefresh = true; arg = "cover1"; }
    jobs.push_back({verb + "\t" + source + "\t" + arg + "\n", launch});
    if (!worker.joinable()) worker = std::thread(run);
    ready.notify_one();
}
#else
static void post(const std::string&, const std::string&, const std::string&, bool = true) {
    Cvar_Set("st_musicStatus", "The music companion requires Windows.");
}
#endif

static void panel() {
    if (visible->integer && (Key_GetCatcher() & KEYCATCH_UI))
        Cbuf_ExecuteText(EXEC_INSERT, "ui_musicclose\n");
    else {
        post("refresh","","");
        Cbuf_ExecuteText(EXEC_INSERT, "ui_openmenu st_music_player\n");
    }
}

static void command() {
    bool generic = !Q_stricmp(Cmd_Argv(0), "st_musiccmd");
    std::string source = generic ? "" : !Q_stricmp(Cmd_Argv(0),"spotify") ? "Spotify" :
        !Q_stricmp(Cmd_Argv(0),"applemusic") ? "Apple Music" : "YouTube Music";
    std::string verb = Cmd_Argv(1), arg = Cmd_ArgsFrom(2);
    if (!generic && verb.empty()) { post("source", "", source); panel(); return; }
    if (generic && verb == "source" && arg.empty()) verb = "cycle";
    if (verb == "play" && !arg.empty()) verb = "playquery";
    if (generic && verb == "search" && arg.empty()) arg = Cvar_VariableString("st_musicQuery");
    static const char *allowed[] = {"cycle","source","refresh","desktop","toggle","play","playquery","pause","next","previous","open","search","volume"};
    for (const char *action : allowed) {
        if (verb == action) { post(verb,source,arg); return; }
    }
    Com_Printf("Music commands: play [song], pause, previous, next, search [song], open.\n");
}

static const char *aliases[] = {"st_musiccmd","spotify","applemusic","ytmusic","youtubemusic"};
static const char *shortcuts[] = {"playnext", "playprev", "pausemusic", "search", "musicvolume"};
static void shortcut() {
    const char *name = Cmd_Argv(0);
    if (!Q_stricmp(name,"musicvolume")) {
        if (Cmd_Argc() == 2) post("volume","",Cmd_Argv(1));
        else Com_Printf("Use musicvolume 0 to 100, or musicvolume +5 / -5.\n");
        return;
    }
    if (!Q_stricmp(name,"search")) {
        std::string query = Cmd_ArgsFrom(1);
        if (!query.empty()) post("search","",query);
        else if (visible->integer && (Key_GetCatcher() & KEYCATCH_UI))
            Cbuf_ExecuteText(EXEC_INSERT, "ui_musicsearch\n");
        else {
            post("refresh","","");
            Cbuf_ExecuteText(EXEC_INSERT, "ui_openmenu st_music_player\nui_musicsearch\n");
        }
        return;
    }
    post(!Q_stricmp(name,"playnext") ? "next" : !Q_stricmp(name,"playprev") ? "previous" : "pause","","");
}
static void init() {
    visible = Cvar_Get("st_musicVisible","0",CVAR_TEMP);
    autoStart = Cvar_Get("st_musicAutoStart","-1",CVAR_ARCHIVE);
    Cvar_Get("st_musicQuery","",CVAR_TEMP);
    Cvar_Get("st_musicVolume","-1",CVAR_ROM);
    Cvar_Get("st_musicCanVolume","0",CVAR_ROM);
    Cvar_Get("st_musicVolumeLabel","Volume",CVAR_ROM);
    for (size_t i=0; i<ARRAY_LEN(fields); ++i) Cvar_Get(fields[i],initial[i],CVAR_ROM);
    Cmd_AddCommand("st_music",panel,"Open or close the music player");
    for (const char *name : aliases) Cmd_AddCommand(name,command,"Control the local music player");
    for (const char *name : shortcuts) Cmd_AddCommand(name,shortcut,"Control or search the selected music source");
#ifdef _WIN32
    if (autoStart->integer > 0) post("attach","",std::to_string(GetCurrentProcessId()));
#endif
}

static void frame() {
    if (!visible) return;
#ifdef _WIN32
    std::string reply, problem;
    {
        std::lock_guard<std::mutex> guard(lock);
        reply.swap(response); problem.swap(error);
    }
    if (!problem.empty()) {
        setCover("");
        Cvar_Set("st_musicCanVolume","0");
        Cvar_Set("st_musicVolume","-1");
        Cvar_Set("st_musicStatus",problem.c_str());
        for (int n=4; n<10; ++n) Cvar_Set(fields[n],"0");
    } else if (!reply.empty()) {
        std::istringstream in(reply);
        std::vector<std::string> parts;
        std::string part;
        while (std::getline(in,part,'\t')) parts.push_back(part);
        if (parts.size() == ARRAY_LEN(fields) || parts.size() == ARRAY_LEN(fields) + 3) {
            if (parts.size() > ARRAY_LEN(fields)) {
                setCover(parts[10]);
                int level = atoi(parts[11].c_str());
                bool available = level >= 0 && level <= 100;
                Cvar_Set("st_musicCanVolume",available ? "1" : "0");
                Cvar_Set("st_musicVolume",available ? parts[11].c_str() : "-1");
                Cvar_Set("st_musicVolumeLabel",parts[12].c_str());
            }
            else if (parts[0] != Cvar_VariableString(fields[0]) || parts[1] != Cvar_VariableString(fields[1]) ||
                     parts[2] != Cvar_VariableString(fields[2])) {
                setCover("");
                Cvar_Set("st_musicCanVolume","0");
                Cvar_Set("st_musicVolume","-1");
            }
            for (size_t i=0; i<ARRAY_LEN(fields); ++i) {
                std::replace(parts[i].begin(),parts[i].end(),'^',' ');
                Cvar_Set(fields[i],parts[i].c_str());
            }
        }
    }
#endif
    if (visible->integer && (Key_GetCatcher() & KEYCATCH_UI) && cls.realtime >= nextPoll) {
        nextPoll = cls.realtime + 750;
        post("refresh","","",false);
    }
}
static void shutdown() {
    visible = nullptr;
#ifdef _WIN32
    {
        std::lock_guard<std::mutex> guard(lock);
        stopping = true;
    }
    ready.notify_one();
    if (worker.joinable()) worker.join();
    jobs.clear(); error.clear(); response.clear();
    pendingRefresh = false;
    setCover("");
    lastLaunch = 0;
    stopping = false;
#endif
    nextPoll = 0;
    Cmd_RemoveCommand("st_music");
    for (const char *name : aliases) Cmd_RemoveCommand(name);
    for (const char *name : shortcuts) Cmd_RemoveCommand(name);
}
}

qhandle_t CL_RegisterMusicUIShader(const char *name) {
    if (!name || !re) return 0;
    if (strcmp(name, "st_music/ui/current_cover")) return re->RegisterShaderNoMip(name);
#ifdef _WIN32
    if (stmusic::coverView && !stmusic::coverShader && re && re->ST_ChatUpload)
        stmusic::coverShader = re->ST_ChatUpload(223, stmusic::coverSize, stmusic::coverSize, stmusic::coverView);
    return stmusic::coverShader;
#else
    return 0;
#endif
}

void CL_ResetMusicShader() {
#ifdef _WIN32
    stmusic::coverShader = 0;
#endif
}
