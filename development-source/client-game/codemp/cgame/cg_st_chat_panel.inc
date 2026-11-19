/* HUD chat history is local to the current match. */
#include "ui/st_chat_layout.h"
enum { ST_CHAT_AUTO, ST_CHAT_COLLAPSED, ST_CHAT_EXPANDED };
#define ST_CHAT_MAX_LINES 12
typedef char stChatLine_t[MAX_SAY_TEXT + 3];

void ST_ToggleChat_f(void)
{
	cg.chatPanelMode = cg.chatPanelMode == ST_CHAT_COLLAPSED
		? ST_CHAT_EXPANDED : ST_CHAT_COLLAPSED;
}

void CG_ChatBox_AddString(char *chatStr)
{
	if (cg_chatBox.integer <= 0 || !chatStr[0])
		return;
	chatBoxItem_t *chat = &cg.chatItems[cg.chatItemActive];
	Q_strncpyz(chat->string, chatStr, sizeof(chat->string));
	chat->time = cg.time + cg_chatBox.integer;
	qtime_t now;
	trap->RealTime(&now);
	Com_sprintf(chat->stamp, sizeof(chat->stamp), "[%02d:%02d]", now.tm_hour, now.tm_min);
	cg.chatItemActive = (cg.chatItemActive + 1) % MAX_CHATBOX_ITEMS;
}

static int ST_ChatWrap(const char *text, stChatLine_t *lines, float width, float scale)
{
	char color = '7';
	int count = 0;
	while (*text && count < ST_CHAT_MAX_LINES) {
		char *line = lines[count++];
		int len = 2, space = 0;
		const char *nextWord = NULL;
		char wordColor = color;
		float used = 0;
		line[0] = '^';
		line[1] = color;
		while (*text && *text != '\n') {
			if (Q_IsColorString(text)) {
				line[len++] = *text++;
				color = *text;
				line[len++] = *text++;
				continue;
			}
			if (*text == ' ') {
				space = len;
				nextWord = text + 1;
				wordColor = color;
			}
			int advance = 1;
			if ((unsigned char)*text >= 128)
				trap->R_AnyLanguage_ReadCharFromString(text, &advance, NULL);
			char glyph[8];
			advance = Com_Clampi(1, sizeof(glyph)-1, advance);
			Q_strncpyz(glyph, text, advance + 1);
			const int glyphWidth = CG_Text_Width(glyph, scale, FONT_SMALL2);
			if (used > 0 && used + glyphWidth > width) {
				if (nextWord) {
					text = nextWord;
					len = space;
					color = wordColor;
				}
				break;
			}
			const int copied = (int)strlen(glyph);
			memcpy(line + len, glyph, copied);
			len += copied;
			used += glyphWidth;
			text += copied;
		}
		line[len] = '\0';
		if (*text == '\n') ++text;
		while (*text == ' ') ++text;
	}
	return count;
}

static void ST_ChatPic(float x, float y, float w, float h, float u, float v, float u2, float v2,
	qhandle_t shader, const float *color)
{
	if (!shader) return;
	trap->R_SetColor(color);
	trap->R_DrawStretchPic(x, y, w, h, u, v, u2, v2, shader);
	trap->R_SetColor(NULL);
}

static void CG_ChatBox_DrawStrings(void)
{
	if (cg_chatBox.integer <= 0 || cg.chatPanelMode == ST_CHAT_COLLAPSED)
		return;
	const qboolean expanded = cg.chatPanelMode == ST_CHAT_EXPANDED;
	const stChatLayout_t layout = ST_ChatLayout(st_chatSize.value, st_chatWidth.value,
		st_chatHeight.value, st_chatOpacity.value);
	const float s = layout.size, fontScale = .65f*s, stampScale = .47f*s;
	const float row = 16*s, x = 10, padding = 12*s, stampColumn = 32*s;
	const float bottom = cg.scoreBoardShowing ? 474 : Com_Clampi(190, 400, cg_chatBoxHeight.integer+33);
	const float height = Q_min(layout.height, bottom-25*s);
	const float y = bottom-height;
	const int visible = Com_Clampi(1, ST_CHAT_MAX_LINES, (int)((height-20*s)/row));
	stChatLine_t lines[ST_CHAT_MAX_LINES];
	const char *stamps[ST_CHAT_MAX_LINES];
	int total = 0;
	for (int i = 0; i < MAX_CHATBOX_ITEMS; ++i) {
		const chatBoxItem_t *chat = &cg.chatItems[(cg.chatItemActive+i) % MAX_CHATBOX_ITEMS];
		if (!chat->string[0] || (!expanded && chat->time <= cg.time))
			continue;
		stChatLine_t wrapped[ST_CHAT_MAX_LINES];
		const int count = ST_ChatWrap(chat->string, wrapped, layout.width-2*padding-stampColumn, fontScale);
		for (int j = 0; j < count; ++j, ++total) {
			memcpy(lines[total % ST_CHAT_MAX_LINES], wrapped[j], strlen(wrapped[j])+1);
			stamps[total % ST_CHAT_MAX_LINES] = j ? NULL : chat->stamp;
		}
	}
	if (!total && !expanded)
		return;
	const int count = Q_min(total, visible);
	ST_ChatDrawFrame(ST_ChatPic, st_hudMedia.chatFill, st_hudMedia.chatFrame,
		x, y, layout.width, height, s, s, layout.opacity);
	const float headerAspect = ST_HudAspect();
	ST_ChatPic(x, y-11*s, 102*s*headerAspect, 26*s, 0, 0, 1, 1, st_hudMedia.chatHeader, NULL);
	ST_HudText(x/headerAspect+32*s, y-5*s, 8*s, "CHAT", st_hudWhite);
	vec4_t timeColor = {.51f,.77f,.89f,1};
	const float top = y+13*s;
	if (!count)
		CG_Text_Paint(x+padding, top, fontScale, timeColor, "No recent messages", 0, 0, ITEM_TEXTSTYLE_OUTLINED, FONT_SMALL2);
	for (int i = 0; i < count; ++i) {
		const int index = (total-count+i) % ST_CHAT_MAX_LINES;
		const float textY = top+i*row;
		if (stamps[index]) {
			CG_Text_Paint(x+padding, textY+2*s, stampScale, timeColor, stamps[index], 0, 0, ITEM_TEXTSTYLE_OUTLINED, FONT_SMALL2);
			CG_FillRect(x+padding+stampColumn-6*s, textY, .4f*s, 10*s, timeColor);
		}
		CG_Text_Paint(x+padding+stampColumn, textY, fontScale, colorWhite,
			lines[index], 0, 0, ITEM_TEXTSTYLE_OUTLINED, FONT_SMALL2);
	}
}
