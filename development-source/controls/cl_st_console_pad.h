#ifndef CL_ST_CONSOLE_PAD_H
#define CL_ST_CONSOLE_PAD_H

bool Con_PadKeyboardActive();
void Con_OpenPadKeyboard();
void Con_ClosePadKeyboard();
void Con_PadKeyboardMove(int dx,int dy);
void Con_PadKeyboardButton(int button,int confirm);
void Con_DrawPadKeyboard();
bool Con_AutoKeyboard(bool gamepad);
void Con_SetPadKeyboard(int catcher);
void Con_UpdatePadKeyboard(int catcher);
void Con_PadKeyboardMouseClick();

#endif
