/* Persistent outgoing chat color. GPL-2.0; see LICENSE.txt. */
#ifndef CL_ST_CHAT_COLOR_H
#define CL_ST_CHAT_COLOR_H
#include "qcommon/st_utf8.h"
#include <string>

static inline int ST_ChatTextColor() {
    const int color = Cvar_Get("st_chatColor", "-1", CVAR_ARCHIVE)->integer;
    return color >= 0 && color <= 9 ? color : -1;
}

static inline int ST_ChatTextLimit() {
    return MAX_SAY_TEXT - 1 - (ST_ChatTextColor() >= 0 ? 2 : 0);
}

static inline std::string ST_ChatColorPrefix() {
    const int color = ST_ChatTextColor();
    return color < 0 ? std::string() : std::string("^") + char('0'+color);
}

static inline std::string ST_ChatColorized(const char* text) {
    const int color = ST_ChatTextColor();
    if (color < 0) return text;
    std::string result = std::string("^") + char('0'+color);
    /* A preference changed while editing must not cut a UTF-8 character or
     * leave a dangling color escape at the network message-length boundary. */
    for (const char* p = text; *p;) {
        int bytes;
        if (Q_IsColorString(p)) bytes = 2;
        else ST_UTF8Read(p, &bytes);
        if (bytes < 1 || result.size()+bytes >= MAX_SAY_TEXT) break;
        result.append(p, bytes);
        p += bytes;
    }
    return result;
}
#endif
