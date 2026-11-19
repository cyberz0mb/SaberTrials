#ifndef ST_CHAT_LAYOUT_H
#define ST_CHAT_LAYOUT_H

#define ST_CHAT_FRAME "gfx/sabertrials/hud_theme/chat_frame"
#define ST_CHAT_FILL "gfx/sabertrials/hud_theme/chat_frame_fill"
#define ST_CHAT_HEADER "gfx/sabertrials/hud_theme/chat_header"

typedef struct {
	float width, height, size, opacity;
} stChatLayout_t;

static float ST_ChatScalePercent(float value)
{
	if (value == 0) return 80;
	if (value == 1) return 100;
	if (value == 2) return 120;
	return Com_Clamp(75, 125, value);
}

static stChatLayout_t ST_ChatLayout(float size, float width, float height, float opacity)
{
	stChatLayout_t result;
	result.size = ST_ChatScalePercent(size) * .01f;
	result.width = Com_Clamp(24, 68, width) * 6.4f * result.size;
	result.height = Com_Clamp(12, 36, height) * 4.8f * result.size;
	result.opacity = Com_Clamp(0, 100, opacity) * .01f;
	return result;
}

typedef void (*stChatPic_t)(float, float, float, float, float, float, float, float,
	qhandle_t, const float *);

static void ST_ChatDrawFrame(stChatPic_t pic, qhandle_t fill, qhandle_t frame,
	float x, float y, float w, float h, float unitX, float unitY, float opacity)
{
	const float ex = 18 * unitX, ey = 17 * unitY;
	const float xs[] = {x, x+ex, x+w-ex, x+w};
	const float ys[] = {y, y+ey, y+h-ey, y+h};
	const float u[] = {0, .067f, .933f, 1};
	const float v[] = {0, .189f, .811f, 1};
	const vec4_t tint = {1, 1, 1, opacity};
	for (int row = 0; row < 3; ++row) {
		for (int col = 0; col < 3; ++col) {
			const float dx = xs[col+1]-xs[col], dy = ys[row+1]-ys[row];
			pic(xs[col], ys[row], dx, dy, u[col], v[row], u[col+1], v[row+1], fill, tint);
			pic(xs[col], ys[row], dx, dy, u[col], v[row], u[col+1], v[row+1], frame, NULL);
		}
	}
}
#endif
