// Optional GPU timestamps. Read only after the command buffer's existing fence wait.
// No added GPU wait, no vendor extension, and no dependency on NVIDIA software.
#include "st_frame_stats.h"
static VkQueryPool stGpuQueries;
static PFN_vkCreateQueryPool stCreateQueryPool;
static PFN_vkDestroyQueryPool stDestroyQueryPool;
static PFN_vkCmdResetQueryPool stResetQueries;
static PFN_vkCmdWriteTimestamp stWriteTimestamp;
static PFN_vkGetQueryPoolResults stGetQueries;
static bool stGpuPending[NUM_COMMAND_BUFFERS];
static bool stGpuRecording;
static double stTimestampNanoseconds;
static uint32_t stTimestampBits;
static int stGpuTarget;
static STFrameStats stGpuTimes;

void ST_VulkanProfileShutdown() {
    if (stGpuQueries && stDestroyQueryPool) stDestroyQueryPool(vk.device,stGpuQueries,nullptr);
    stGpuQueries=VK_NULL_HANDLE;
    memset(stGpuPending,0,sizeof(stGpuPending));
    stGpuRecording=false; stGpuTarget=0; stGpuTimes.clear();
}
static bool ST_VulkanProfileInit() {
    if (stGpuQueries) return true;
    VkPhysicalDeviceProperties properties;
    qvkGetPhysicalDeviceProperties(vk.physical_device,&properties);
    uint32_t count=0;
    qvkGetPhysicalDeviceQueueFamilyProperties(vk.physical_device,&count,nullptr);
    std::vector<VkQueueFamilyProperties> queues(count);
    qvkGetPhysicalDeviceQueueFamilyProperties(vk.physical_device,&count,queues.data());
    if (vk.queue_family_index>=count || !queues[vk.queue_family_index].timestampValidBits) return false;
    stTimestampBits=queues[vk.queue_family_index].timestampValidBits;
    stTimestampNanoseconds=properties.limits.timestampPeriod;
    stCreateQueryPool=(PFN_vkCreateQueryPool)qvkGetDeviceProcAddr(vk.device,"vkCreateQueryPool");
    stDestroyQueryPool=(PFN_vkDestroyQueryPool)qvkGetDeviceProcAddr(vk.device,"vkDestroyQueryPool");
    stResetQueries=(PFN_vkCmdResetQueryPool)qvkGetDeviceProcAddr(vk.device,"vkCmdResetQueryPool");
    stWriteTimestamp=(PFN_vkCmdWriteTimestamp)qvkGetDeviceProcAddr(vk.device,"vkCmdWriteTimestamp");
    stGetQueries=(PFN_vkGetQueryPoolResults)qvkGetDeviceProcAddr(vk.device,"vkGetQueryPoolResults");
    if (!stCreateQueryPool || !stDestroyQueryPool || !stResetQueries || !stWriteTimestamp || !stGetQueries) return false;
    VkQueryPoolCreateInfo info={};
    info.sType=VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO;
    info.queryType=VK_QUERY_TYPE_TIMESTAMP;
    info.queryCount=NUM_COMMAND_BUFFERS*2;
    return stCreateQueryPool(vk.device,&info,nullptr,&stGpuQueries)==VK_SUCCESS;
}
static void ST_VulkanProfileBegin() {
    stGpuRecording=false;
    auto setting=ri.Cvar_Get("r_vkProfileFrames","0",CVAR_TEMP,"Record 1-6000 Vulkan GPU timestamp samples");
    const int target=std::max(0,std::min(6000,setting->integer));
    if (!target) { stGpuTarget=0; return; }
    if (!ST_VulkanProfileInit()) {
        ri.Printf(PRINT_WARNING,"ST_VULKAN_GPU unavailable: graphics queue timestamps unsupported\n");
        ri.Cvar_Set("r_vkProfileFrames","0"); return;
    }
    if (target!=stGpuTarget) {
        stGpuTarget=target;stGpuTimes.clear();memset(stGpuPending,0,sizeof(stGpuPending));
    }
    const uint32_t slot=vk.cmd_index;
    if (stGpuPending[slot]) {
        uint64_t results[4]={};
        VkResult result=stGetQueries(vk.device,stGpuQueries,slot*2,2,sizeof(results),results,2*sizeof(uint64_t),
            VK_QUERY_RESULT_64_BIT|VK_QUERY_RESULT_WITH_AVAILABILITY_BIT);
        if (result==VK_SUCCESS && results[1] && results[3]) {
            uint64_t elapsed=results[2]-results[0];
            if(stTimestampBits<64) elapsed&=(uint64_t(1)<<stTimestampBits)-1;
            stGpuTimes.add(elapsed*stTimestampNanoseconds/1000000.0);
        }
    }
    if ((int)stGpuTimes.values.size()>=stGpuTarget) {
        ri.Printf(PRINT_ALL,"ST_VULKAN_GPU frames=%d mean_ms=%.4f p95_ms=%.4f p99_ms=%.4f\n",
            stGpuTarget,stGpuTimes.mean(),stGpuTimes.percentile(.95),stGpuTimes.percentile(.99));
        ri.Cvar_Set("r_vkProfileFrames","0");stGpuTarget=0;return;
    }
    stGpuPending[slot]=false;
    stResetQueries(vk.cmd->command_buffer,stGpuQueries,slot*2,2);
    stWriteTimestamp(vk.cmd->command_buffer,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,stGpuQueries,slot*2);
    stGpuRecording=true;
}
static void ST_VulkanProfileEnd() {
    if (!stGpuRecording) return;
    stWriteTimestamp(vk.cmd->command_buffer,VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,stGpuQueries,vk.cmd_index*2+1);
    stGpuPending[vk.cmd_index]=true;
    stGpuRecording=false;
}
