/* Offline helper lifecycle. No game/renderer calls on the background thread. */
#ifndef ST_TRANSLATION_CORE_H
#define ST_TRANSLATION_CORE_H
#include "st_translation_api.h"
#include "st_utf8.h"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <deque>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace sttr {
inline std::string hex(const char *text) {
    static const char digits[]="0123456789abcdef";
    std::string out;
    for(const unsigned char *p=(const unsigned char*)text;*p;++p) {
        out+=digits[*p>>4];out+=digits[*p&15];
    }
    return out.empty()?"-":out;
}
inline bool unhex(const std::string& text,char *out,size_t size) {
    if(text.empty() || text.size()%2 || text.size()/2>=size) return false;
    auto digit=[](char c)->int {return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;};
    size_t n=0;
    for(size_t i=0;i<text.size();i+=2) {
        int a=digit(text[i]),b=digit(text[i+1]);if(a<0||b<0)return false;
        unsigned char c=(unsigned char)((a<<4)|b);
        if(c<32 || c==127 || c=='^') return false;
        out[n++]=(char)c;
    }
    out[n]=0;return ST_UTF8Valid(out)!=0;
}
inline bool parse(const std::string& line,unsigned ticket,int target,stTranslationResult_t& result) {
    std::istringstream stream(line);std::string magic,status,encoded,extra;unsigned received=0;
    if(!(stream>>magic>>received>>status>>encoded) || (stream>>extra) || magic!="STTR2" || received!=ticket) return false;
    result={};result.ticket=ticket;result.target=target;
    return status=="ok" && unhex(encoded,result.text,sizeof(result.text));
}

class Worker {
    using Clock=std::chrono::steady_clock;
    struct Job {unsigned ticket,epoch;stTranslationRequest_t request;Clock::time_point created;};
    std::mutex mutex;
    std::condition_variable wake;
    std::deque<Job> jobs;
    std::deque<stTranslationResult_t> results;
    std::thread thread;
    std::atomic<bool> stopping{false};
    std::atomic<unsigned> epoch{1};
    unsigned nextTicket=0;
    std::wstring directory;
#ifdef _WIN32
    HANDLE process=nullptr,jobObject=nullptr,input=nullptr,output=nullptr;
    void closeProcess() {
        if(jobObject) {CloseHandle(jobObject);jobObject=nullptr;}
        if(process) {TerminateProcess(process,0);CloseHandle(process);process=nullptr;}
        if(input) {CloseHandle(input);input=nullptr;}
        if(output) {CloseHandle(output);output=nullptr;}
    }
    bool startProcess() {
        if(process) return true;
        SECURITY_ATTRIBUTES sa={sizeof(sa),nullptr,TRUE};
        HANDLE childIn=nullptr,childOut=nullptr;
        if(!CreatePipe(&childIn,&input,&sa,65536) || !CreatePipe(&output,&childOut,&sa,65536)) {
            if(childIn)CloseHandle(childIn);if(childOut)CloseHandle(childOut);closeProcess();return false;
        }
        SetHandleInformation(input,HANDLE_FLAG_INHERIT,0);SetHandleInformation(output,HANDLE_FLAG_INHERIT,0);
        HANDLE null=CreateFileW(L"NUL",GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,OPEN_EXISTING,0,nullptr);
        STARTUPINFOEXW startup={};startup.StartupInfo.cb=sizeof(startup);
        startup.StartupInfo.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;startup.StartupInfo.wShowWindow=SW_HIDE;
        startup.StartupInfo.hStdInput=childIn;startup.StartupInfo.hStdOutput=childOut;startup.StartupInfo.hStdError=null;
        SIZE_T attributeSize=0;InitializeProcThreadAttributeList(nullptr,1,0,&attributeSize);
        std::vector<unsigned char> attributes(attributeSize);
        startup.lpAttributeList=(LPPROC_THREAD_ATTRIBUTE_LIST)attributes.data();
        bool attributesReady=InitializeProcThreadAttributeList(startup.lpAttributeList,1,0,&attributeSize)!=0;
        HANDLE inherited[]={childIn,childOut,null};
        bool handlesReady=attributesReady && null!=INVALID_HANDLE_VALUE &&
            UpdateProcThreadAttribute(startup.lpAttributeList,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,inherited,sizeof(inherited),nullptr,nullptr);
        PROCESS_INFORMATION info={};
        std::wstring exe=directory+L"\\python.exe";
        std::wstring command=L"\""+exe+L"\" -I -B \""+directory+L"\\worker.py\"";
        jobObject=CreateJobObjectW(nullptr,nullptr);
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits={};
        limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE|JOB_OBJECT_LIMIT_PROCESS_MEMORY;
        limits.ProcessMemoryLimit=(SIZE_T)4096*1024*1024;
        bool ok=handlesReady && jobObject && SetInformationJobObject(jobObject,JobObjectExtendedLimitInformation,&limits,sizeof(limits)) &&
            CreateProcessW(exe.c_str(),&command[0],nullptr,nullptr,TRUE,
                CREATE_NO_WINDOW|CREATE_SUSPENDED|BELOW_NORMAL_PRIORITY_CLASS|EXTENDED_STARTUPINFO_PRESENT,
                nullptr,directory.c_str(),&startup.StartupInfo,&info);
        if(attributesReady)DeleteProcThreadAttributeList(startup.lpAttributeList);
        CloseHandle(childIn);CloseHandle(childOut);if(null!=INVALID_HANDLE_VALUE)CloseHandle(null);
        if(!ok) {closeProcess();return false;}
        process=info.hProcess;
        if(!AssignProcessToJobObject(jobObject,process)) {CloseHandle(info.hThread);closeProcess();return false;}
        ResumeThread(info.hThread);CloseHandle(info.hThread);return true;
    }
    bool exchange(const Job& job,std::string& response) {
        if(!startProcess()) return false;
        const auto& q=job.request;
        std::string request="STTR2 "+std::to_string(job.ticket)+" "+std::to_string(q.source)+" "+
            std::to_string(q.target)+" "+hex(q.text)+" "+hex(q.names)+"\n";
        DWORD written=0;
        if(!WriteFile(input,request.data(),(DWORD)request.size(),&written,nullptr) || written!=request.size()) return false;
        auto deadline=Clock::now()+std::chrono::seconds(8);
        while(!stopping && epoch==job.epoch && Clock::now()<deadline) {
            DWORD available=0;
            if(!PeekNamedPipe(output,nullptr,0,nullptr,&available,nullptr)) return false;
            if(available) {
                char buffer[1024];DWORD count=0;
                if(!ReadFile(output,buffer,available<sizeof(buffer)?available:sizeof(buffer),&count,nullptr)) return false;
                response.append(buffer,count);
                if(response.size()>8192) return false;
                if(response.find('\n')!=std::string::npos) return true;
            } else if(WaitForSingleObject(process,0)!=WAIT_TIMEOUT) return false;
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
        return false;
    }
#else
    void closeProcess() {}
    bool exchange(const Job&,std::string&) {return false;}
#endif
    void run() {
        unsigned activeEpoch=epoch;
        auto retry=Clock::time_point::min();
        while(!stopping) {
            Job job;
            {
                std::unique_lock<std::mutex> lock(mutex);
                wake.wait_for(lock,std::chrono::milliseconds(100),[&]{return stopping||!jobs.empty()||activeEpoch!=epoch;});
                if(stopping)break;
                if(activeEpoch!=epoch) {activeEpoch=epoch;closeProcess();retry=Clock::time_point::min();status=0;}
                if(jobs.empty())continue;
                job=jobs.front();jobs.pop_front();
            }
            if(job.epoch!=epoch || Clock::now()-job.created>std::chrono::seconds(8)) continue;
            if(Clock::now()<retry)continue;
            std::string line;
            status=4;
            if(!exchange(job,line)) {
                closeProcess();status=2;retry=Clock::now()+std::chrono::seconds(30);continue;
            }
            if(job.epoch!=epoch)continue;
            status=1;
            stTranslationResult_t result;
            if(parse(line,job.ticket,job.request.target,result)) {
                std::lock_guard<std::mutex> lock(mutex);
                if(job.epoch!=epoch)continue;
                if(results.size()==16)results.pop_front();
                results.push_back(result);
            } else if(line.find(" missing ")!=std::string::npos) status=3;
        }
        closeProcess();
    }
public:
    std::atomic<int> status{0}; /* 0 idle, 1 ready, 2 helper unavailable, 3 pack unavailable, 4 busy */
    ~Worker() {shutdown();}
    unsigned submit(const stTranslationRequest_t& request,const std::wstring& path) {
        if(!memchr(request.text,0,sizeof(request.text)) || !memchr(request.names,0,sizeof(request.names)) ||
           !request.text[0] || request.source<0 || request.source>ST_TRANSLATION_LANGUAGES ||
           request.target<1 || request.target>ST_TRANSLATION_LANGUAGES) return 0;
        std::lock_guard<std::mutex> lock(mutex);
        if(stopping || jobs.size()>=16) return 0;
        if(!thread.joinable()) {
            directory=path;
            try {thread=std::thread(&Worker::run,this);}catch(...) {status=2;return 0;}
        }
        if(++nextTicket==0) ++nextTicket;
        jobs.push_back({nextTicket,epoch.load(),request,Clock::now()});wake.notify_one();return nextTicket;
    }
    bool poll(stTranslationResult_t& result) {
        std::lock_guard<std::mutex> lock(mutex);
        if(results.empty())return false;
        result=results.front();results.pop_front();return true;
    }
    void reset() {
        std::lock_guard<std::mutex> lock(mutex);
        ++epoch;jobs.clear();results.clear();status=0;wake.notify_one();
    }
    void shutdown() {
        stopping=true;++epoch;wake.notify_one();
        if(thread.joinable())thread.join();
    }
};
}
#endif
