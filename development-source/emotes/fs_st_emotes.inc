/* A pack contributes one bounded body clip. It is never mounted as a game PK3. */
#include "../ghoul2/st_gla_compat.h"
#include "../game/bg_public.h"
#include "st_emotes.h"
#include <zlib.h>

namespace {
constexpr const char* canonicalEmoteGla = "models/players/_humanoid/_humanoid.gla";
struct EmoteData {
    stemote::Clip clip;
    std::vector<unsigned char> poses;
};
static std::vector<EmoteData> stEmotePacks;
static std::vector<unsigned char> stEmoteGla;

static std::vector<unsigned char> FS_EmoteEntry(unzFile zip, const char* name, unsigned limit) {
    unz_file_info info = {};
    if (!zip || unzLocateFile(zip, name, 1) != UNZ_OK ||
        unzGetCurrentFileInfo(zip, &info, nullptr, 0, nullptr, 0, nullptr, 0) != UNZ_OK ||
        !info.uncompressed_size || info.uncompressed_size > limit || unzOpenCurrentFile(zip) != UNZ_OK) return {};
    std::vector<unsigned char> bytes(info.uncompressed_size);
    size_t offset = 0;
    while (offset < bytes.size()) {
        const int got = unzReadCurrentFile(zip, bytes.data()+offset, unsigned(bytes.size()-offset));
        if (got <= 0) break;
        offset += got;
    }
    if (unzCloseCurrentFile(zip) != UNZ_OK || offset != bytes.size()) return {};
    return bytes;
}

static void FS_EmoteFolder(const char* root, uint32_t skeleton) {
    char directory[MAX_OSPATH];
    Q_strncpyz(directory, FS_BuildOSPath(root, "SaberTrials", "dlc/emotes"), sizeof(directory));
    int count = 0;
    char** files = Sys_ListFiles(directory, ".pk3", nullptr, &count, qfalse);
    std::vector<std::string> names;
    for (int i = 0; i < count; ++i) {
        const std::string name = files[i];
        if (name.size() <= 64 && name.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.") == std::string::npos &&
            name.find("..") == std::string::npos) names.push_back(name);
    }
    if (files) Sys_FreeFileList(files);
    std::sort(names.begin(), names.end());
    const auto stock = stemote::builtins();
    for (const auto& name : names) {
        if (stEmotePacks.size() == stemote::maxDlc) break;
        unzFile zip = unzOpen(FS_BuildOSPath(root, "SaberTrials", ("dlc/emotes/" + name).c_str()));
        auto manifest = FS_EmoteEntry(zip,"emote.txt",256);
        auto poses = FS_EmoteEntry(zip,"poses.bin",240*53*14);
        if (zip) unzClose(zip);
        std::istringstream row(std::string(manifest.begin(), manifest.end()));
        EmoteData data;
        auto& clip = data.clip;
        std::string format;
        uint32_t bind = 0;
        row >> format >> clip.id >> clip.frames >> clip.fps >> std::hex >> bind;
        if (!row || row.get() != '\t') continue;
        std::getline(row, clip.label);
        if (format != "STEMOTE1" || !stemote::idValid(clip.id) || !stemote::labelValid(clip.label) ||
            bind != skeleton || clip.frames < 2 || clip.frames > 240 || clip.fps < 10 || clip.fps > 60 ||
            poses.size() != size_t(clip.frames)*53*14 || stemote::find(stock,clip.id) ||
            std::any_of(stEmotePacks.begin(), stEmotePacks.end(), [&](const EmoteData& other) { return other.clip.id == clip.id; })) continue;
        clip.signature = uint32_t(crc32(crc32(0, reinterpret_cast<const Bytef*>(clip.id.data()), unsigned(clip.id.size())),
            poses.data(), unsigned(poses.size()))) ^ skeleton ^ uint32_t(clip.fps);
        if (!clip.signature) clip.signature = 1;
        data.poses = std::move(poses);
        stEmotePacks.push_back(std::move(data));
    }
}

static void FS_LoadEmotes() {
    stEmotePacks.clear();
    stEmoteGla.clear();
    for (int i = 0; i < stemote::maxDlc; ++i) {
        const char* name = va("st_emoteClip%d", i);
        Cvar_Get(name, "", CVAR_ROM | CVAR_NORESTART);
        Cvar_Set(name, "");
    }
    if (Q_stricmp(fs_gamedirvar->string,"SaberTrials")) return;
    void* buffer = nullptr;
    const long bytes = FS_ReadFile(canonicalEmoteGla, &buffer);
    st_gla_compat::Gla base;
    if (!buffer) return;
    if (!base.load(buffer, bytes > 0 ? size_t(bytes) : 0) || base.bones != 53 || base.frames < 22443) {
        FS_FreeFile(buffer);
        return;
    }
    const uint32_t skeleton = uint32_t(crc32(0, base.data+100, unsigned(base.frameOffset-100)));
    FS_EmoteFolder(fs_homepath->string, skeleton);
    if (!Sys_PathCmp(fs_homepath->string,fs_basepath->string)) FS_EmoteFolder(fs_basepath->string, skeleton);
    std::sort(stEmotePacks.begin(),stEmotePacks.end(),[](const EmoteData& a,const EmoteData& b) {return a.clip.id < b.clip.id;});
    size_t extraPoses = 0;
    for (const auto& data : stEmotePacks) extraPoses += data.poses.size()/14;
    const size_t newPool = base.poolOffset+extraPoses*3;
    const size_t resultSize = base.size + extraPoses*17;
    if (extraPoses && resultSize <= st_gla_compat::maxBytes && base.poolCount+extraPoses <= 0xffffff) {
        stEmoteGla.resize(resultSize);
        std::memcpy(stEmoteGla.data(),base.data,base.poolOffset);
        std::memcpy(stEmoteGla.data()+newPool,base.data+base.poolOffset,base.size-base.poolOffset);
        size_t frame = base.frames, pool = base.poolCount, index = base.poolOffset;
        for (size_t i = 0; i < stEmotePacks.size(); ++i) {
            auto& data = stEmotePacks[i];
            auto& clip = data.clip;
            clip.first = int(frame);
            frame += clip.frames;
            std::memcpy(stEmoteGla.data()+newPool+pool*14,data.poses.data(),data.poses.size());
            for (size_t p = 0; p < data.poses.size()/14; ++p, index += 3)
                st_gla_compat::put24(stEmoteGla.data()+index,uint32_t(pool++));
            Cvar_Set(va("st_emoteClip%d",int(i)),va("%s %d %d %d %08x\t%s",clip.id.c_str(),clip.first,
                clip.frames,clip.fps,clip.signature,clip.label.c_str()));
        }
        st_gla_compat::put32(stEmoteGla.data()+76,uint32_t(frame));
        st_gla_compat::put32(stEmoteGla.data()+88,uint32_t(newPool));
        st_gla_compat::put32(stEmoteGla.data()+96,uint32_t(resultSize));
        Com_Printf("Saber Trials emotes: loaded %d DLC clips.\n",int(stEmotePacks.size()));
    }
    FS_FreeFile(buffer);
}
}

static long FS_ReadEmoteGla(const char* path, void** buffer) {
    if (stEmoteGla.empty() || Q_stricmp(path,canonicalEmoteGla) || fs_numServerPaks) return -1;
    if (buffer) {
        *buffer = Z_Malloc(stEmoteGla.size()+1,TAG_FILESYS,qfalse);
        std::memcpy(*buffer,stEmoteGla.data(),stEmoteGla.size());
        static_cast<unsigned char*>(*buffer)[stEmoteGla.size()] = 0;
        ++fs_loadCount;
    }
    return long(stEmoteGla.size());
}
