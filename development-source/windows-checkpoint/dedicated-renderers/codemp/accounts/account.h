#pragma once
#include <cstdint>
#include <string>
namespace staccount {
extern const char* const Origin;
enum class Kind { None, Start, Poll, Profile, Logout };
struct Job { Kind kind=Kind::None; uint64_t serial=0; std::string method,path,body,bearer; };
struct Response { int status=0; std::string body; };
struct Saved { std::string token; double expires=0; bool logout=false; };
struct View { bool signedIn=false,busy=false; std::string name="Signed out",team,status="Log in with Discord."; };
bool ValidBrowserUrl(const std::string&);
class Client {
    Saved saved_; View view_; std::string request_,poll_,browser_;
    Kind active_=Kind::None; uint64_t serial_=0,revision_=0;
    bool start_=false,cancelled_=false; double due_=0,deadline_=0;
    void Clear(const char*); void Hide(); void Fail(const char*);
public:
    ~Client();
    void Restore(const Saved&,double now);
    void Login(double now);
    void Logout(double now);
    Job Next(double now);
    void Complete(const Job&,const Response&,double now);
    std::string TakeBrowserUrl();
    const View& Status()const{return view_;}
    const Saved& Record()const{return saved_;}
    uint64_t Revision()const{return revision_;}
};
Response Send(const Job&);
bool Save(const std::string& path,const Saved&);
bool Load(const std::string& path,Saved&);
bool Forget(const std::string& path);
std::string SessionPath();
bool OpenBrowser(const std::string&);
}
