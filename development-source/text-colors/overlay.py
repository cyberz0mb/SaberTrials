"""Add ten-color entry and saved outgoing chat color to the combined client."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Text color anchor changed: ' + old[:100])
    return text.replace(old, new)


def catalogue(path):
    text = path.read_text()
    entry = next(line for line in (SOURCE / 'setup/st_setup_catalog.h').read_text().splitlines()
                 if line.startswith(' {"st_chatColor",'))
    lines = text.splitlines(keepends=True)
    assert '"st_chatColor"' not in text
    matches = [i for i, line in enumerate(lines) if line.startswith(' {"st_chatOpacity",')]
    assert len(matches) == 1
    lines.insert(matches[0]+1, entry+'\n')
    path.write_text(''.join(lines))


def engine(root):
    root = Path(root)
    client = root / 'codemp/client'
    catalogue(root / 'codemp/ui/st_setup_catalog.h')
    shutil.copyfile(HERE / 'cl_st_chat_color.h', client / 'cl_st_chat_color.h')
    shutil.copyfile(SOURCE / 'translator/st_chat_raster.h', client / 'st_chat_raster.h')
    path = client / 'cl_keys.cpp'
    text = path.read_text()
    text = replace(text, '#include "cl_st_console_pad.h"',
                   '#include "cl_st_console_pad.h"\n#include "cl_st_chat_color.h"')
    start = text.index('void Message_Key( int key ) {')
    end = text.index('//============================================================================', start)
    block = text[start:end]
    block = replace(block, 'if ( chatField.buffer[0] && cls.state == CA_ACTIVE ) {',
                    'if ( chatField.buffer[0] && cls.state == CA_ACTIVE ) {\n'
                    '            const std::string colored = ST_ChatColorized(chatField.buffer);')
    assert block.count(', chatField.buffer );') == 3
    block = block.replace(', chatField.buffer );', ', colored.c_str() );')
    path.write_text(text[:start]+block+text[end:])
    path = client / 'cl_st_chat_input.inc'
    text = replace(path.read_text(), 'if(length-remove+count>=MAX_SAY_TEXT)return;',
                   'if(length-remove+count>ST_ChatTextLimit())return;')
    path.write_text(text)
    path = client / 'cl_st_chat_text.inc'
    text = replace(path.read_text(), '#include "st_chat_raster.h"',
                   '#include "st_chat_raster.h"\n#include "cl_st_chat_color.h"')
    text = replace(text, '    stChatLayoutRequest_t request={31,shown,',
                   '    const std::string colored=ST_ChatColorPrefix()+shown;\n'
                   '    stChatLayoutRequest_t request={31,colored.c_str(),')
    path.write_text(text)


def frontend(root):
    ui = Path(root) / 'codemp/ui'
    catalogue(ui / 'st_setup_catalog.h')
    shutil.copyfile(SOURCE / 'profile/ui_st_name_keyboard.inc', ui / 'ui_st_name_keyboard.inc')
    shutil.copyfile(SOURCE / 'setup/ui_st_chat_preview.inc', ui / 'ui_st_chat_preview.inc')
    remove_black_outline(ui / 'ui_st_rich.inc')


def remove_black_outline(path):
    """Remove the prior menu rim when updating an already colored UI tree."""
    path = Path(path)
    text = path.read_text()
    outline = '''  if(c[0]==0&&c[1]==0&&c[2]==0){
   const vec4_t rim={.63f,.74f,.79f,c[3]*.82f};trap->R_SetColor(rim);
   for(int dy=-1;dy<=1;++dy)for(int dx=-1;dx<=1;++dx)if(dx||dy)
    trap->R_DrawStretchPic(x-6*unit*aspect+dx*.35f*aspect,y-3*unit+dy*.35f,64*unit*aspect,80*unit,u,v,u+64.f/1024,v+80.f/1024,shader);
   trap->R_SetColor(c);
  }
'''
    if outline in text:
        path.write_text(replace(text, outline, ''))
    else:
        assert 'if(c[0]==0&&c[1]==0&&c[2]==0)' not in text, 'Unrecognized black-text outline'
