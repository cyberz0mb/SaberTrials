#ifndef ST_COMBAT_WIRE_H
#define ST_COMBAT_WIRE_H
#include "st_combat_core.h"
#include <stddef.h>
#define STC_WIRE_SIZE 72u
/* Versioned development snapshot format; not an authentication mechanism and
 * not yet connected to JKA's delta-playerstate protocol. All fields are explicit
 * little-endian uint32s, independent of compiler struct padding. Decode rejects
 * malformed states and never partially overwrites the destination. */
int STC_StateValid(const STC_State* state);
int STC_Encode(const STC_State* state, unsigned char* bytes, size_t size);
int STC_Decode(STC_State* state, const unsigned char* bytes, size_t size);
#endif
