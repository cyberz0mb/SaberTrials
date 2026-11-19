"""Apply profile-first bot chat without replacing the current gameplay tree."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace(text, old, new):
    assert text.count(old) == 1, 'Bot chat patch anchor changed: ' + old[:100]
    return text.replace(old, new)


def apply(root):
    game = Path(root)/'codemp/game'
    path = game/'ai_util.c'
    text = path.read_text()
    start = text.index('int GetValueGroup(')
    end = text.index('int BotDoChat(', start)
    text = text[:start] + '''#include "st_bot_profile.h"

int GetValueGroup(char *buf, char *group, char *outbuf)
{
    return ST_ProfileGroup(buf, group, outbuf, 65536);
}

int GetPairedValue(char *buf, char *key, char *outbuf)
{
    return ST_ProfileValue(buf, key, outbuf, 1024);
}

''' + text[end:]
    start = text.index('int BotDoChat(')
    end = text.index('void ParseEmotionalAttachments(', start)
    text = text[:start] + '#include "ai_st_chat.inc"\n\n' + text[end:]
    start = text.index('int ReadChatGroups(')
    end = text.index('void BotUtilizePersonality(', start)
    text = text[:start] + '''int ReadChatGroups(bot_state_t *bs, char *buf)
{
    const char *begin = strstr(buf, "BEGIN_CHAT_GROUPS");
    gBotChatBuffer[bs->client][0] = '\\0';
    if (!begin) return 0;
    begin += strlen("BEGIN_CHAT_GROUPS");
    if (strlen(begin) >= MAX_CHAT_BUFFER_SIZE) {
        trap->Print(S_COLOR_RED "Error: Personality chat section exceeds max size\\n");
        return 0;
    }
    Q_strncpyz(gBotChatBuffer[bs->client], begin, MAX_CHAT_BUFFER_SIZE);
    return ST_ChatLines(gBotChatBuffer[bs->client], NULL, -1, NULL, 0) > 0;
}

''' + text[end:]
    text = replace(text, '\tlen = trap->FS_Open(bs->settings.personalityfile, &f, FS_READ);',
        '''\t// A reused client slot must never inherit the previous model's dialogue.
\tgBotChatBuffer[bs->client][0] = '\\0';
\tbs->canChat = 0;
\tbs->doChat = 0;
\tlen = trap->FS_Open(bs->settings.personalityfile, &f, FS_READ);''')
    text = replace(text, '''\tif (bs->canChat)
\t{
\t\tif (!ReadChatGroups(bs, buf))
\t\t{
\t\t\tbs->canChat = 0;
\t\t}
\t}''', '''\t// Keep authored dialogue even when chatability is explicitly disabled,
\t// so role chatter cannot override that personality's silence.
\tif (!ReadChatGroups(bs, buf)) bs->canChat = 0;''')
    path.write_text(text)
    path = game/'ai_main.c'
    text = path.read_text()
    start = text.index('static void ST_BotTricksterChat(')
    end = text.index('static void ST_BotApplyTrickster(', start)
    text = text[:start] + text[end:]
    text = replace(text, '''\telse if (bs->doChat && bs->currentEnemy && bs->frame_Enemy_Vis)
\t{
\t\t//bs->chatTime = level.time + bs->chatTime_stored;
\t\tbs->doChat = 0; //do we want to keep the bot waiting to chat until after the enemy is gone?
\t\tbs->chatTeam = 0;
\t}
''', '')
    path.write_text(text)
    path = game/'ai_main.h'
    text = path.read_text()
    text = replace(text, 'int BotDoChat(bot_state_t *bs, char *section, int always);',
        'int BotDoChat(bot_state_t *bs, char *section, int always);\nvoid ST_BotTricksterChat(bot_state_t *bs);')
    path.write_text(text)
    shutil.copyfile(HERE/'ai_st_chat.inc', game/'ai_st_chat.inc')
    shutil.copyfile(HERE/'st_bot_profile.h', game/'st_bot_profile.h')
