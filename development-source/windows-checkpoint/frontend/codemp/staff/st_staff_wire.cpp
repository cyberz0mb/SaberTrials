#include "st_staff_wire.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <sodium.h>
#include <cstring>
namespace st {
Bytes SessionMessage(const Bytes& transcript,const Nonce& session){Bytes b={'S','T','S',1};b.resize(36);crypto_hash_sha256(b.data()+4,transcript.data(),transcript.size());b.insert(b.end(),session.begin(),session.end());return b;}
bool ReadSessionMessage(const Bytes& b,const Bytes& transcript,Nonce& out){if(b.size()!=68||std::memcmp(b.data(),"STS\1",4))return false;unsigned char hash[32];crypto_hash_sha256(hash,transcript.data(),transcript.size());if(sodium_memcmp(hash,b.data()+4,32))return false;std::memcpy(out.data(),b.data()+36,32);return true;}
Bytes ResultMessage(const Nonce& session,uint64_t seq,bool ok,const std::string& message){Bytes b={'S','T','R',1};b.insert(b.end(),session.begin(),session.end());for(int i=0;i<8;i++)b.push_back((unsigned char)(seq>>(i*8)));b.push_back(ok?1:0);auto s=message.substr(0,330);b.insert(b.end(),s.begin(),s.end());return b;}
bool ReadResultMessage(const Bytes& b,const Nonce& session,uint64_t seq,bool& ok,std::string& message){if(b.size()<45||b.size()>375||std::memcmp(b.data(),"STR\1",4)||sodium_memcmp(b.data()+4,session.data(),32))return false;uint64_t s=0;for(int i=0;i<8;i++)s|=(uint64_t)b[36+i]<<(i*8);if(s!=seq||b[44]>1)return false;ok=b[44]!=0;message.assign((const char*)b.data()+45,b.size()-45);for(unsigned char c:message)if(c<32||c==127)return false;return true;}
std::string PrivateRoot(){wchar_t w[32768];DWORD n=GetEnvironmentVariableW(L"LOCALAPPDATA",w,32768);if(!n||n>=32768)return {};int len=WideCharToMultiByte(CP_UTF8,0,w,n,NULL,0,NULL,NULL);std::string s(len,'\0');WideCharToMultiByte(CP_UTF8,0,w,n,&s[0],len,NULL,NULL);s+="/SaberTrialsStaff";return PrivateDirectory(s)?s:std::string();}
bool NumericAddress(const std::string& address){
 if(address.empty()||address.size()>90)return false;for(char c:address)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')||(c>='A'&&c<='F')||c==':'||c=='.'||c=='['||c==']'))return false;
 std::string host,port;int family=AF_INET;
 if(address[0]=='['){size_t end=address.find(']');if(end==std::string::npos||end+2>=address.size()||address[end+1]!=':')return false;host=address.substr(1,end-1);port=address.substr(end+2);family=AF_INET6;}
 else {size_t colon=address.find(':');if(colon==std::string::npos)return false;host=address.substr(0,colon);port=address.substr(colon+1);}
 if(port.empty()||port.size()>5)return false;unsigned int p=0;for(char c:port){if(c<'0'||c>'9')return false;p=p*10+c-'0';}if(!p||p>65535)return false;
 unsigned char out[16];return InetPtonA(family,host.c_str(),out)==1;
}
namespace {
struct Prompt {std::string* out;bool confirm;};
INT_PTR CALLBACK PasswordProc(HWND window,UINT msg,WPARAM wp,LPARAM lp){
 auto* p=(Prompt*)GetWindowLongPtrW(window,DWLP_USER);
 if(msg==WM_INITDIALOG){p=(Prompt*)lp;SetWindowLongPtrW(window,DWLP_USER,lp);
  CreateWindowW(L"STATIC",p->confirm?L"Backup passphrase (at least 12 characters)":L"Backup passphrase",WS_CHILD|WS_VISIBLE,15,12,350,22,window,NULL,NULL,NULL);
  auto edit=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|ES_PASSWORD|ES_AUTOHSCROLL,15,38,350,24,window,(HMENU)101,NULL,NULL);SendMessageW(edit,EM_SETLIMITTEXT,256,0);
  if(p->confirm){CreateWindowW(L"STATIC",L"Confirm passphrase",WS_CHILD|WS_VISIBLE,15,70,350,20,window,NULL,NULL,NULL);auto e=CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|ES_PASSWORD|ES_AUTOHSCROLL,15,94,350,24,window,(HMENU)102,NULL,NULL);SendMessageW(e,EM_SETLIMITTEXT,256,0);}
  CreateWindowW(L"BUTTON",L"Continue",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_DEFPUSHBUTTON,160,132,95,28,window,(HMENU)IDOK,NULL,NULL);
  CreateWindowW(L"BUTTON",L"Cancel",WS_CHILD|WS_VISIBLE|WS_TABSTOP,270,132,95,28,window,(HMENU)IDCANCEL,NULL,NULL);SetFocus(edit);return FALSE;
 }
 if(msg==WM_COMMAND && LOWORD(wp)==IDCANCEL){EndDialog(window,0);return TRUE;}
 if(msg==WM_COMMAND && LOWORD(wp)==IDOK&&p){wchar_t a[257]={},b[257]={};GetDlgItemTextW(window,101,a,257);GetDlgItemTextW(window,102,b,257);bool good=!p->confirm||(wcslen(a)>=12&&wcscmp(a,b)==0);
  if(good){int n=WideCharToMultiByte(CP_UTF8,0,a,-1,NULL,0,NULL,NULL);p->out->resize(n);WideCharToMultiByte(CP_UTF8,0,a,-1,&(*p->out)[0],n,NULL,NULL);p->out->resize(n-1);}
  SecureZeroMemory(a,sizeof(a));SecureZeroMemory(b,sizeof(b));if(good)EndDialog(window,1);else MessageBoxW(window,L"Use at least 12 characters and matching entries.",L"Saber Trials",MB_OK);return TRUE;
 }return FALSE;
}
}
bool AskPassphrase(std::string& pass,bool confirm){
 struct Template {DLGTEMPLATE dialog;WORD menu,windowClass;wchar_t title[32];} t={};t.dialog.style=WS_POPUP|WS_CAPTION|WS_SYSMENU|DS_MODALFRAME|DS_CENTER;t.dialog.cx=260;t.dialog.cy=115;wcscpy_s(t.title,L"Saber Trials protected backup");Prompt p{&pass,confirm};return DialogBoxIndirectParamW(GetModuleHandleW(NULL),&t.dialog,GetActiveWindow(),PasswordProc,(LPARAM)&p)==1;
}
}
