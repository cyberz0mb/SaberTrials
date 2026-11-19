#pragma once
#include "st_staff_types.h"
namespace st {
// Linux-only owner-private storage. Keep both the file and its .protect key in backups.
bool ProtectFile(const std::string& path,const char magic[5],const Bytes&,bool replace);
bool UnprotectFile(const std::string& path,const char magic[5],Bytes&);
bool PrivateFile(const std::string& path);
std::string LinuxStateRoot(const char* component);
}
