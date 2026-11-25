#ifdef _WIN32
#include "win32/resource.h"
#endif

static void SetClientWindowIcon(SDL_Window *window, SDL_Surface *fallback)
{
#ifdef _WIN32
	SDL_SysWMinfo info = {};
	SDL_VERSION(&info.version);
	if (SDL_GetWindowWMInfo(window, &info) && info.subsystem == SDL_SYSWM_WINDOWS)
	{
		const HMODULE module = GetModuleHandleW(nullptr);
		const auto large = static_cast<HICON>(LoadImageW(module, MAKEINTRESOURCEW(IDI_ICON1),
			IMAGE_ICON, GetSystemMetrics(SM_CXICON), GetSystemMetrics(SM_CYICON), LR_SHARED));
		const auto small = static_cast<HICON>(LoadImageW(module, MAKEINTRESOURCEW(IDI_ICON1),
			IMAGE_ICON, GetSystemMetrics(SM_CXSMICON), GetSystemMetrics(SM_CYSMICON), LR_SHARED));
		if (large && small)
		{
			SendMessageW(info.info.win.window, WM_SETICON, ICON_BIG, reinterpret_cast<LPARAM>(large));
			SendMessageW(info.info.win.window, WM_SETICON, ICON_SMALL, reinterpret_cast<LPARAM>(small));
			return;
		}
	}
#endif
	SDL_SetWindowIcon(window, fallback);
}
