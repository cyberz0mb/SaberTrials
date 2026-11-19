# Profile-first bot dialogue

`overlay.py` applies this server-only change to the combined Weapon DLC game
source. It preserves the independent combat roles, assists/K/D, sabers and
weapon changes. The installed translator engine, cgame, UI, renderers and
model packages are protected by the installation receipt.

`ai_st_chat.inc` contains the shared event selection and Trickster precedence
policy. `st_bot_profile.h` accepts DLC settings groups with extra blank lines
and different line endings. The overlay also removes cancellation of queued remarks when an enemy
becomes visible, clears stale chat on profile load, and reads chat regardless
of host menu language. Only `ai_main.c`, `ai_main.h` and `ai_util.c` change;
the two includes are the only added gameplay source files.

From the repository root, with the existing Windows build dependencies:

```powershell
python tools/Build-Bot-Chat.py prepare
python tools/Build-Bot-Chat.py test
python tools/Build-Bot-Chat.py build
python tools/Check-Bot-Chat.py
python tools/Build-Bot-Chat.py validate
python tools/Build-Bot-Chat.py install
python tools/Check-Bot-Chat.py --installed
```

See [Bot roles](../../docs/BOT_ROLES.md#character-dialogue-and-dlc-priority)
for the DLC authoring contract.
