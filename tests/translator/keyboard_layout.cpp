#include <algorithm>
#include <cassert>
#include <cstring>
#include <string>
#include "../../development-source/controls/st_keyboard_layout.h"
#include "../../development-source/translator/st_utf8.h"

constexpr int MAX_EDIT_LINE = 32;
struct field_t {
    char buffer[MAX_EDIT_LINE] = {};
    int cursor = 0, scroll = 0, widthInChars = 12;
};
static struct { bool key_overstrikeMode = false; } kg;
#include "../../development-source/controls/cl_st_keyboard_edit.inc"

int main() {
    int preference = 0;
    for (const auto& layout : stkeys::layouts) {
        preference = stkeys::next(preference);
        assert(preference == layout.id);
        const int index = stkeys::index(0, layout.id);
        assert(index == stkeys::index(layout.id, 1));
        for (int pos = 0; pos < stkeys::count; ++pos) {
            for (bool shift : {false, true}) {
                const auto letter = stkeys::character(index, pos, shift, false);
                assert(letter && stkeys::character(index, pos, shift, true));
                field_t field;
                ST_ConsoleChar(&field, letter);
                int bytes;
                assert(ST_UTF8Read(field.buffer, &bytes) == unsigned(letter));
                assert(field.cursor == bytes);
                ST_ConsoleMove(&field, true, false);
                assert(field.cursor == 0);
                ST_ConsoleMove(&field, false, true);
                assert(field.buffer[0] == 0);
            }
        }
    }
    assert(stkeys::next(preference) == 0);
    const std::u32string accents[] = {U"ąćęłńóśźż", U"ëéï", U"åäö", U"åäöšž"};
    for (int i = 0; i < 4; ++i) {
        std::u32string available;
        for (int k = 0; k < stkeys::count; ++k)
            available += stkeys::character(i+1, k, false, false);
        for (auto ch : accents[i]) assert(available.find(ch) != std::u32string::npos);
    }
    field_t mixed;
    for (auto ch : std::u32string(U"Łëåä")) ST_ConsoleChar(&mixed, ch);
    assert(!std::strcmp(mixed.buffer, u8"Łëåä"));
    ST_ConsoleMove(&mixed, true, true);
    ST_ConsoleMove(&mixed, true, false);
    kg.key_overstrikeMode = true;
    ST_ConsoleChar(&mixed, U'Ż');
    assert(!std::strcmp(mixed.buffer, u8"ŁëŻ"));
    for (int i = 0; i < MAX_EDIT_LINE; ++i) ST_ConsoleChar(&mixed, U'ä');
    assert(ST_UTF8Valid(mixed.buffer) && mixed.cursor <= MAX_EDIT_LINE - 2);
}
