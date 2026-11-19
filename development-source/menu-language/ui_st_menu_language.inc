/* Localized menu copy, kept independent of game and chat language. */
#include <initializer_list>
#include <string>
#include <unordered_map>
#include <vector>
#include "qcommon/st_utf8.h"

static constexpr const char *stMenuLanguageCvar = "st_menuLanguage";
static bool stMenuLanguageRaw;
struct STML_Raw {
	bool saved = stMenuLanguageRaw;
	STML_Raw() { stMenuLanguageRaw = true; }
	~STML_Raw() { stMenuLanguageRaw = saved; }
};
static const std::unordered_map<std::string, std::string>& STML_Catalog() {
	static std::unordered_map<std::string, std::string> catalog;
	static int active = -1;
	const int language = (int)trap->Cvar_VariableValue(stMenuLanguageCvar);
	if (active == language)
		return catalog;
	active = language;
	catalog.clear();
	if (language < 2 || language > 17)
		return catalog;

	int size = 0;
	const char *data = trap->MenuCatalog ? trap->MenuCatalog(language, &size) : nullptr;
	if (data && size > 0 && size <= 1024 * 1024) {
		const std::string contents(data, size);
		for (size_t start = 0; start < contents.size();) {
			size_t end = contents.find('\n', start);
			if (end == std::string::npos)
				end = contents.size();
			const size_t separator = contents.find('\t', start);
			if (separator > start && separator < end && separator + 1 < end) {
				auto unescape = [](const std::string& field) {
					std::string out;
					for (size_t i = 0; i < field.size(); ++i) {
						if (field[i] == '\\' && i + 1 < field.size()) {
							if (field[i+1] == 'n') { out += '\n'; ++i; continue; }
							if (field[i+1] == '\\') { out += '\\'; ++i; continue; }
						}
						out += field[i];
					}
					return out;
				};
				std::string value = unescape(contents.substr(separator + 1, end - separator - 1));
				if (ST_UTF8Valid(value.c_str()))
					catalog.emplace(unescape(contents.substr(start, separator - start)), std::move(value));
			}
			start = end + 1;
		}
	}
	return catalog;
}

const char *STML_Translate(const char *text) {
	if (!text || !*text || stMenuLanguageRaw)
		return text;
	const auto& catalog = STML_Catalog();
	const auto match = catalog.find(text);
	return match == catalog.end() ? text : match->second.c_str();
}

static std::string STML_FormatNumbers(const char *text, std::initializer_list<int> numbers) {
	std::string result = STML_Translate(text);
	size_t offset = 0;
	for (int number : numbers) {
		offset = result.find("%d", offset);
		if (offset == std::string::npos)
			return result;
		const std::string digits = std::to_string(number);
		result.replace(offset, 2, digits);
		offset += digits.size();
	}
	return result;
}

const char *STML_Reference(const char *reference, const char *fallback) {
	const auto& catalog = STML_Catalog();
	const auto match = catalog.find(reference);
	return match == catalog.end() ? fallback : match->second.c_str();
}

static bool STML_UTF8(const char *text) {
	if (!text)
		return false;
	for (const char *p = text; *p; ++p)
		if ((unsigned char)*p >= 128)
			return ST_UTF8Valid(text) != 0;
	return false;
}

static float STML_Width(const char *text, float scale) {
	return trap->MenuText && STML_UTF8(text) ? trap->MenuText(text, scale, 0, 0, nullptr) : 0;
}

static bool STML_Draw(float x, float y, float scale, const char *text, const float *color) {
	return trap->MenuText && STML_UTF8(text) && trap->MenuText(text, scale, x, y, color) > 0;
}

// The original StringEd wrapper counts legacy multibyte encodings. Use full
// UTF-8 scalars for catalog paragraphs, preferring the last space when present.
std::vector<std::string> STML_Lines(const char *text, float width, float scale, int font) {
	std::vector<std::string> lines;
	for (const char *start = text; *start && lines.size() < 128;) {
		const char *end = start;
		const char *space = nullptr;
		while (*end && *end != '\n') {
			if (*end == ' ')
				space = end;
			int bytes;
			ST_UTF8Read(end, &bytes);
			const char *next = end + bytes;
			const std::string trial(start, next);
			const float unicodeWidth = STML_Width(trial.c_str(), scale);
			const float trialWidth = unicodeWidth > 0 ? unicodeWidth :
				trap->R_Font_StrLenPixels(trial.c_str(), font, scale);
			if (end != start && trialWidth > width) {
				if (space && space > start)
					end = space;
				break;
			}
			end = next;
		}
		lines.emplace_back(start, end);
		start = end;
		if (*start == '\n')
			++start;
		else
			while (*start == ' ')
				++start;
	}
	return lines;
}
