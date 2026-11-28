// Included by the multiplayer client command buffer, after MAX_CMD_BUFFER.
#include "tag_buffer.h"
#include "client_trace.h"
static antiscript::TagBuffer<MAX_CMD_BUFFER> asTags;
static uint32_t asSerial, asExecuting, asAdding, asInserting;
uint32_t Cbuf_ASOrigin() {
    if (!CL_ASCollecting()) return 0;
    if (!++asSerial) ++asSerial;
    return asSerial;
}
void Cbuf_ASReset() {
    asTags.reset();
    asExecuting = asAdding = asInserting = 0;
}
void Cbuf_ASBound(const char* text,uint32_t origin) {
    asAdding = origin;
    Cbuf_AddText(text);
    asAdding = 0;
}
// Internal to cmd.cpp and defined below this include.
void Cbuf_InsertText(const char* text);
static void Cbuf_ASScript(const char* text) {
    asInserting = asExecuting ? asExecuting : Cbuf_ASOrigin();
    Cbuf_InsertText(text);
    asInserting = 0;
}
