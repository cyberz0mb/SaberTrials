// Frame storage with stable addresses, bounded growth and reusable pages.
// Unlike the legacy ring, allocation never overwrites a queued surface.
#pragma once
#include <array>
#include <memory>
#include <cstddef>
namespace st_models {
template<class T, size_t PageSize, size_t MaxPages> class SurfacePool {
    std::array<std::unique_ptr<T[]>,MaxPages> pages;
    size_t used=0;
public:
    T* allocate() {
        if(used>=PageSize*MaxPages) return nullptr;
        const size_t page=used/PageSize, slot=used%PageSize;
        if(!pages[page]) pages[page].reset(new T[PageSize]);
        ++used;
        return &pages[page][slot];
    }
    // Call only after all queued draws referencing this frame have finished.
    void reset() { used=0; }
    size_t size() const { return used; }
};
}
