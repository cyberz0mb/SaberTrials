#pragma once
#include <string>
namespace staccount {
struct ServerCredential {std::string id,token;};
std::string ServerCredentialPath(int port);
bool ImportServerCredential(const std::string& input,const std::string& output);
bool LoadServerCredential(const std::string& path,ServerCredential&);
}
