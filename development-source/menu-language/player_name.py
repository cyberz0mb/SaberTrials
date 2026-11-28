"""Preserve complete UTF-8 Latin letters when cleaning multiplayer display names."""
from pathlib import Path
import shutil


def apply(source):
    shared = Path(source) / "codemp/qcommon/st_utf8.h"
    if not shared.exists():
        shutil.copyfile(Path(__file__).resolve().parents[1] / "translator/st_utf8.h", shared)
    path = Path(source) / "codemp/game/g_client.c"
    text = path.read_text(encoding="utf8")
    if "ST_UTF8Read(in, &bytes)" in text:
        return
    start = text.index("static void ClientCleanName(")
    pos = text.index("\t\tout[outpos] = *in;", start)
    text = text[:pos] + """		// Treat accented Latin letters as one character before the legacy byte filter.
		if ((byte)*in >= 0xc2) {
			int bytes;
			const unsigned cp = ST_UTF8Read(in, &bytes);
			if (bytes > 1 && cp >= 0x00c0 && cp <= 0x024f) {
				if (outpos + bytes >= outSize) break;
				memcpy(out + outpos, in, bytes);
				outpos += bytes;
				in += bytes - 1;
				spaces = ats = 0;
				colorlessLen++;
				continue;
			}
		}
""" + text[pos:]
    text = text.replace('#include "g_local.h"', '#include "g_local.h"\n#include "qcommon/st_utf8.h"', 1)
    path.write_text(text, encoding="utf8", newline="\n")


if __name__ == "__main__":
    import sys
    apply(sys.argv[1])
