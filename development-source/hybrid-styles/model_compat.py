"""In-memory humanoid animation extension for private facial GLAs.

Only the engine owns Ghoul2 loaders. Never modify an installed model package.
"""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def apply(root, kind):
    if kind != 'engine':
        return
    root = Path(root)
    shutil.copy2(HERE / 'st_gla_compat.h', root / 'codemp/ghoul2/st_gla_compat.h')
    for renderer in ('rd-vanilla', 'rd-dedicated'):
        path = root / 'codemp' / renderer / 'tr_model.cpp'
        text = path.read_text(encoding='utf-8')
        hook = '\t\tri.FS_ReadFile( sModelName, ppvBuffer );'
        replacement = '\t\tint stFileBytes = ri.FS_ReadFile( sModelName, ppvBuffer );\n\t\tST_GLA_CompatRead(sModelName, ppvBuffer, stFileBytes);'
        if text.count(hook) != 1:
            raise ValueError(f'Private GLA loader hook changed: {path}')
        text = text.replace(hook, replacement)
        marker = 'qboolean RE_RegisterModels_GetDiskFile('
        if text.count(marker) != 1:
            raise ValueError(f'Private GLA include hook changed: {path}')
        text = text.replace(marker, '#define ST_GLA_COMPAT_ENGINE\n#include "../ghoul2/st_gla_compat.h"\n\n' + marker)
        path.write_text(text, encoding='utf-8', newline='\n')
    path = root / 'codemp/rd-rend2/tr_cache.cpp'
    text = path.read_text(encoding='utf-8')
    hook = '\tint len = ri.FS_ReadFile(path, ppFileBuffer);'
    marker = 'qboolean CModelCacheManager::LoadFile('
    if text.count(hook) != 1 or text.count(marker) != 1:
        raise ValueError(f'Private GLA Rend2 loader hook changed: {path}')
    text = text.replace(hook, hook + '\n\tST_GLA_CompatRead(path, ppFileBuffer, len);')
    text = text.replace(marker, '#define ST_GLA_COMPAT_ENGINE\n#include "../ghoul2/st_gla_compat.h"\n\n' + marker)
    path.write_text(text, encoding='utf-8', newline='\n')
