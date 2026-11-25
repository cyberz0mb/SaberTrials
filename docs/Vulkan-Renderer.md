# Optional Vulkan renderer

Vulkan is available alongside Vanilla and Rend2 in the Windows client.
In **Setup > Video**, select Vulkan, then apply and keep the change.
If initialization fails, the client
tries the last successful OpenGL renderer, then Vanilla.

The preview uses the [OpenJK Vulkan renderer work](https://github.com/JACoders/OpenJK/pull/1330),
pinned in the [Vulkan overlay](../development-source/vulkan/overlay.py).
See [validation](Vulkan-Validation.md) and the [Vulkan license notice](licenses/Khronos-Vulkan-MIT.txt).

Vulkan supports Enhanced Maps and STCOS1 character meshes. See the
[material compatibility guide](Vulkan-Material-Compatibility.md).
