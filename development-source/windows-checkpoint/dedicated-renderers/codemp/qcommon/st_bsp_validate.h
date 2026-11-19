// Shared multiplayer RBSP preflight. Validate before the loaders follow disk offsets.
#pragma once

#include "qfiles.h"
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

#define ST_BSP_VERSION 2
#define ST_BSP_CAPABILITY_KEY "stmap"
#define ST_BSP_CAPABILITY "2"
#define ST_BSP_REQUIREMENT "This map requires a Saber Trials client with Enhanced Map Support (RBSP 2)."

namespace st_bsp {
constexpr int maxFileBytes = 256 * 1024 * 1024;
constexpr int classicCoord = 65536;
constexpr int enhancedCoord = 131072;
constexpr int maxLightGridPoints = 1 << 20;
constexpr int maxClusters = 1 << 14;
constexpr int lightmapBytes = LIGHTMAP_WIDTH * LIGHTMAP_HEIGHT * 3;
constexpr int maxLightmaps = 256;

static_assert(sizeof(dheader_t) == 152 && sizeof(dsurface_t) == 148 &&
              sizeof(drawVert_t) == 80 && sizeof(dgrid_t) == 30, "Unexpected RBSP layout");

struct LumpRule { int stride, limit; };
constexpr LumpRule rules[HEADER_LUMPS] = {
    {1, 512 * 1024}, {sizeof(dshader_t), 4096}, {sizeof(dplane_t), 524288},
    {sizeof(dnode_t), 262144}, {sizeof(dleaf_t), 262144}, {4, 1048576}, {4, 1048576},
    {sizeof(dmodel_t), 510}, {sizeof(dbrush_t), 131072}, {sizeof(dbrushside_t), 1048576},
    {sizeof(drawVert_t), 2097152}, {4, 6291456}, {sizeof(dfog_t), 30},
    {sizeof(dsurface_t), 262144}, {lightmapBytes, maxLightmaps}, {sizeof(dgrid_t), 65536},
    {1, 8 + maxClusters * (maxClusters / 8)}, {2, maxLightGridPoints}
};

inline bool Index(int i, int count) { return i >= 0 && i < count; }
inline bool Span(int first, int count, int total) {
    return first >= 0 && count >= 0 && first <= total && count <= total - first;
}
inline bool Bounded(float x, float limit) { return std::isfinite(x) && std::fabs(x) <= limit; }
inline bool Style(byte style) { return style < MAX_LIGHT_STYLES || style >= LS_UNUSED; }

template<typename T>
T Record(const byte *data, int i) {
    T out;
    std::memcpy(&out, data + sizeof(T) * i, sizeof(T));
    return out;
}

inline const char *Validate(const void *buffer, int length, int &version) {
    if (!buffer || length < int(sizeof(dheader_t)) || length > maxFileBytes)
        return "invalid BSP file length";
    const auto *base = static_cast<const byte *>(buffer);
    const auto header = Record<dheader_t>(base, 0);
    if (LittleLong(header.ident) != BSP_IDENT)
        return "invalid RBSP signature";
    version = LittleLong(header.version);
    if (version != BSP_VERSION && version != ST_BSP_VERSION)
        return "unsupported RBSP version (expected classic 1 or Saber Trials 2)";
    const float coord = version == ST_BSP_VERSION ? enhancedCoord : classicCoord;
    const byte *data[HEADER_LUMPS];
    int count[HEADER_LUMPS];
    int offsets[HEADER_LUMPS], sizes[HEADER_LUMPS];
    for (int i = 0; i < HEADER_LUMPS; ++i) {
        const int offset = LittleLong(header.lumps[i].fileofs);
        const int size = LittleLong(header.lumps[i].filelen);
        const auto rule = rules[i];
        if (!Span(offset, size, length) || size % rule.stride ||
            (size && (offset < int(sizeof(dheader_t)) || offset % 4)))
            return "invalid BSP lump offset, length or record alignment";
        count[i] = size / rule.stride;
        if (count[i] > rule.limit)
            return "BSP lump exceeds the supported capacity";
        for (int j = 0; size && j < i; ++j) {
            if (sizes[j] && offset < offsets[j] + sizes[j] && offsets[j] < offset + size)
                return "overlapping BSP lumps";
        }
        offsets[i] = offset;
        sizes[i] = size;
        data[i] = base + offset;
    }

    if (!count[LUMP_ENTITIES] || data[LUMP_ENTITIES][count[LUMP_ENTITIES] - 1] != 0 ||
        !count[LUMP_MODELS] || !count[LUMP_NODES] || !count[LUMP_LEAFS] ||
        !count[LUMP_PLANES] || !count[LUMP_SHADERS])
        return "missing required BSP data or unterminated entity text";

    for (int i = 0; i < count[LUMP_SHADERS]; ++i) {
        const auto shader = Record<dshader_t>(data[LUMP_SHADERS], i);
        if (!std::memchr(shader.shader, 0, sizeof(shader.shader)))
            return "unterminated BSP shader name";
    }
    for (int i = 0; i < count[LUMP_PLANES]; ++i) {
        const auto plane = Record<dplane_t>(data[LUMP_PLANES], i);
        if (!Bounded(LittleFloat(plane.dist), 4 * coord))
            return "invalid BSP plane distance";
        for (float normal : plane.normal) {
            if (!Bounded(LittleFloat(normal), 1.01f))
                return "invalid BSP plane normal";
        }
    }
    int modelBrushes = 0, modelSurfaces = 0;
    for (int i = 0; i < count[LUMP_MODELS]; ++i) {
        const auto model = Record<dmodel_t>(data[LUMP_MODELS], i);
        const int brushes = LittleLong(model.numBrushes), surfaces = LittleLong(model.numSurfaces);
        if (!Span(LittleLong(model.firstBrush), brushes, count[LUMP_BRUSHES]) ||
            !Span(LittleLong(model.firstSurface), surfaces, count[LUMP_SURFACES]) ||
            !Span(modelBrushes, brushes, count[LUMP_BRUSHES]) ||
            !Span(modelSurfaces, surfaces, count[LUMP_SURFACES]))
            return "invalid BSP model geometry range";
        modelBrushes += brushes;
        modelSurfaces += surfaces;
        for (int axis = 0; axis < 3; ++axis) {
            const float lo = LittleFloat(model.mins[axis]), hi = LittleFloat(model.maxs[axis]);
            if (!Bounded(lo, coord) || !Bounded(hi, coord) || lo > hi)
                return "BSP model bounds exceed the map format's coordinate range";
        }
    }
    for (int i = 0; i < count[LUMP_BRUSHSIDES]; ++i) {
        const auto side = Record<dbrushside_t>(data[LUMP_BRUSHSIDES], i);
        if (!Index(LittleLong(side.planeNum), count[LUMP_PLANES]) ||
            !Index(LittleLong(side.shaderNum), count[LUMP_SHADERS]))
            return "invalid BSP brush side reference";
    }
    for (int i = 0; i < count[LUMP_BRUSHES]; ++i) {
        const auto brush = Record<dbrush_t>(data[LUMP_BRUSHES], i);
        const int first = LittleLong(brush.firstSide), sides = LittleLong(brush.numSides);
        if (sides < 6 || sides > 1024 || !Span(first, sides, count[LUMP_BRUSHSIDES]) ||
            !Index(LittleLong(brush.shaderNum), count[LUMP_SHADERS]))
            return "invalid BSP brush geometry range";
    }
    for (int i = 0; i < count[LUMP_FOGS]; ++i) {
        const auto fog = Record<dfog_t>(data[LUMP_FOGS], i);
        const int brush = LittleLong(fog.brushNum), side = LittleLong(fog.visibleSide);
        if (!std::memchr(fog.shader, 0, sizeof(fog.shader)) ||
            (brush != -1 && !Index(brush, count[LUMP_BRUSHES])) ||
            (side != -1 && (brush == -1 ||
                !Index(side, LittleLong(Record<dbrush_t>(data[LUMP_BRUSHES], brush).numSides)))))
            return "invalid BSP fog reference";
    }

    int clusters = maxClusters;
    if (count[LUMP_VISIBILITY]) {
        if (count[LUMP_VISIBILITY] < 8)
            return "truncated BSP visibility header";
        clusters = LittleLong(Record<int>(data[LUMP_VISIBILITY], 0));
        const int row = LittleLong(Record<int>(data[LUMP_VISIBILITY], 1));
        if (clusters < 1 || clusters > maxClusters || row < (clusters + 7) / 8 ||
            int64_t(clusters) * row != count[LUMP_VISIBILITY] - 8)
            return "invalid BSP visibility dimensions";
    }
    for (int i = 0; i < count[LUMP_LEAFS]; ++i) {
        const auto leaf = Record<dleaf_t>(data[LUMP_LEAFS], i);
        const int cluster = LittleLong(leaf.cluster), area = LittleLong(leaf.area);
        if (cluster < -1 || cluster >= clusters || area < -1 || area >= MAX_MAP_AREAS ||
            !Span(LittleLong(leaf.firstLeafSurface), LittleLong(leaf.numLeafSurfaces), count[LUMP_LEAFSURFACES]) ||
            !Span(LittleLong(leaf.firstLeafBrush), LittleLong(leaf.numLeafBrushes), count[LUMP_LEAFBRUSHES]))
            return "invalid BSP leaf references";
    }
    for (int i = 0; i < count[LUMP_LEAFBRUSHES]; ++i) {
        if (!Index(LittleLong(Record<int>(data[LUMP_LEAFBRUSHES], i)), count[LUMP_BRUSHES]))
            return "invalid BSP leaf brush reference";
    }
    for (int i = 0; i < count[LUMP_LEAFSURFACES]; ++i) {
        if (!Index(LittleLong(Record<int>(data[LUMP_LEAFSURFACES], i)), count[LUMP_SURFACES]))
            return "invalid BSP leaf surface reference";
    }

    // Renderers and collision traverse this tree recursively. Check depth and
    // reject cycles or shared internal nodes before handing it to either loader.
    std::vector<byte> seen(count[LUMP_NODES]);
    struct Visit { int node, depth; };
    std::vector<Visit> stack;
    for (int root = 0; root < count[LUMP_NODES]; ++root) {
        if (seen[root])
            continue;
        stack.push_back({root, 0});
        while (!stack.empty()) {
            const auto visit = stack.back();
            stack.pop_back();
            if (seen[visit.node] || visit.depth > 128)
                return "cyclic, shared or excessively deep BSP node tree";
            seen[visit.node] = 1;
            const auto node = Record<dnode_t>(data[LUMP_NODES], visit.node);
            if (!Index(LittleLong(node.planeNum), count[LUMP_PLANES]))
                return "invalid BSP node plane";
            for (int raw : node.children) {
                const int child = LittleLong(raw);
                if (child < 0) {
                    if (!Index(-(child + 1), count[LUMP_LEAFS]))
                        return "invalid BSP node leaf";
                } else if (Index(child, count[LUMP_NODES])) {
                    stack.push_back({child, visit.depth + 1});
                } else {
                    return "invalid BSP child node";
                }
            }
        }
    }

    for (int i = 0; i < count[LUMP_DRAWVERTS]; ++i) {
        const auto vert = Record<drawVert_t>(data[LUMP_DRAWVERTS], i);
        for (float value : vert.xyz) {
            if (!Bounded(LittleFloat(value), coord))
                return "BSP draw vertex exceeds the map format's coordinate range";
        }
        for (float value : vert.normal) {
            if (!Bounded(LittleFloat(value), 1.01f))
                return "invalid BSP vertex normal";
        }
        for (float value : vert.st) {
            if (!std::isfinite(LittleFloat(value)))
                return "invalid BSP texture coordinates";
        }
        // Stock BSPs contain uninitialized coordinates for unused light styles.
        if (version == ST_BSP_VERSION) {
            for (const auto &style : vert.lightmap) {
                for (float value : style) {
                    if (!std::isfinite(LittleFloat(value)))
                        return "invalid BSP lightmap coordinates";
                }
            }
        }
    }
    // A small file can share the same ranges across many surfaces. Budget the
    // expanded references too, because the renderers copy those per surface.
    int referencedVerts = 0, referencedIndices = 0, patches = 0;
    for (int i = 0; i < count[LUMP_SURFACES]; ++i) {
        const auto surf = Record<dsurface_t>(data[LUMP_SURFACES], i);
        const int type = LittleLong(surf.surfaceType), fog = LittleLong(surf.fogNum);
        const int firstVert = LittleLong(surf.firstVert), verts = LittleLong(surf.numVerts);
        const int firstIndex = LittleLong(surf.firstIndex), indices = LittleLong(surf.numIndexes);
        if (type < MST_PLANAR || type > MST_FLARE || fog < -1 || fog >= count[LUMP_FOGS] ||
            !Index(LittleLong(surf.shaderNum), count[LUMP_SHADERS]) ||
            !Span(firstVert, verts, count[LUMP_DRAWVERTS]) ||
            !Span(firstIndex, indices, count[LUMP_DRAWINDEXES]))
            return "invalid BSP surface geometry range";
        if (!Span(referencedVerts, verts, rules[LUMP_DRAWVERTS].limit) ||
            !Span(referencedIndices, indices, rules[LUMP_DRAWINDEXES].limit))
            return "BSP surface references exceed the supported capacity";
        referencedVerts += verts;
        referencedIndices += indices;
        if ((type == MST_PLANAR || type == MST_TRIANGLE_SOUP) &&
            (verts < 3 || verts >= SHADER_MAX_VERTEXES || indices < 3 ||
             indices >= SHADER_MAX_INDEXES || indices % 3))
            return "BSP surface exceeds the renderer batch capacity";
        if (type == MST_PATCH) {
            if (++patches > 8192)
                return "BSP patch count exceeds the supported capacity";
            const int w = LittleLong(surf.patchWidth), h = LittleLong(surf.patchHeight);
            if (w < 3 || h < 3 || w > 31 || h > 31 || !(w & 1) || !(h & 1) || w * h != verts)
                return "invalid BSP patch dimensions";
            if (version == ST_BSP_VERSION) {
                const auto origin = Record<drawVert_t>(data[LUMP_DRAWVERTS], firstVert);
                for (int j = 1; j < verts; ++j) {
                    const auto v = Record<drawVert_t>(data[LUMP_DRAWVERTS], firstVert + j);
                    for (int axis = 0; axis < 3; ++axis) {
                        if (!Bounded(LittleFloat(v.xyz[axis]) - LittleFloat(origin.xyz[axis]), 16384))
                            return "enhanced BSP patch must be split into smaller patches";
                    }
                }
            }
        }
        for (int j = 0; j < MAXLIGHTMAPS; ++j) {
            const int lm = LittleLong(surf.lightmapNum[j]);
            if (lm < -4 || lm >= maxLightmaps ||
                !Style(surf.lightmapStyles[j]) || !Style(surf.vertexStyles[j]))
                return "invalid BSP surface lightmap or lighting style";
        }
        if (version == ST_BSP_VERSION || type == MST_FLARE) {
            for (float value : surf.lightmapOrigin) {
                if (!Bounded(LittleFloat(value), 4 * coord))
                    return "invalid BSP surface origin";
            }
        }
        for (const auto &vec : surf.lightmapVecs) {
            for (float value : vec) {
                if (!Bounded(LittleFloat(value), 4 * coord))
                    return "invalid BSP surface vector";
            }
        }
        if (type == MST_PLANAR || type == MST_TRIANGLE_SOUP) {
            for (int j = 0; j < indices; ++j) {
                if (!Index(LittleLong(Record<int>(data[LUMP_DRAWINDEXES], firstIndex + j)), verts))
                    return "invalid BSP surface vertex index";
            }
        }
    }
    for (int i = 0; i < count[LUMP_LIGHTGRID]; ++i) {
        const auto point = Record<dgrid_t>(data[LUMP_LIGHTGRID], i);
        for (byte style : point.styles) {
            if (style >= MAX_LIGHT_STYLES && style != LS_LSNONE)
                return "invalid BSP light grid style";
        }
    }
    for (int i = 0; i < count[LUMP_LIGHTARRAY]; ++i) {
        if (!Index(static_cast<unsigned short>(LittleShort(Record<short>(data[LUMP_LIGHTARRAY], i))),
                   count[LUMP_LIGHTGRID]))
            return "invalid BSP light grid index";
    }
    return nullptr;
}

// Gridsize is read from worldspawn by each renderer. Check before float-to-int
// conversion, multiplication or optional HDR grid allocation.
inline bool GridLayout(const float *mins, const float *maxs, const float *size,
                       float *origin, float *inverseSize, int *bounds) {
    int total = 1;
    for (int axis = 0; axis < 3; ++axis) {
        if (!Bounded(size[axis], 4 * enhancedCoord) || size[axis] < 1)
            return false;
        inverseSize[axis] = 1.0f / size[axis];
        origin[axis] = size[axis] * std::ceil(mins[axis] / size[axis]);
        const float max = size[axis] * std::floor(maxs[axis] / size[axis]);
        const float cells = (max - origin[axis]) / size[axis] + 1;
        if (!Bounded(cells, maxLightGridPoints) || cells < 0)
            return false;
        bounds[axis] = static_cast<int>(cells);
        if (bounds[axis] && total > maxLightGridPoints / bounds[axis])
            return false;
        total *= bounds[axis];
    }
    return true;
}
} // namespace st_bsp
