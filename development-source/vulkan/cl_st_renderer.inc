// An optional renderer may fail without rewriting the user's selected renderer.
// The Vulkan-only import extension uses API 13. Existing OpenGL DLLs keep API 12.
#include <string>
#include <vector>
extern cvar_t *cvar_vars;

static std::string stActiveRenderer;
static std::string stForcedRenderer;
static bool ST_IsOpenGLRenderer(const char *name) {
    return !Q_stricmp(name, "rd-vanilla") || !Q_stricmp(name, "rd-rend2");
}
static const char *ST_FallbackRenderer() {
    const char *last = Cvar_VariableString("st_lastGoodRenderer");
    return ST_IsOpenGLRenderer(last) ? last : "rd-vanilla";
}
static void ST_RendererFailure(const char *reason) {
    Cvar_Set("st_rendererError", reason);
    Com_Printf("Saber Trials: %s; using %s for this session. Saved graphics settings retained.\n",
        reason, ST_FallbackRenderer());
}
static refexport_t *ST_LoadRenderer(refimport_t *imports) {
    const std::string requested = stForcedRenderer.empty() ? cl_renderer->string : stForcedRenderer;
    std::vector<std::string> candidates = {requested};
    if (requested != ST_FallbackRenderer()) candidates.push_back(ST_FallbackRenderer());
    if (requested != "rd-vanilla" && candidates.back() != "rd-vanilla") candidates.push_back("rd-vanilla");
    for (const auto &name : candidates) {
        char path[MAX_OSPATH];
        Com_sprintf(path, sizeof(path), "%s_" ARCH_STRING DLL_EXT, name.c_str());
        rendererLib = Sys_LoadDll(path, qfalse);
        if (rendererLib) {
            auto api = (GetRefAPI_t)Sys_LoadFunction(rendererLib, "GetRefAPI");
            // Do not call an unrelated upstream Vulkan binary with our extended ABI.
            const bool vulkan = name == "rd-vulkan";
            if (api && (!vulkan || Sys_LoadFunction(rendererLib, "STVulkan_TryBeginRegistration"))) {
                refexport_t *exports = api(vulkan ? 13 : REF_API_VERSION, imports);
                if (exports) {
                    stActiveRenderer = name;
                    Cvar_Set("st_activeRenderer", name.c_str());
                    return exports;
                }
            }
            Sys_UnloadDll(rendererLib);
            rendererLib = nullptr;
        }
        ST_RendererFailure(va("Could not load compatible renderer %s", name.c_str()));
    }
    return nullptr;
}

static void ST_BeginRenderer() {
    if (stActiveRenderer == "rd-vulkan") {
        struct Saved { std::string name, value, pending; bool latched; };
        std::vector<Saved> settings;
        for (cvar_t *v = cvar_vars; v; v = v->next)
            if (!Q_stricmpn(v->name, "r_", 2))
                settings.push_back({v->name, v->string, v->latchedString ? v->latchedString : "", v->latchedString != nullptr});
        typedef qboolean (QDECL *TryBegin)(glconfig_t *, char *, int);
        auto begin = (TryBegin)Sys_LoadFunction(rendererLib, "STVulkan_TryBeginRegistration");
        char error[MAXPRINTMSG] = "Vulkan initialization entry point unavailable";
        if (begin && begin(&cls.glconfig, error, sizeof(error))) return;
        // The DLL has released partial Vulkan resources. Do not shut it down twice.
        re = nullptr;
        Sys_UnloadDll(rendererLib);
        rendererLib = nullptr;
        WIN_Shutdown();
        for (const auto &saved : settings) {
            Cvar_Set(saved.name.c_str(), saved.value.c_str());
            if (saved.latched) Cvar_SetSafe(saved.name.c_str(), saved.pending.c_str());
        }
        memset(&cls.glconfig, 0, sizeof(cls.glconfig));
        ST_RendererFailure(error);
        stForcedRenderer = ST_FallbackRenderer();
        CL_InitRef();
        stForcedRenderer.clear();
    }
    re->BeginRegistration(&cls.glconfig);
    if (ST_IsOpenGLRenderer(stActiveRenderer.c_str()))
        Cvar_Set("st_lastGoodRenderer", stActiveRenderer.c_str());
}
