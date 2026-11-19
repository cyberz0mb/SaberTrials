// Initialization errors remain inside this DLL; no C++ exception crosses the ABI.
struct STVulkanInitError { char message[MAXPRINTMSG]; };
static bool stVulkanInitializing = false;
static void (QDECL *stEngineError)(int, const char *, ...);

static void QDECL STVulkan_Error(int level, const char *format, ...) {
    STVulkanInitError error;
    va_list args;
    va_start(args, format);
    Q_vsnprintf(error.message, sizeof(error.message), format, args);
    va_end(args);
    if (stVulkanInitializing) throw error;
    stEngineError(level, "%s", error.message);
}

extern "C" Q_EXPORT qboolean QDECL STVulkan_TryBeginRegistration(glconfig_t *config, char *error, int size) {
    stVulkanInitializing = true;
    try {
        RE_BeginRegistration(config);
        stVulkanInitializing = false;
        return qtrue;
    } catch (const STVulkanInitError &failure) {
        Q_strncpyz(error, failure.message, size);
        // Shutdown is also protected: report the original failure to the engine.
        // All handles are zero-initialized, and vk_shutdown handles partial startup.
        try { RE_Shutdown(qtrue, qfalse); } catch (const STVulkanInitError &) {}
        stVulkanInitializing = false;
        return qfalse;
    }
}
