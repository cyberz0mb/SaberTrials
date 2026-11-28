// Console commands retain their byte limit. Cursor positions point to UTF-8 boundaries.
static void ST_ConsoleScroll(field_t *field) {
    if (field->cursor < field->scroll) field->scroll = field->cursor;
    if (field->cursor >= field->scroll + field->widthInChars)
        field->scroll = std::max(0, field->cursor - field->widthInChars + 1);
    while (field->scroll > 0 && ((unsigned char)field->buffer[field->scroll] & 0xc0) == 0x80)
        --field->scroll;
}

static void ST_ConsoleChar(field_t *field, unsigned cp) {
    if (cp < 32 || (cp >= 127 && cp < 160)) return;
    char encoded[4];
    const int bytes = ST_UTF8Write(cp, encoded);
    int size = (int)strlen(field->buffer), replace = 0;
    if (kg.key_overstrikeMode && field->cursor < size)
        ST_UTF8Read(field->buffer + field->cursor, &replace);
    if (!bytes || size - replace + bytes > MAX_EDIT_LINE - 2) return;
    char *at = field->buffer + field->cursor;
    memmove(at + bytes, at + replace, size - field->cursor - replace + 1);
    memcpy(at, encoded, bytes);
    field->cursor += bytes;
    ST_ConsoleScroll(field);
}

static void ST_ConsoleMove(field_t *field, bool left, bool erase) {
    int old = field->cursor, next = old;
    if (left) next = ST_UTF8Previous(field->buffer, old);
    else if (field->buffer[old]) {
        int bytes;
        ST_UTF8Read(field->buffer + old, &bytes);
        next += bytes;
    }
    if (erase) {
        int start = std::min(old, next), end = std::max(old, next);
        memmove(field->buffer + start, field->buffer + end, strlen(field->buffer + end) + 1);
        next = start;
    }
    field->cursor = next;
    ST_ConsoleScroll(field);
}
