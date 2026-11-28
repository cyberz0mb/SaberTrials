#include <windows.h>
#include <cstdio>
#include <string>

#ifdef ST_HOST_LAUNCHER
constexpr auto title = L"Saber Trials Dedicated Server";
constexpr auto program = L"\\SaberTrials\\SaberTrialsDed.x86_64.exe";
#else
constexpr auto title = L"Saber Trials";
constexpr auto program = L"\\SaberTrials\\client\\SaberTrials.x86_64.exe";
#endif

static int fail(const std::wstring& message) {
#ifdef ST_HOST_LAUNCHER
    std::fwprintf(stderr, L"%ls\n", message.c_str());
#else
    MessageBoxW(nullptr, message.c_str(), title, MB_OK | MB_ICONERROR);
#endif
    return 1;
}

static std::wstring environment(const wchar_t* name) {
    DWORD capacity = GetEnvironmentVariableW(name, nullptr, 0);
    std::wstring result(capacity, L'\0');
    if (capacity) result.resize(GetEnvironmentVariableW(name, result.data(), capacity));
    return result;
}

#ifdef ST_HOST_LAUNCHER
static BOOL WINAPI controlEvent(DWORD event) {
    // The dedicated engine receives console interrupts directly.
    return event == CTRL_C_EVENT || event == CTRL_BREAK_EVENT;
}
#endif

int WINAPI wWinMain(HINSTANCE, HINSTANCE, LPWSTR arguments, int) {
    std::wstring path(32768, L'\0');
    DWORD length = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (!length || length >= path.size()) return fail(L"Windows could not locate the launcher.");
    path.resize(length);
    const auto gameData = path.substr(0, path.find_last_of(L"\\/"));
    const auto payload = gameData + program;
    if (GetFileAttributesW((gameData + L"\\base\\assets0.pk3").c_str()) == INVALID_FILE_ATTRIBUTES)
        return fail(L"Extract the beta ZIP into Jedi Academy's GameData folder, beside the base folder.");
    if (GetFileAttributesW(payload.c_str()) == INVALID_FILE_ATTRIBUTES)
        return fail(L"Extract the complete beta ZIP into GameData. The installation is missing:\n" + payload);

    std::wstring command = L"\"" + payload + L"\" +set fs_basepath \"" + gameData + L"\"";
#ifndef ST_HOST_LAUNCHER
    const auto local = environment(L"LOCALAPPDATA");
    if (local.empty()) return fail(L"Windows could not locate your local settings folder.");
    command += L" +set fs_homepath \"" + local + L"\\SaberTrials\" +set fs_game SaberTrials"
        L" +set sv_pure 0 +set st_mvpPrototype 1 +set st_mvpTestSingleSaber 0 +set developer 0 +set logfile 1";
#endif
    if (arguments && *arguments) command += std::wstring(L" ") + arguments;
    // Scope the library search path to this process and its child.
    const auto searchPath = gameData + L";" + environment(L"PATH");
    if (!SetEnvironmentVariableW(L"PATH", searchPath.c_str())) return fail(L"Could not set the game library path.");

    STARTUPINFOW startup{};
    GetStartupInfoW(&startup);
    startup.cb = sizeof(startup);
    startup.dwFlags &= STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
    PROCESS_INFORMATION child{};
    DWORD flags = 0;
    BOOL inherit = (startup.dwFlags & STARTF_USESTDHANDLES) != 0;
#ifdef ST_HOST_LAUNCHER
    inherit = TRUE;
    flags = CREATE_SUSPENDED;
    // Holding a job makes stopping this launcher also stop the server it owns.
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!job || !SetInformationJobObject(job, JobObjectExtendedLimitInformation, &limits, sizeof(limits)))
        return fail(L"Windows could not initialize the dedicated server process.");
    SetConsoleCtrlHandler(controlEvent, TRUE);
#endif
    if (!CreateProcessW(payload.c_str(), command.data(), nullptr, nullptr, inherit, flags,
                        nullptr, gameData.c_str(), &startup, &child))
        return fail(L"Windows could not start " + payload + L" (error " + std::to_wstring(GetLastError()) + L").");
#ifdef ST_HOST_LAUNCHER
    // A host manager may already own this process in a restrictive job.
    AssignProcessToJobObject(job, child.hProcess);
    if (ResumeThread(child.hThread) == static_cast<DWORD>(-1)) {
        TerminateProcess(child.hProcess, 1);
        return fail(L"Windows could not resume the dedicated server.");
    }
#endif
    CloseHandle(child.hThread);
    WaitForSingleObject(child.hProcess, INFINITE);
    DWORD status = 1;
    GetExitCodeProcess(child.hProcess, &status);
    CloseHandle(child.hProcess);
#ifdef ST_HOST_LAUNCHER
    CloseHandle(job);
#endif
    return static_cast<int>(status);
}
