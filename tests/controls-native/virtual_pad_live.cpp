// Test UI only. Supply SDL 2.0.14+ for its virtual joystick test API.
#include <windows.h>
#include <cmath>

template<typename T> static T sdlFunction(const char* name) {
    return reinterpret_cast<T>(GetProcAddress(GetModuleHandleA("SDL2.dll"), name));
}

const char* ST_VirtualPadDrive(int phase, float x, float y) {
    using Attach = int (*)(int, int, int, int);
    using Open = void* (*)(int);
    using Axis = int (*)(void*, int, short);
    using Button = int (*)(void*, int, unsigned char);
    using Update = void (*)();
    static auto attach = sdlFunction<Attach>("SDL_JoystickAttachVirtual");
    static auto open = sdlFunction<Open>("SDL_JoystickOpen");
    static auto axis = sdlFunction<Axis>("SDL_JoystickSetVirtualAxis");
    static auto button = sdlFunction<Button>("SDL_JoystickSetVirtualButton");
    static auto update = sdlFunction<Update>("SDL_JoystickUpdate");
    static int previous = 0;
    static void* pad;
    if (!phase) return nullptr;
    if (!attach || !open || !axis || !button || !update) return "missing SDL virtual input support";
    if (phase == 1 && !previous) {
        // The first pad stays idle. All navigation comes from the second.
        if (attach(1, 6, 15, 0) < 0) return "first controller failed";
        int index = attach(1, 6, 15, 0);
        if (index < 0 || !(pad = open(index))) return "second controller failed";
    } else if (phase == 2) {
        // Drive toward the Controller tab using only stick input.
        auto steer = [](float delta) -> short {
            if (std::fabs(delta) < 3) return 0;
            const int strength = std::fabs(delta) > 18 ? 24000 : 11000;
            return static_cast<short>(delta > 0 ? strength : -strength);
        };
        axis(pad, 0, steer(372 - x));
        axis(pad, 1, steer(130 - y));
    } else if ((phase == 3 || phase == 4) && previous != phase) {
        axis(pad, 0, 0);
        axis(pad, 1, 0);
        const int face = phase == 3 ? 0 : 1;
        // Both edges arrive between two game frames.
        button(pad, face, 1);
        update();
        button(pad, face, 0);
        update();
    }
    previous = phase;
    return nullptr;
}
