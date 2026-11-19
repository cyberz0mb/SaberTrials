#pragma once
#include "st_staff_types.h"
namespace st {
class Identity {
 unsigned char key_[64]; bool loaded_=false;
 void Clear();
 bool Save(const std::string& path,bool replace);
public:
 Identity(); ~Identity();
 Identity(const Identity&)=delete; Identity& operator=(const Identity&)=delete;
 bool LoadOrCreate(const std::string& path,bool explicitCreate);
 std::string PublicId() const;
 Bytes Sign(const Bytes&) const;
 static bool Verify(const std::string& publicId,const Bytes&,const Bytes& signature);
 bool ExportProtected(const std::string& path,const std::string& passphrase) const;
 bool ImportProtected(const std::string& path,const std::string& passphrase,const std::string& destination);
};
}
