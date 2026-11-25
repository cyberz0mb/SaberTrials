// Scene-submission checks only. This does not launch the game or validate pixels.
#include "../../dist/black-sabers-01/frontend/codemp/rd-common/tr_types.h"
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>
#include <vector>

static void require(bool value, const char* message) {
    if (!value) { std::fprintf(stderr, "%s\n", message); std::exit(1); }
}
static unsigned randomSeed;
float DotProduct(const vec3_t a,const vec3_t b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
void VectorCopy(const vec3_t a,vec3_t out) { for (int i=0;i<3;++i) out[i]=a[i]; }
void VectorScale(const vec3_t a,float scale,vec3_t out) { for (int i=0;i<3;++i) out[i]=a[i]*scale; }
void VectorMA(const vec3_t a,float scale,const vec3_t b,vec3_t out) { for (int i=0;i<3;++i) out[i]=a[i]+scale*b[i]; }
float Q_flrand(float lo, float hi) {
    randomSeed = randomSeed * 1664525u + 1013904223u;
    return lo + (hi-lo) * float(randomSeed & 65535u) / 65535.f;
}
float VectorNormalize(vec3_t v) {
    const float len = std::sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);
    if (len) for (int i=0;i<3;++i) v[i] /= len;
    return len;
}
void CrossProduct(const vec3_t a, const vec3_t b, vec3_t out) {
    out[0]=a[1]*b[2]-a[2]*b[1]; out[1]=a[2]*b[0]-a[0]*b[2]; out[2]=a[0]*b[1]-a[1]*b[0];
}
void PerpendicularVector(vec3_t out, const vec3_t v) {
    int axis=0;
    for (int i=1;i<3;++i) if (std::fabs(v[i]) < std::fabs(v[axis])) axis=i;
    for (int i=0;i<3;++i) out[i]=(i==axis ? 1.f : 0.f)-v[axis]*v[i];
    VectorNormalize(out);
}
static int ST_CrystalChannel(int rgb, int channel) { return (rgb >> ((2-channel)*8)) & 255; }

struct Scene {
    std::vector<refEntity_t> entities;
    std::vector<std::array<float,7>> lights;
};
static Scene scene;
static std::map<std::string,int> resources;
static bool missingModel=false;
struct MockRenderer {
    qhandle_t R_RegisterShaderNoMip(const char* name) {
        auto found=resources.find(name);
        if (found!=resources.end()) return found->second;
        return resources[name]=int(resources.size())+1;
    }
    qhandle_t R_RegisterModel(const char* name) { return missingModel ? 0 : R_RegisterShaderNoMip(name); }
    void R_AddRefEntityToScene(const refEntity_t* entity) { scene.entities.push_back(*entity); }
    void R_AddLightToScene(const vec3_t pos, float r, float red, float green, float blue) {
        scene.lights.push_back({pos[0],pos[1],pos[2],r,red,green,blue});
    }
} renderer;
static MockRenderer* trap=&renderer;

namespace previous {
#include "../../dist/profile-uniform-fix/frontend/codemp/cgame/st_crystal_blade.inc"
}
namespace updated {
#include "../../development-source/saber-crystals/st_crystal_blade.inc"
}

static bool close(float a,float b) { return std::fabs(a-b)<.0001f; }
int main() {
    const vec3_t origin={10,20,30}, direction={.6f,.8f,0};
    // Reproduce the legacy fault: White Core off still submits the baked-rim strip.
    scene={}; randomSeed=7;
    require(previous::ST_DrawCrystalBlade(origin,direction,40,40,3,0,0,qtrue,qfalse),"Legacy draw failed");
    require(scene.entities.size()==1 && scene.entities[0].reType==RT_LINE &&
        scene.entities[0].customShader==resources.at("gfx/st_crystals/blackCore"),"Legacy fault not reproduced");

    for (int core=0;core<2;++core) {
        scene={}; randomSeed=7;
        const int flags=RF_FORCEPOST|RF_THIRD_PERSON|RF_DEPTHHACK;
        require(updated::ST_DrawCrystalBlade(origin,direction,40,40,3,0,flags,qtrue,core?qtrue:qfalse),"Black draw failed");
        require(scene.entities.size()==(core?3:1) && scene.lights.empty(),"Black edge toggle or lighting failed");
        const auto& body=scene.entities[0];
        require(body.reType==RT_MODEL && body.hModel && body.nonNormalizedAxes &&
            body.customShader==resources.at("gfx/st_crystals/blackVolume"),"Opaque black volume missing");
        require(body.renderfx==((flags & ~RF_FORCEPOST)|RF_NOSHADOW),"Black depth/camera flags failed");
        require(close(std::sqrt(DotProduct(body.axis[0],body.axis[0])),.96f),"Black radius changed");
        for (int i=0;i<3;++i)
            require(close(body.origin[i]+40*body.axis[2][i],origin[i]+40*direction[i]),"Black blade tip length failed");
        for (size_t i=1;i<scene.entities.size();++i)
            require(scene.entities[i].customShader==resources.at("gfx/st_crystals/blackEdge") &&
                scene.entities[i].shaderRGBA[3]>0,"Conditional edge missing");
    }
    // Replay identical inputs and jitter through both versions. Colored blades
    // must submit byte-identical scene entities and light values, including dark RGB.
    int comparisons=0;
    for (int rgb : {0xFF0000,0x00FF00,0x0000FF,0xFF7A17,0xAA33FF,0xFFFFFF,0x010101})
        for (int core=0;core<2;++core) for (float length : {1.f,19.f,40.f}) {
            scene={}; randomSeed=42;
            require(previous::ST_DrawCrystalBlade(origin,direction,length,40,3,rgb,RF_THIRD_PERSON,qtrue,core?qtrue:qfalse),"Legacy color failed");
            const Scene expected=scene;
            scene={}; randomSeed=42;
            require(updated::ST_DrawCrystalBlade(origin,direction,length,40,3,rgb,RF_THIRD_PERSON,qtrue,core?qtrue:qfalse),"Updated color failed");
            require(scene.entities.size()==expected.entities.size() && scene.lights==expected.lights,"Colored glow/light changed");
            for (size_t i=0;i<scene.entities.size();++i)
                require(!std::memcmp(&scene.entities[i],&expected.entities[i],sizeof(refEntity_t)),"Colored entity changed");
            ++comparisons;
        }
    scene={}; missingModel=true;
    require(!updated::ST_DrawCrystalBlade(origin,direction,40,40,3,0,0,qtrue,qfalse) && scene.entities.empty(),"Missing-asset fallback failed");
    std::printf("PASS: legacy border reproduced; black toggle, depth, size, tip and fallback checked; %d colored replays identical. No game launched.\n",comparisons);
}
