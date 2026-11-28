// OpenJK cgame API 2 reads the original playerState_t, without the ST tail.
// All later members of snapshot_t must therefore move, including vehicle state.
static qboolean CL_GetStockSnapshot(int number, snapshot_t *target) {
    static snapshot_t scratch;
    if (!CL_GetSnapshot(number, &scratch)) return qfalse;
    constexpr size_t prefix = offsetof(playerState_t, stCombat);
    constexpr size_t tail = sizeof(playerState_t) - prefix;
    static_assert(prefix % alignof(playerState_t) == 0, "stock playerState alignment");
    static_assert(offsetof(snapshot_t, vps) == offsetof(snapshot_t, ps) + sizeof(playerState_t), "player states must be adjacent");
    byte *out = reinterpret_cast<byte *>(target);
    memcpy(out, &scratch, offsetof(snapshot_t, ps) + prefix);
    memcpy(out + offsetof(snapshot_t, vps) - tail, &scratch.vps, prefix);
    memcpy(out + offsetof(snapshot_t, numEntities) - 2 * tail, &scratch.numEntities, sizeof(int));
    memcpy(out + offsetof(snapshot_t, entities) - 2 * tail, scratch.entities, scratch.numEntities * sizeof(entityState_t));
    memcpy(out + offsetof(snapshot_t, numServerCommands) - 2 * tail, &scratch.numServerCommands, sizeof(int));
    memcpy(out + offsetof(snapshot_t, serverCommandSequence) - 2 * tail, &scratch.serverCommandSequence, sizeof(int));
    return qtrue;
}
