// Selected-character preview for the main Profile grid. GPL-2.0-only.
// Uses its own Ghoul2 instance; never changes the selected model or game state.
static void ST_UIProfileNameField( menuDef_t *menu ) {
	itemDef_t *field = Menu_FindItemByName(menu,"namefield");
	char value[256], label[128];
	float width, scale;
	if ( !field ) return;
	trap->Cvar_VariableStringBuffer("ui_Name",value,sizeof(value));
	trap->SE_GetStringTextString("MENUS_NAME1",label,sizeof(label));
	width = uiInfo.uiDC.textWidth(value,0.9f,field->iMenuFont) +
		uiInfo.uiDC.textWidth(label,0.9f,field->iMenuFont);
	scale = width > field->window.rect.w-24 ? 0.9f*(field->window.rect.w-24)/width : 0.9f;
	// Fit long display names without shortening the stored name or changing other fields.
	if ( field->textscale != scale ) {
		field->textscale = scale;
		field->textRect.w = 0;
	}
}

static void ST_UIProfilePreview( menuDef_t *menu ) {
	static itemDef_t *cachedItem;
	static char cachedSelection[MAX_QPATH];
	static qboolean loaded;
	itemDef_t *item;
	modelDef_t *preview;
	char selection[MAX_QPATH], model[MAX_QPATH], path[MAX_QPATH*2];
	char *skin;
	int duration;

	if ( !menu || Q_stricmp( menu->window.name, "playerMenu" ) ) {
		cachedItem = NULL;
		return;
	}
	ST_UIProfileNameField(menu);
	item = Menu_FindItemByName( menu, "st_profile_preview" );
	if ( !item || item->type != ITEM_TYPE_MODEL || !item->typeData.model ) return;
	preview = item->typeData.model;
	// Preserve the model's proportions when the legacy 640x480 menu is stretched.
	// Match horizontal field of view to the actual pixel viewport, not menu units.
	if ( item->window.rect.w > 2 && item->window.rect.h > 2 && uiInfo.uiDC.yscale > 0 ) {
		float aspect = ((item->window.rect.w-2)*uiInfo.uiDC.xscale) /
			((item->window.rect.h-2)*uiInfo.uiDC.yscale);
		preview->fov_x = (float)(atan(tan(preview->fov_y*M_PI/360.0)*aspect)*360.0/M_PI);
	}
	trap->Cvar_VariableStringBuffer( "model", selection, sizeof(selection) );
	if ( !selection[0] ) Q_strncpyz( selection, "kyle/default", sizeof(selection) );

	// The UI renderer's character tint comes from these presentation cvars.
	// Leave ui_char_model/skin and all saved character settings untouched.
	trap->Cvar_Set( "ui_char_color_red", UI_Cvar_VariableString("char_color_red") );
	trap->Cvar_Set( "ui_char_color_green", UI_Cvar_VariableString("char_color_green") );
	trap->Cvar_Set( "ui_char_color_blue", UI_Cvar_VariableString("char_color_blue") );
	trap->Cvar_Update( &ui_char_color_red );
	trap->Cvar_Update( &ui_char_color_green );
	trap->Cvar_Update( &ui_char_color_blue );

	// Only reload when selection changes. Reinitializing every frame would
	// restart the walk instead of allowing the animation to loop.
	if ( cachedItem == item && !strcmp(cachedSelection,selection) && (!loaded || item->ghoul2) ) return;
	cachedItem = item;
	Q_strncpyz( cachedSelection, selection, sizeof(cachedSelection) );
	Q_strncpyz( model, selection, sizeof(model) );
	skin = strchr(model,'/');
	if ( skin ) *skin++ = '\0';
	else skin = "default";

	preview->g2skin = 0;
	if ( strchr(skin,'|') ) {
		Com_sprintf( path, sizeof(path), "models/players/%s/|%s", model, skin );
	} else {
		Com_sprintf( path, sizeof(path), "models/players/%s/model_%s.skin", model, skin );
	}
	preview->g2skin = trap->R_RegisterSkin( path );
	preview->g2anim = BOTH_WALK1;
	preview->rotationSpeed = 100; // milliseconds per degree: 36 seconds per turn.
	preview->angle = (int)AngleNormalize360(180.0f-(float)uiInfo.uiDC.realTime/100.0f);
	Com_sprintf( path, sizeof(path), "models/players/%s/model.glm", model );
	ItemParse_asset_model_go( item, path, &duration );
	loaded = item->ghoul2 && (item->flags & ITF_G2VALID);
	trap->Cvar_Set( "ui_stProfilePreviewAvailable", loaded ? "1" : "0" );
}
