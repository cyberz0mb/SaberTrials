#pragma once
#include <array>
#include <string>
#include <vector>
#include <cstdint>
#include "st_staff_game_api.h"
namespace st {
using Bytes=std::vector<unsigned char>;
using Nonce=std::array<unsigned char,32>;
using Generation=std::array<unsigned char,16>;
enum class Role { None=0, Moderator=1, Admin=2, Owner=3 };
const char* RoleName(Role role);
bool Random(void* out, size_t size);
std::string Hex(const unsigned char* bytes,size_t size);
bool Unhex(const std::string&,Bytes&,size_t expected=0);
bool ValidId(const std::string&);
bool ValidLabel(const std::string&);
bool PrivateWrite(const std::string& path,const Bytes& bytes,bool replace);
bool PrivateDirectory(const std::string& path);
bool ReadFileBytes(const std::string& path,Bytes& bytes,size_t maxSize=4096);
}
