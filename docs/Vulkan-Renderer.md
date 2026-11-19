# Optional Vulkan client — development milestone

The separate Windows Vulkan preview loads alongside Vanilla and Rend2. Use
`tools/Stage-Vulkan.py` to stage it, then launch with the
[Vulkan test launcher](../tools/launchers/development/Play-SaberTrials-Vulkan-Test.cmd).
In **Settings > Video**, select Vulkan. If initialization fails, the client
tries the last successful OpenGL renderer, then Vanilla.

The preview uses the [OpenJK Vulkan renderer work](https://github.com/JACoders/OpenJK/pull/1330),
pinned in the [Vulkan overlay](../development-source/vulkan/overlay.py).
See [validation](Vulkan-Validation.md) and the [Vulkan license notice](licenses/Khronos-Vulkan-MIT.txt).
