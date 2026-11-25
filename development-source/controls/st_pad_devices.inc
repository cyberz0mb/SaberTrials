// Keep mapped devices open so the controller the player touches can take over.
#include <vector>
struct STPadDevice {
    SDL_GameController* handle;
    SDL_JoystickID id;
    bool axisEngaged[SDL_CONTROLLER_AXIS_MAX];
};
static std::vector<STPadDevice> stPadDevices;
static bool stPadWatching;

static bool STPadPressed(SDL_GameController* pad, int button) {
    if (button < SDL_CONTROLLER_BUTTON_MAX && button < 15)
        return SDL_GameControllerGetButton(pad, (SDL_GameControllerButton)button) != 0;
    if (button == 16 || button == 17) {
        const auto axis = button == 16 ? SDL_CONTROLLER_AXIS_TRIGGERLEFT : SDL_CONTROLLER_AXIS_TRIGGERRIGHT;
        return SDL_GameControllerGetAxis(pad, axis) > 8192;
    }
    return false;
}

static void STPadButtonState(int button, bool pressed, bool focused) {
    if (!focused || !pressed) stPadBlocked[button] = pressed;
    const bool held = focused && pressed && !stPadBlocked[button];
    if (held != stPadHeld[button]) {
        Sys_QueEvent(0, SE_GAMEPAD_BUTTON, button, held, 0, NULL);
        stPadHeld[button] = held;
    }
}

static void STPadSelect(SDL_GameController* next, int initiatingButton = -1, bool suppressHeld = true) {
    if (next == stPad) return;
    if (stPad) STPadRelease();
    stPad = next;
    // Other buttons may already be held on the incoming device. Only the
    // action that selected it should become a new click or gameplay press.
    if (next) {
        for (int i = 0; i < 18; ++i)
            stPadBlocked[i] = suppressHeld && i != initiatingButton && STPadPressed(next, i);
    }
    Cvar_Set("st_controllerDevice", next ? SDL_GameControllerName(next) : "No compatible controller detected");
    Cvar_SetValue("st_controllerActive", next ? 1 : 0);
}

static void STPadAdd(int index) {
    const SDL_JoystickID id = SDL_JoystickGetDeviceInstanceID(index);
    if (id < 0 || !SDL_IsGameController(index)) return;
    for (const auto& device : stPadDevices) if (device.id == id) return;
    SDL_GameController* handle = SDL_GameControllerOpen(index);
    if (!handle) return;
    stPadDevices.push_back({handle, id, {}});
    if (!stPad) {
        if (in_joystick->integer) Key_ClearStates();
        STPadSelect(handle, -1, false);
    }
}

static void STPadClose() {
    STPadSelect(NULL);
    for (const auto& pad : stPadDevices) SDL_GameControllerClose(pad.handle);
    stPadDevices.clear();
    if (stPadWatching) SDL_QuitSubSystem(SDL_INIT_GAMECONTROLLER);
    stPadWatching = false;
}

static void STPadBeginFrame() {
    static cvar_t* mode = Cvar_Get("st_controllerEnabled", "1", CVAR_ARCHIVE);
    static cvar_t* device = Cvar_Get("st_controllerDevice", "No compatible controller detected", CVAR_ROM);
    static cvar_t* active = Cvar_Get("st_controllerActive", "0", CVAR_ROM);
    (void)device; (void)active;
    // Both the original default (0) and Automatic (1) allow hot-plugging.
    if (mode->integer == 2) {
        if (stPadWatching) STPadClose();
        return;
    }
    if (stPadWatching || SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) < 0) return;
    stPadWatching = true;
    for (int i = 0; i < SDL_NumJoysticks(); ++i) STPadAdd(i);
}

static void STPadHandleEvent(const SDL_Event& event, bool focused) {
    if (!stPadWatching) return;
    if (event.type == SDL_CONTROLLERDEVICEADDED) {
        STPadAdd(event.cdevice.which);
        return;
    }
    if (event.type == SDL_CONTROLLERDEVICEREMOVED) {
        for (auto it = stPadDevices.begin(); it != stPadDevices.end(); ++it) {
            if (it->id != event.cdevice.which) continue;
            if (it->handle == stPad) STPadSelect(NULL);
            SDL_GameControllerClose(it->handle);
            stPadDevices.erase(it);
            if (!stPad && !stPadDevices.empty()) STPadSelect(stPadDevices.front().handle);
            break;
        }
        return;
    }

    const bool motion = event.type == SDL_CONTROLLERAXISMOTION;
    const auto id = motion ? event.caxis.which : event.cbutton.which;
    for (auto& pad : stPadDevices) {
        if (pad.id != id) continue;
        if (motion) {
            const int axis = event.caxis.axis;
            if (axis >= SDL_CONTROLLER_AXIS_MAX) return;
            const bool trigger = axis >= SDL_CONTROLLER_AXIS_TRIGGERLEFT;
            static cvar_t* deadzone = Cvar_Get("st_controllerDeadzone", "0.15", CVAR_ARCHIVE);
            const int threshold = trigger ? 8192 : (int)(32767 * Com_Clamp(.15f, .95f, deadzone->value));
            const int magnitude = std::abs((int)event.caxis.value);
            const int button = trigger ? 16 + axis - SDL_CONTROLLER_AXIS_TRIGGERLEFT : -1;
            if (magnitude > threshold && !pad.axisEngaged[axis]) {
                pad.axisEngaged[axis] = true;
                if (focused) STPadSelect(pad.handle, button);
            } else if (magnitude <= threshold / 2) {
                pad.axisEngaged[axis] = false;
            }
            if (trigger && pad.handle == stPad)
                STPadButtonState(button, event.caxis.value > 8192, focused);
        } else {
            const int button = event.cbutton.button;
            if (button >= 15) return;
            const bool pressed = event.type == SDL_CONTROLLERBUTTONDOWN;
            if (pressed && focused) STPadSelect(pad.handle, button);
            if (pad.handle == stPad) STPadButtonState(button, pressed, focused);
        }
        return;
    }
}
