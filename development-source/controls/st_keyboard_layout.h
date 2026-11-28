#ifndef ST_KEYBOARD_LAYOUT_H
#define ST_KEYBOARD_LAYOUT_H

// Saved keyboard preferences use the same stable IDs as menu and chat languages.
namespace stkeys {
constexpr int columns = 11, rows = 4, count = columns * rows;
struct Layout {
    int id;
    const char *name;
    const char32_t *lower[rows], *upper[rows];
};
static constexpr Layout layouts[] = {
    {1, "English",
     {U"1234567890-", U"qwertyuiop[", U"asdfghjkl;'", U"zxcvbnm,./?"},
     {U"1234567890-", U"QWERTYUIOP[", U"ASDFGHJKL;'", U"ZXCVBNM,./?"}},
    {15, "Polski",
     {U"\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c-!", U"qwertyuiop[", U"asdfghjkl;'", U"zxcvbnm,./?"},
     {U"\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b-!", U"QWERTYUIOP[", U"ASDFGHJKL;'", U"ZXCVBNM,./?"}},
    {18, "Nederlands",
     {U"\u00e9\u00eb\u00ef\u00f6\u00fc\u00e4\u00e1\u00ed\u00f3\u00fa\u00e8", U"qwertyuiop\u00ea", U"asdfghjkl\u00e0\u00e7", U"zxcvbnm,.!?"},
     {U"\u00c9\u00cb\u00cf\u00d6\u00dc\u00c4\u00c1\u00cd\u00d3\u00da\u00c8", U"QWERTYUIOP\u00ca", U"ASDFGHJKL\u00c0\u00c7", U"ZXCVBNM,.!?"}},
    {19, "Svenska",
     {U"1234567890+", U"qwertyuiop\u00e5", U"asdfghjkl\u00f6\u00e4", U"zxcvbnm,.\u00e9-"},
     {U"1234567890+", U"QWERTYUIOP\u00c5", U"ASDFGHJKL\u00d6\u00c4", U"ZXCVBNM,.\u00c9-"}},
    {20, "Suomi",
     {U"1234567890+", U"qwertyuiop\u00e5", U"asdfghjkl\u00f6\u00e4", U"zxcvbnm,.\u0161\u017e"},
     {U"1234567890+", U"QWERTYUIOP\u00c5", U"ASDFGHJKL\u00d6\u00c4", U"ZXCVBNM,.\u0160\u017d"}}
};
static constexpr const char32_t *symbols[] = {
    U"1234567890!", U"@#$%^&*()_+", U"-=[]{}<>/\\|", U"`~:;\"'?,. *"
};
inline int index(int preference, int menuLanguage) {
    const int id = preference ? preference : menuLanguage;
    for (int i = 0; i < int(sizeof(layouts) / sizeof(layouts[0])); ++i)
        if (layouts[i].id == id) return i;
    return 0;
}
inline int next(int preference) {
    if (!preference) return layouts[0].id;
    const int nextIndex = index(preference, 1) + 1;
    return nextIndex < int(sizeof(layouts) / sizeof(layouts[0])) ? layouts[nextIndex].id : 0;
}
inline int character(int layout, int slot, bool shift, bool punctuation) {
    const int row = slot / columns, col = slot % columns;
    return (punctuation ? symbols[row] : shift ? layouts[layout].upper[row] : layouts[layout].lower[row])[col];
}
}
#endif
