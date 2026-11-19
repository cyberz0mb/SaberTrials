#pragma once

// Read a renderer-owned world or sub-BSP without allocating arbitrary disk sizes.
// The vanilla renderer can instead reuse the already-validated collision cache.
static byte *ST_ReadBSP(const char *name, int &version) {
    fileHandle_t file;
    const long length = ri.FS_FOpenFileRead(name, &file, qfalse);
    if (!file)
        return nullptr;
    if (length < long(sizeof(dheader_t)) || length > st_bsp::maxFileBytes) {
        ri.FS_FCloseFile(file);
        ri.Error(ERR_DROP, "%s: invalid BSP file length", name);
        return nullptr;
    }
    auto *buffer = static_cast<byte *>(ri.Hunk_AllocateTempMemory(static_cast<int>(length)));
    const int bytes = ri.FS_Read(buffer, static_cast<int>(length), file);
    ri.FS_FCloseFile(file);
    const char *error = bytes == length ? st_bsp::Validate(buffer, bytes, version) : "short BSP read";
    if (error) {
        ri.Hunk_FreeTempMemory(buffer);
        ri.Error(ERR_DROP, "%s: %s", name, error);
        return nullptr;
    }
    return buffer;
}
