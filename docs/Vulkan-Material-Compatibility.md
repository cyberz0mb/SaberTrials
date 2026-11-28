# Vulkan material compatibility

Vulkan renders the color and alpha stages of compatible materials when their
shader declarations include optional Rend2 normal or material maps. The Vulkan
renderer uses the standard appearance in those stages.

The compatibility logic is part of the renderer overlay in
`development-source/vulkan/`. To verify it, compare the same shader in
Rend2 and Vulkan with compatible content and check for missing fallback textures.
