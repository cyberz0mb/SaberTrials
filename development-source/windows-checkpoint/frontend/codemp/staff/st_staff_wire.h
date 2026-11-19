#pragma once
#include "st_staff_protocol.h"
namespace st {
// All network replies are server-signed and bound to the local outstanding request.
Bytes SessionMessage(const Bytes& transcript,const Nonce& session);
bool ReadSessionMessage(const Bytes&,const Bytes& transcript,Nonce& out);
Bytes ResultMessage(const Nonce& session,uint64_t sequence,bool ok,const std::string& message);
bool ReadResultMessage(const Bytes&,const Nonce&,uint64_t sequence,bool& ok,std::string& message);
std::string PrivateRoot();
bool NumericAddress(const std::string& address);
bool AskPassphrase(std::string& passphrase,bool confirm);
}
