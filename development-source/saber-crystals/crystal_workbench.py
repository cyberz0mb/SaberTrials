import shutil


def patch(source, path, insert):
    shutil.copyfile(source/'ui_st_crystal_controls.inc', path.parent/'ui_st_crystal_controls.inc')
    insert(path, 'SWB_Hilt, SWB_Color, SWB_Ignite', 'SWB_Hilt, SWB_Color, SWB_Blade, SWB_Channel, SWB_Hex, SWB_ResetRgb, SWB_WhiteCore, SWB_Ignite')
    insert(path, '"ui_saber", "ui_saber2", "ui_saber_color", "ui_saber2_color", "ui_saberHand", "ui_saber_type"',
           '"ui_saber", "ui_saber2", "ui_saber_color", "ui_saber2_color", "ui_saberHand", "ui_saber_type",\n\tstCrystalDrafts[0], stCrystalDrafts[1], ST_WHITE_CORE_DRAFT')
    insert(path, 'static constexpr int swbRows = 9;', 'static constexpr int swbRows = 9;\nstatic constexpr int swbSettingCount = ARRAY_LEN(swbCvars);')
    insert(path, 'int scroll, focus;', 'int scroll, focus, blade, channelDrag;\n\tbool hexEditing;\n\tchar hex[7];')
    insert(path, 'saved[6][MAX_QPATH], childDraft[6][MAX_QPATH]', 'saved[swbSettingCount][MAX_QPATH], childDraft[swbSettingCount][MAX_QPATH]')
    s=path.read_text()
    s=s.replace('(&snapshot)[6]', '(&snapshot)[swbSettingCount]').replace('i < 6; ++i)\n\t\ttrap', 'i < swbSettingCount; ++i)\n\t\ttrap')
    s=s.replace('char draft[6][MAX_QPATH];','char draft[swbSettingCount][MAX_QPATH];')
    s=s.replace('i < 5; ++i)\n\t\tif (Q_stricmp(draft[i], swb.saved[i]))','i < swbSettingCount; ++i)\n\t\tif (i != 5 && Q_stricmp(draft[i], swb.saved[i]))')
    a=s.index('static const struct {\n\tconst char *name;\n\tvec4_t rgb;')
    b=s.index('static bool SWB_Paint()',a)
    s=s[:a]+'#include "ui_st_crystal_controls.inc"\n\n'+s[b:]
    path.write_text(s)
    insert(path, '''	UI_FillRect(323, 359, 86, 2, ruWhite);
	UI_FillRect(322 + 86 * (swb.angle + 25) / 50.f, 354, 6, 12, angleFocus ? ruCyan : ruGold);''',
           '''	SWB_DrawSlider(323, 360, 86, (swb.angle + 25.f) / 50.f, ruGold, angleFocus);''')
    insert(path, '\tswb.focus = -1;\n\tSWB_Read(swb.saved);', '''	swb.focus = -1;
	swb.channelDrag = -1;
	for (int saber = 0; saber < 2; ++saber) {
		char saved[ST_CRYSTAL_TEXT_SIZE + 1];
		int colors[MAX_BLADES];
		trap->Cvar_VariableStringBuffer(stCrystalCvars[saber], saved, sizeof(saved));
		ST_CrystalParse(saved, colors);
		char normalized[ST_CRYSTAL_TEXT_SIZE];
		ST_CrystalFormat(colors, normalized);
		trap->Cvar_Set(stCrystalDrafts[saber], normalized);
	}
	trap->Cvar_Set(ST_WHITE_CORE_DRAFT, trap->Cvar_VariableValue(ST_WHITE_CORE_CVAR) != 0 ? "1" : "0");
	SWB_Read(swb.saved);''')
    insert(path, '\tif (apply)\n\t\tUI_UpdateSaberCvars();\n\telse\n\t\tSWB_Restore(swb.saved);', '''	if (apply) {
		UI_UpdateSaberCvars();
		for (int saber = 0; saber < 2; ++saber)
			trap->Cvar_Set(stCrystalCvars[saber], UI_Cvar_VariableString(stCrystalDrafts[saber]));
		trap->Cvar_Set(ST_WHITE_CORE_CVAR, UI_Cvar_VariableString(ST_WHITE_CORE_DRAFT));
	} else {
		SWB_Restore(swb.saved);
	}''')
    insert(path, '\tswb.second = false;\n\tSWB_Filter();', '\tswb.second = false;\n\tswb.blade = 0;\n\tSWB_Filter();')
    insert(path, '\tswb.searching = false;\n\tswitch (control.action)', '\tswb.searching = false;\n\tswb.hexEditing = false;\n\tswitch (control.action)')
    insert(path, 'case SWB_Cancel: SWB_Restore(swb.saved); swb.second = false; SWB_Filter(); break;',
           'case SWB_Cancel: SWB_Restore(swb.saved); swb.second = false; swb.blade = 0; SWB_Filter(); break;')
    insert(path, 'case SWB_Slot: swb.second = control.value != 0; break;',
           'case SWB_Slot: swb.second = control.value != 0; swb.blade = 0; break;')
    insert(path, '\t\tUI_UpdateSaberHilt(swb.second ? qtrue : qfalse);\n\t\tbreak;',
           '\t\tUI_UpdateSaberHilt(swb.second ? qtrue : qfalse);\n\t\tswb.blade = 0;\n\t\tbreak;')
    insert(path, '''	case SWB_Color:
		trap->Cvar_Set(swb.second ? "ui_saber2_color" : "ui_saber_color", swbColors[control.value].name);
		break;''', '''	case SWB_Color: SWB_SetPreset(control.value); break;
	case SWB_Blade: {
		const int count = SWB_BladeCount();
		swb.blade = (swb.blade + count + control.value) % count;
		break;
	}
	case SWB_Channel: SWB_SetChannel(control.value, (ST_CrystalChannel(SWB_CurrentRgb(), control.value) + 5) % 256); break;
	case SWB_Hex: swb.hexEditing = true; swb.hex[0] = '\\0'; break;
	case SWB_ResetRgb: SWB_StoreRgb(ST_CRYSTAL_DEFAULT, false); break;''')
    insert(path, 'case SWB_ResetRgb: SWB_StoreRgb(ST_CRYSTAL_DEFAULT, false); break;', '''case SWB_ResetRgb: SWB_StoreRgb(ST_CRYSTAL_DEFAULT, false); break;
	case SWB_WhiteCore:
		trap->Cvar_Set(ST_WHITE_CORE_DRAFT, trap->Cvar_VariableValue(ST_WHITE_CORE_DRAFT) != 0 ? "0" : "1");
		break;''')
    insert(path, 'static bool SWB_Mouse()\n{\n\tif (!SWI_Menu(Menu_GetFocused()))\n\t\treturn false;',
           'static bool SWB_Mouse()\n{\n\tif (!SWI_Menu(Menu_GetFocused()))\n\t\treturn false;\n\tif (swb.menu != Menu_GetFocused())\n\t\treturn true;')
    insert(path, '\tif (swb.angleDrag)\n\t\tSWB_SetAngle();',
           '\tif (swb.angleDrag)\n\t\tSWB_SetAngle();\n\tif (swb.channelDrag >= 0)\n\t\tSWB_DragChannel(swb.channelDrag);')
    insert(path, '\t\tif (key == A_MOUSE1)\n\t\t\tswb.angleDrag = swb.scrollDrag = false;',
           '\t\tif (key == A_MOUSE1) {\n\t\t\tswb.angleDrag = swb.scrollDrag = false;\n\t\t\tswb.channelDrag = -1;\n\t\t}')
    insert(path, '\tSWB_Start(menu);\n\tif (key == A_ESCAPE', '\tSWB_Start(menu);\n\tif (SWB_HexKey(key)) return true;\n\tif (key == A_ESCAPE')
    insert(path, '\t} else if (key == A_MOUSE1) {\n\t\tswb.searching = false;',
           '\t} else if (key == A_MOUSE1) {\n\t\tswb.searching = false;\n\t\tswb.hexEditing = false;')
    insert(path, '''						SWB_SetAngle();
					} else
						SWB_Activate(menu, control);''', '''						SWB_SetAngle();
					} else if (control.action == SWB_Channel) {
						swb.channelDrag = control.value;
						SWB_DragChannel(control.value);
					} else {
						SWB_Activate(menu, control);
					}''')
    insert(path, '\t} else if ((key == A_ENTER || key == A_JOY0) && swb.searching) {', '''	} else if ((key == A_CURSOR_LEFT || key == A_CURSOR_RIGHT || key == A_JOY13 || key == A_JOY14) &&
		swb.focus >= 0 && swb.focus < (int)swbControls.size() && swbControls[swb.focus].action == SWB_Channel) {
		const int channel = swbControls[swb.focus].value;
		const int step = key == A_CURSOR_LEFT || key == A_JOY13 ? -5 : 5;
		SWB_SetChannel(channel, ST_CrystalChannel(SWB_CurrentRgb(), channel) + step);
	} else if ((key == A_ENTER || key == A_JOY0) && swb.searching) {''')
