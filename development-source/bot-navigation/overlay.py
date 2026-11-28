"""Layer Berserker navigation over the current combined game source."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Berserker navigation anchor changed: ' + old[:100])
    return text.replace(old, new)


def apply(root):
    game = Path(root) / 'codemp/game'
    path = game / 'ai_main.h'
    text = path.read_text()
    text = replace(text, '#include "bg_saga.h"',
                   '#include "bg_saga.h"\n#include "st_berserker_state.h"')
    text = replace(text, '\tchar\t\t\t\tforceinfo[MAX_FORCE_INFO_SIZE];',
                   '\tstBerserkerNav_t stBerserker;\n\n\tchar\t\t\t\tforceinfo[MAX_FORCE_INFO_SIZE];')
    path.write_text(text)
    path = game / 'ai_main.c'
    text = path.read_text()
    text = replace(text, 'static void ST_BotPrepareRole( bot_state_t *bs ) {',
                   '#include "ai_st_berserker.inc"\n\nstatic void ST_BotPrepareRole( bot_state_t *bs ) {')
    text = replace(text, '\tint role = ST_BotEffectiveRole( bs );\n\tif ( role == ST_BOT_ROLE_DEFENDER',
                   '\tint role = ST_BotEffectiveRole( bs );\n\tST_BerserkerPrepare(bs);\n\tif ( role == ST_BOT_ROLE_DEFENDER')
    text = replace(text, '''\t\tif ( !ucmd->forwardmove && !ucmd->rightmove )
\t\t\tucmd->forwardmove = 127;''', '\t\tST_BerserkerCommand(bs, ucmd);')
    text = replace(text, '\tStandardBotAI(bs, thinktime);',
                   '\tStandardBotAI(bs, thinktime);\n\tST_BerserkerNavigate(bs);')
    text = replace(text, '\t\twp = GetNearestVisibleWP(bs->origin, bs->client);',
                   '\t\twp = ST_BerserkerWaypoint(bs, GetNearestVisibleWP(bs->origin, bs->client));')
    text = replace(text, '\tdistChange = 0; //keep the compiler from complaining',
                   '\tif (ST_BerserkerDestination(bs)) return;\n\n\tdistChange = 0; //keep the compiler from complaining')
    text = replace(text, '''int BotIsAChickenWuss(bot_state_t *bs)
{
\tint bWRange;''', '''int BotIsAChickenWuss(bot_state_t *bs)
{
\tint bWRange;
\t// Berserkers commit to the pursuit instead of alternating flee/chase goals.
\tif (ST_BotEffectiveRole(bs) == ST_BOT_ROLE_BERSERKER) return 0;''')
    path.write_text(text)
    path = game / 'g_svcmds.c'
    text = path.read_text()
    text = replace(text, 'svcmd_t svcmds[] = {',
        'void Svcmd_STBotNav_f(void);\n\nsvcmd_t svcmds[] = {\n\t{ "st_botnav", Svcmd_STBotNav_f, qfalse },')
    path.write_text(text)
    for name in ('ai_st_berserker.inc', 'st_berserker_state.h'):
        shutil.copyfile(HERE / name, game / name)
