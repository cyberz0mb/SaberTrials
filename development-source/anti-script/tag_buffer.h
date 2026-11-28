#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace antiscript {
// Mirror command-buffer byte positions. Popping and prepending rotate the
// head, so a one-line command never shifts the remainder of the metadata.
template<std::size_t Capacity> class TagBuffer {
    std::array<uint32_t,Capacity> tags_{};
    size_t head_ = 0;
public:
    void reset() { tags_.fill(0); head_ = 0; }
    void append(size_t offset,size_t length,uint32_t tag) {
        for (size_t i = 0; i < length; ++i) tags_[(head_+offset+i)%Capacity] = tag;
    }
    void prepend(size_t length,uint32_t tag) {
        head_ = (head_+Capacity-length)%Capacity;
        append(0,length,tag);
    }
    uint32_t take(size_t bytes,size_t consumed) {
        uint32_t tag = tags_[head_];
        for (size_t i = 1; tag && i < bytes; ++i)
            if (tags_[(head_+i)%Capacity] != tag) tag = 0;
        head_ = (head_+consumed)%Capacity;
        return tag;
    }
};
}
