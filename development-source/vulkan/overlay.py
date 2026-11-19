"""Adapt the pinned OpenJK Vulkan proposal to Saber Trials' current client ABI."""
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent

def edit(path, before, after, count=1):
    text = path.read_text(encoding='utf-8')
    if text.count(before) != count:
        raise ValueError(f'{path.name}: expected {count} occurrences of {before[:90]!r}, found {text.count(before)}')
    path.write_text(text.replace(before, after), encoding='utf-8', newline='\n')

def apply(engine, frontend):
    mp = engine / 'codemp'
    rd = mp / 'rd-vulkan'
    subprocess.run(['git','apply','--unsafe-paths','--ignore-space-change','--directory='+engine.as_posix(),
                    str(HERE/'compatibility.patch')],check=True)
    edit(rd/'tr_cache.cpp', 'ST_GLM_Preflight(path, ppFileBuffer, len, MAX_G2_BONES);',
         'ST_GLM_Preflight(path, ppFileBuffer, len);')
    edit(engine/'CMakeLists.txt',
         'option(BuildMPRdVulkan "Whether to create projects for the MP vulkan renderer (rd-vulkan_x86.dll)" ON)',
         'option(BuildMPRdVulkan "Build the optional MP Vulkan renderer" OFF)')
    # API 13 only for this module: the appended Vulkan imports cannot be read from an older engine.
    edit(rd/'tr_init.cpp','assert( rimp );', 'if (apiVersion != 13 || !rimp) return nullptr;\n\tassert( rimp );')
    edit(rd/'tr_init.cpp','if ( apiVersion != REF_API_VERSION ) {','if ( apiVersion != 13 ) {')
    for name in ('tr_st_chat.inc','tr_st_vulkan_init.inc'):
        shutil.copyfile(HERE/name,rd/name)
    shutil.copyfile(HERE/'cl_st_renderer.inc',mp/'client/cl_st_renderer.inc')
    shutil.copyfile(mp/'rd-vanilla/renderer_st_mvp_pose.inc',rd/'renderer_st_mvp_pose.inc')
    cosmetic = (mp/'rd-common/st_cosmetic_render.inc').read_text()
    cosmetic = cosmetic.replace('return m->mdxm;', 'return m->data.glm->header;')
    # Vulkan shares Vanilla's surface submission API and uses GPU-skinning model storage.
    cosmetic = re.sub(r'// ST_VANILLA_COMPAT_BEGIN.*?// ST_VANILLA_COMPAT_END', '', cosmetic, flags=re.S)
    (rd/'st_cosmetic_render.inc').write_text(cosmetic,newline='\n')
    edit(rd/'tr_init.cpp','extern "C" {\nQ_EXPORT refexport_t*',
         '#include "tr_st_vulkan_init.inc"\nextern int ST_MvpPackPose(void *,unsigned char *,int);\n'
         'extern void *ST_MvpUnpackPose(const unsigned char *,int);\nextern "C" {\nQ_EXPORT refexport_t*')
    edit(rd/'tr_init.cpp','ri = *rimp;', 'ri = *rimp;\n\tstEngineError=ri.Error;\n\tri.Error=STVulkan_Error;')
    edit(rd/'tr_init.cpp','re.Shutdown = RE_Shutdown;', 're.Shutdown = RE_Shutdown;\n'
         '    re.ST_MvpPackPose=ST_MvpPackPose;\n    re.ST_MvpUnpackPose=ST_MvpUnpackPose;\n'
         '    re.G2API_STLockPose=G2API_STLockPose;\n    re.ST_ChatUpload=RE_STChatUpload;')
    edit(rd/'tr_init.cpp','void R_Init( void ) {','void R_Init( void ) {\n'
         '    ri.Cvar_Get("st_mirrorRenderer","0",CVAR_ROM,"Saber Trials pose capability");\n'
         '    ri.Cvar_Set("st_mirrorRenderer","1");\n    ri.Cvar_Set("st_handProtocol","1");')
    edit(rd/'tr_init.cpp','\tR_ShutdownWorldEffects();',
         '    ri.Cvar_Set("st_mirrorRenderer","0");\n'
         '    if (!tr.inited) {\n'
         '        if(destroyWindow) { vk_shutdown(); ri.WIN_Shutdown(); Com_Memset(&glConfig,0,sizeof(glConfig)); }\n'
         '        return;\n    }\n\tR_ShutdownWorldEffects();')
    edit(rd/'tr_init.cpp','\t\tvk_shutdown();','\t\tvk_shutdown();\n        ri.WIN_Shutdown();\n        Com_Memset(&glConfig,0,sizeof(glConfig));')
    shader = rd/'tr_shader.cpp'
    edit(shader,'void R_InitShaders( qboolean server )\n{',
         '#include "tr_st_chat.inc"\nvoid R_InitShaders( qboolean server )\n{\n    ST_ChatResetImages();')
    # Use the stable-paged Ghoul2 surface pool already exercised by Rend2.
    ghoul = rd/'tr_ghoul2.cpp'
    text = ghoul.read_text()
    first = text.index('static const int MAX_RENDERABLE_SURFACES')
    last = text.index('bool HackadelicOnClient', first)
    existing = (mp/'rd-rend2/tr_ghoul2.cpp').read_text()
    a = existing.index('#include "../rd-common/st_surface_pool.h"')
    b = existing.index('bool HackadelicOnClient', a)
    ghoul.write_text(text[:first]+existing[a:b]+text[last:],newline='\n')
    # Fail cleanly before dereferencing a missing loader; SDL owns the library lifetime.
    edit(rd/'vk_instance.cpp','vk_debug("Failed to find entrypoint vkGetInstanceProcAddr\\n");',
         'ri.Error(ERR_FATAL,"Vulkan loader is unavailable");')
    edit(rd/'vk_init.cpp','window = ri.WIN_Init(&windowDesc, &glConfig);',
         'window = ri.WIN_Init(&windowDesc, &glConfig);\n'
         '        if (!glConfig.vidWidth || !glConfig.vidHeight) ri.Error(ERR_FATAL,"Could not create Vulkan window");')
    # The proposed upstream interface does not expose SDL's extension list yet.
    # Keep the existing platform requirements, with Linux/macOS validation explicitly pending.
    sdl = engine/'shared/sdl/sdl_window.cpp'
    edit(sdl,'\t\tif( r_mode->integer != R_MODE_FALLBACK )',
         '\t\tif (windowDesc->api == GRAPHICS_API_VULKAN) { glConfig->vidWidth=glConfig->vidHeight=0; return {}; }\n'
         '\t\tif( r_mode->integer != R_MODE_FALLBACK )')
    edit(sdl,'Com_Error(ERR_FATAL, "Failed to load Vulkan library (code %d): %s", code, SDL_GetError());',
         'Com_Printf("Failed to load Vulkan library (code %d): %s\\n", code, SDL_GetError());\n        return nullptr;')
    # The Vulkan window already holds SDL's loader reference. Avoid a new reference per restart.
    edit(sdl,'int code = SDL_Vulkan_LoadLibrary(NULL);',
         'if (void *address=SDL_Vulkan_GetVkGetInstanceProcAddr()) return address;\n'
         '    int code = SDL_Vulkan_LoadLibrary(NULL);')
    edit(sdl,'\tCom_Printf("graphics mode: %d", (int)windowDesc->api);','')
    # Validate that window creation actually succeeded, also on r_mode 4.
    edit(sdl,'\t\tif ( windowDesc->api == GRAPHICS_API_OPENGL ) {\n\t\t\tif ( opengl_context == NULL ) {',
         '\t\tif (!screen) { SDL_FreeSurface(icon); return RSERR_UNKNOWN; }\n'
         '\t\tif ( windowDesc->api == GRAPHICS_API_OPENGL ) {\n\t\t\tif ( opengl_context == NULL ) {')
    main = mp/'client/cl_main.cpp'
    edit(main,'void CL_InitRenderer( void ) {', '#include "cl_st_renderer.inc"\nvoid CL_InitRenderer( void ) {')
    edit(main,'re->BeginRegistration( &cls.glconfig );','ST_BeginRenderer();')
    text = main.read_text()
    first = text.index('\tCom_sprintf( dllName, sizeof( dllName ), "%s_" ARCH_STRING DLL_EXT, cl_renderer->string );')
    last = text.index('\t//set up the import table', first)
    text = text[:first]+'''    Cvar_Get("st_activeRenderer","",CVAR_ROM);
    Cvar_Get("st_rendererError","",CVAR_ROM);
    Cvar_Get("st_lastGoodRenderer","rd-vanilla",CVAR_ARCHIVE);
    if (stForcedRenderer.empty()) Cvar_Set("st_rendererError", "");
    memset(&ri,0,sizeof(ri));

'''+text[last:]
    main.write_text(text,newline='\n')
    edit(main,'ret = GetRefAPI( REF_API_VERSION, &ri );','ret = ST_LoadRenderer(&ri);')
    # Change the one existing Renderer row. Do not expose unimplemented DLSS toggles.
    for root in (engine,frontend):
        header=root/'codemp/ui/st_setup_catalog.h'
        edit(header,'rd-vanilla=Vanilla|rd-rend2=Rend2','rd-vanilla=Vanilla|rd-rend2=Rend2|rd-vulkan=Vulkan')
    core = mp/'client/st_setup_core.h'
    edit(core,'it->second!="rd-vanilla"&&it->second!="rd-rend2"',
         'it->second!="rd-vanilla"&&it->second!="rd-rend2"&&it->second!="rd-vulkan"')
    setup=mp/'client/cl_st_setup.inc'
    edit(setup,'sizeof(r->help));say(value);break;}',
         'sizeof(r->help));\n'
         '  if(!Q_stricmp(s.name,"cl_renderer") && *Cvar_VariableString("st_rendererError"))\n'
         '    Com_sprintf(r->help,sizeof(r->help),"Using %s: %s",Cvar_VariableString("st_activeRenderer"),Cvar_VariableString("st_rendererError"));\n'
         '  say(value);break;}')
    # Profiling is opt-in and leaves the simulation clock and network timing alone.
    for folder,name in ((mp/'client','cl_st_frame_profile.inc'),(rd,'vk_st_profile.inc')):
        shutil.copyfile(HERE/name,folder/name)
        shutil.copyfile(HERE/'st_frame_stats.h',folder/'st_frame_stats.h')
    edit(main,'void CL_Frame ( int msec ) {',
         '#include "cl_st_frame_profile.inc"\nvoid CL_Frame ( int msec ) {\n    ST_FrameProfileBegin();')
    edit(main,'\tcls.framecount++;','\tcls.framecount++;\n    ST_FrameProfileEnd();')
    frame=rd/'vk_frame.cpp'
    edit(frame,'#include "tr_local.h"','#include "tr_local.h"\n#include "vk_st_profile.inc"')
    edit(frame,'VK_CHECK( qvkBeginCommandBuffer( vk.cmd->command_buffer, &begin_info ) );',
         'VK_CHECK( qvkBeginCommandBuffer( vk.cmd->command_buffer, &begin_info ) );\n    ST_VulkanProfileBegin();')
    edit(frame,'VK_CHECK( qvkEndCommandBuffer( vk.cmd->command_buffer ) );',
         'ST_VulkanProfileEnd();\n    VK_CHECK( qvkEndCommandBuffer( vk.cmd->command_buffer ) );')
    edit(frame,'        vk_resize_geometry_buffer();',
         '        stGpuRecording=false;stGpuPending[vk.cmd_index]=false;\n        vk_resize_geometry_buffer();')
    edit(rd/'vk_init.cpp','void vk_shutdown( void )\n{',
         'extern void ST_VulkanProfileShutdown();\nvoid vk_shutdown( void )\n{\n'
         '    if(vk.device && qvkDeviceWaitIdle) qvkDeviceWaitIdle(vk.device);\n    ST_VulkanProfileShutdown();')
    # Dynamic Unicode images must not consume the map's append-only image arena on every resize.
    edit(rd/'tr_local.h','typedef struct image_s {',
         'typedef struct image_s {\n    VkDeviceMemory stDynamicMemory;')
    images=rd/'vk_image.cpp'
    edit(images,'\tVkFormat format = (VkFormat)image->internalFormat;',
         '\tVkFormat format = (VkFormat)image->internalFormat;\n'
         '    if(image->stDynamicMemory) vk_wait_idle();')
    edit(images,'\t// create image\n\t{',
         '    if(image->stDynamicMemory) { qvkFreeMemory(vk.device,image->stDynamicMemory,NULL); image->stDynamicMemory=VK_NULL_HANDLE; }\n'
         '\t// create image\n\t{')
    edit(images,'\t\tallocate_and_bind_image_memory( image->handle );',
         '        if(!strncmp(image->imgName,"*stchat",7)) {\n'
         '            VkMemoryRequirements requirements; qvkGetImageMemoryRequirements(vk.device,image->handle,&requirements);\n'
         '            VkMemoryAllocateInfo allocation={}; allocation.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;\n'
         '            allocation.allocationSize=requirements.size;\n'
         '            allocation.memoryTypeIndex=vk_find_memory_type(requirements.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);\n'
         '            VK_CHECK(qvkAllocateMemory(vk.device,&allocation,NULL,&image->stDynamicMemory));\n'
         '            VK_CHECK(qvkBindImageMemory(vk.device,image->handle,image->stDynamicMemory,0));\n'
         '        } else allocate_and_bind_image_memory( image->handle );')
    edit(images,'\t\tvk_destroy_image_resources( &img->handle, &img->view );',
         '\t\tvk_destroy_image_resources( &img->handle, &img->view );\n'
         '        if(img->stDynamicMemory) { qvkFreeMemory(vk.device,img->stDynamicMemory,NULL); img->stDynamicMemory=VK_NULL_HANDLE; }')
