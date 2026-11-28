/*
===========================================================================
Copyright (C) 1999 - 2005, Id Software, Inc.
Copyright (C) 2000 - 2013, Raven Software, Inc.
Copyright (C) 2001 - 2013, Activision, Inc.
Copyright (C) 2013 - 2015, OpenJK contributors

This file is part of the OpenJK source code.

OpenJK is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see <http://www.gnu.org/licenses/>.
===========================================================================
*/
// Adapted from TaystJK codemp/cgame/cg_draw.c and cg_main.c (GPL-2.0).
// The Elegance layout is by DarthNormaN. Art and layout credits are in CREDITS.txt.
static float stHudRatio;
static const int stHudQuake=5;
static int stSelectedHud;
static const char *st_healthTicName[MAX_HUD_TICS*2] =
{
"health_tic1",
"health_tic2",
"health_tic3",
"health_tic4",
"health_tic5",
"health_tic6",
"health_tic7",
"health_tic8",

};
static const char *st_armorTicName[MAX_HUD_TICS*2] =
{
"armor_tic1",
"armor_tic2",
"armor_tic3",
"armor_tic4",
"armor_tic5",
"armor_tic6",
"armor_tic7",
"armor_tic8",
};
typedef struct {float x,y,width,height; const char *file; qhandle_t tic;} stHudTick_t;
#define ST_JK2_TICS 14
static stHudTick_t st_forceTicPos[] =
{
    { 11,  41,  20,  10, "st_huds/jk2/force_tick1", 0},		// Left Top
    {12,  45,  20,  10, "st_huds/jk2/force_tick2", 0},
    {14,  49,  20,  10, "st_huds/jk2/force_tick3", 0},
    {17,  52,  20,  10, "st_huds/jk2/force_tick4", 0},
    {22,  55,  10,  10, "st_huds/jk2/force_tick5", 0},
    {28,  57,  10,  20, "st_huds/jk2/force_tick6", 0},
    {34,  59,  10,  10,	"st_huds/jk2/force_tick7", 0},		// Left bottom
    {46, 59, -10,  	10,"st_huds/jk2/force_tick7",0},		// Right bottom
    {52,57,-10 ,20,"st_huds/jk2/force_tick6",0},
    {58 ,55,-10 ,10,"st_huds/jk2/force_tick5",0},
    {63 ,52,-20 ,10,"st_huds/jk2/force_tick4",0},
    {66 ,49,-20 ,10,"st_huds/jk2/force_tick3",0},
    {68 ,45,-20 ,10,"st_huds/jk2/force_tick2",0},
    {69 ,41,-20 ,10,"st_huds/jk2/force_tick1",0}		// Right top
};
static stHudTick_t st_ammoTicPos[] =
{
	{12,  34,  10,  10, "st_huds/jk2/ammo_tick7", 0},	// Bottom
	{13,  28,  10,  10, "st_huds/jk2/ammo_tick6", 0},
	{15,  23,  10,  10, "st_huds/jk2/ammo_tick5", 0},
	{19,  19,  10,  10, "st_huds/jk2/ammo_tick4", 0},
	{23,  15,  10,  10, "st_huds/jk2/ammo_tick3", 0},
	{29, 12 ,10 ,10 ,"st_huds/jk2/ammo_tick2",0},
	{34 ,11 ,10 ,10 ,"st_huds/jk2/ammo_tick1",0},

	{47 ,11 ,-10 ,10 ,"st_huds/jk2/ammo_tick1",0},
	{52 ,12 ,-10 ,10 ,"st_huds/jk2/ammo_tick2",0},
	{58 ,15 ,-10 ,10 ,"st_huds/jk2/ammo_tick3",0},
	{62 ,19 ,-10 ,10 ,"st_huds/jk2/ammo_tick4",0},
	{66 ,23 ,-10 ,10 ,"st_huds/jk2/ammo_tick5",0},
	{68 ,28 ,-10 ,10 ,"st_huds/jk2/ammo_tick6",0},
	{69 ,34 ,-10 ,10 ,"st_huds/jk2/ammo_tick7",0}
};
static struct {
    qhandle_t JK2HUDLeftFrame;
    qhandle_t JK2HUDInnerLeft;
    qhandle_t JK2HUDArmor1;
    qhandle_t JK2HUDArmor2;
    qhandle_t JK2HUDHealth;
    qhandle_t JK2HUDHealthTic;
    qhandle_t JK2HUDArmorTic;
    qhandle_t JK2HUDSaberStyle1;
    qhandle_t JK2HUDSaberStyle2;
    qhandle_t JK2HUDSaberStyle3;
    qhandle_t JK2HUDSaberStyle4;
    qhandle_t JK2HUDSaberStyle5;
    qhandle_t JK2HUDRightFrame;
    qhandle_t JK2HUDInnerRight;
} stOutcast;
static void ST_RegisterOutcast(void) {
    stOutcast.JK2HUDLeftFrame = trap->R_RegisterShaderNoMip("st_huds/jk2/jk2hudleft");
    stOutcast.JK2HUDInnerLeft = trap->R_RegisterShaderNoMip("st_huds/jk2/jk2hudleft_innerframe");
    stOutcast.JK2HUDArmor1 = trap->R_RegisterShaderNoMip("st_huds/jk2/armor1");
    stOutcast.JK2HUDArmor2 = trap->R_RegisterShaderNoMip("st_huds/jk2/armor2");
    stOutcast.JK2HUDHealth = trap->R_RegisterShaderNoMip("st_huds/jk2/health");
    stOutcast.JK2HUDHealthTic = trap->R_RegisterShaderNoMip("st_huds/jk2/health_tic");
    stOutcast.JK2HUDArmorTic = trap->R_RegisterShaderNoMip("st_huds/jk2/armor_tic");
    stOutcast.JK2HUDSaberStyle1 = trap->R_RegisterShaderNoMip("st_huds/jk2/saber_stylesfast");
    stOutcast.JK2HUDSaberStyle2 = trap->R_RegisterShaderNoMip("st_huds/jk2/saber_stylesmed");
    stOutcast.JK2HUDSaberStyle3 = trap->R_RegisterShaderNoMip("st_huds/jk2/saber_stylesstrong");
    stOutcast.JK2HUDSaberStyle4 = trap->R_RegisterShaderNoMip("st_huds/jk2/saber_stylesstaff");
    stOutcast.JK2HUDSaberStyle5 = trap->R_RegisterShaderNoMip("st_huds/jk2/saber_stylesdual");
    stOutcast.JK2HUDRightFrame = trap->R_RegisterShaderNoMip("st_huds/jk2/jk2hudrightframe");
    stOutcast.JK2HUDInnerRight = trap->R_RegisterShaderNoMip("st_huds/jk2/jk2hudright_innerframe");
    for (int i=0;i<ST_JK2_TICS;++i) {
        st_forceTicPos[i].tic=trap->R_RegisterShaderNoMip(st_forceTicPos[i].file);
        st_ammoTicPos[i].tic=trap->R_RegisterShaderNoMip(st_ammoTicPos[i].file);
    }
}

static void ST_HudHealth( menuDef_t *menuHUD )
{
	vec4_t			calcColor;
	playerState_t	*ps;
	int				healthAmt;
	int				i,currValue,inc;
	itemDef_t		*focusItem;
	float           percent;
    char            numString[8];
    char            numString2[8];

    // Can we find the menu?
	if (!menuHUD)
	{
		return;
	}
	ps = &cg.snap->ps;

	// What's the health?
	healthAmt = ps->stats[STAT_HEALTH];
    currValue = healthAmt;

    inc = ps->stats[STAT_MAX_HEALTH] / MAX_HUD_TICS;

    // Print the health tics, fading out the one which is partial health
    memcpy(calcColor, colorWhite, sizeof(vec4_t));
    for (i = (MAX_HUD_TICS - 1);i>=0;i--){
		focusItem = Menu_FindItemByName(menuHUD, st_healthTicName[i]);

		if (!focusItem)	// This is bad
		{
			continue;
		}

		memcpy(calcColor, colorWhite, sizeof(vec4_t));

		if (currValue <= 0)	// don't show tic
		{
			break;
		} else if (currValue < inc)	// partial tic (alpha it out)
        {
            percent = (float) currValue / (float)inc;
            calcColor[3] *= percent;
        }

		trap->R_SetColor( calcColor);

		CG_DrawPic(
			focusItem->window.rect.x * stHudRatio,
			focusItem->window.rect.y,
			focusItem->window.rect.w * stHudRatio,
			focusItem->window.rect.h,
			focusItem->window.background
			);

		currValue -= inc;
	}

    if(stSelectedHud == stHudQuake && ps->stats[STAT_HEALTH] > ps->stats[STAT_MAX_HEALTH])
    {
        currValue = ps->stats[STAT_HEALTH] - ps->stats[STAT_MAX_HEALTH];
        inc = ps->stats[STAT_MAX_HEALTH] / MAX_HUD_TICS;
        for(i = 2 * MAX_HUD_TICS - 1; i >= MAX_HUD_TICS; i--)
        {
            focusItem = Menu_FindItemByName(menuHUD, st_healthTicName[i]);

            if (!focusItem)	// This is bad
            {
                continue;
            }

            memcpy(calcColor, colorWhite, sizeof(vec4_t));

            if (currValue <= 0)	// don't show tic
            {
                break;
            }
            else if (currValue < inc)	// partial tic (alpha it out)
            {
                percent = (float) currValue / (float)inc;
                calcColor[3] *= percent;
            }

            trap->R_SetColor( calcColor);

            CG_DrawPic(
                    focusItem->window.rect.x * stHudRatio,
                    focusItem->window.rect.y,
                    focusItem->window.rect.w * stHudRatio,
                    focusItem->window.rect.h,
                    focusItem->window.background
            );
            currValue -= inc;
        }
    }


	// Print the mueric amount
	focusItem = Menu_FindItemByName(menuHUD, "healthamount");
	if (focusItem && stSelectedHud != stHudQuake)
	{
		// Print health amount
		trap->R_SetColor( focusItem->window.foreColor );

		CG_DrawNumField (
			focusItem->window.rect.x * stHudRatio,
			focusItem->window.rect.y,
			3,
			ps->stats[STAT_HEALTH],
			focusItem->window.rect.w * stHudRatio,
			focusItem->window.rect.h,
			NUM_FONT_SMALL,
			qfalse);
	} else if (focusItem && stSelectedHud == stHudQuake)
    {
        Com_sprintf(numString, sizeof(numString), "%i", ps->stats[STAT_HEALTH]);
        CG_Text_Paint(focusItem->window.rect.x * stHudRatio, focusItem->window.rect.y, 1.0f, colorWhite, numString, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
        Com_sprintf(numString2, sizeof(numString2), " /%i", ps->stats[STAT_MAX_HEALTH]);
        CG_Text_Paint(focusItem->window.rect.x * stHudRatio + CG_Text_Width(numString, 1.0f, FONT_MEDIUM), focusItem->window.rect.y + CG_Text_Height(numString, 1.0f, FONT_MEDIUM) - CG_Text_Height(numString2, 0.6f, FONT_MEDIUM), 0.6f, colorWhite, numString2, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
    }

}

static void ST_HudArmor( menuDef_t *menuHUD )
{
	vec4_t			calcColor;
	playerState_t	*ps;
	int				maxArmor;
	itemDef_t		*focusItem;
	float			percent,quarterArmor;
	int				i,currValue,inc;
    char            numString[8];

	//ps = &cg.snap->ps;
	ps = &cg.predictedPlayerState;

	// Can we find the menu?
	if (!menuHUD)
	{
		return;
	}

    maxArmor = ps->stats[STAT_MAX_HEALTH];
    currValue = ps->stats[STAT_ARMOR];

    inc = maxArmor / MAX_HUD_TICS;

    // Print the health tics, fading out the one which is partial health

	memcpy(calcColor, colorWhite, sizeof(vec4_t));
	for (i = (MAX_HUD_TICS - 1);i>=0;i--)
	{
		focusItem = Menu_FindItemByName(menuHUD, st_armorTicName[i]);

		if (!focusItem)	// This is bad
		{
			continue;
		}

		memcpy(calcColor, colorWhite, sizeof(vec4_t));

		if (currValue <= 0)	// don't show tic
		{
			break;
		}
		else if (currValue < inc)	// partial tic (alpha it out)
		{
			percent = (float) currValue / (float)inc;
			calcColor[3] *= percent;
		}

		trap->R_SetColor( calcColor);

		if ((i==(MAX_HUD_TICS-1)) && (currValue < inc))
		{
			if (cg.HUDArmorFlag)
			{
				CG_DrawPic(
					focusItem->window.rect.x * stHudRatio,
					focusItem->window.rect.y,
					focusItem->window.rect.w * stHudRatio,
					focusItem->window.rect.h,
					focusItem->window.background
					);
			}
		}
		else
		{
				CG_DrawPic(
					focusItem->window.rect.x * stHudRatio,
					focusItem->window.rect.y,
					focusItem->window.rect.w * stHudRatio,
					focusItem->window.rect.h,
					focusItem->window.background
					);
		}

		currValue -= inc;
	}

    if(stSelectedHud == stHudQuake && ps->stats[STAT_ARMOR] > maxArmor)
    {
        currValue = ps->stats[STAT_ARMOR] - maxArmor;
        inc = maxArmor / MAX_HUD_TICS;
        for(i = 2 * MAX_HUD_TICS - 1; i >= MAX_HUD_TICS; i--)
        {
            focusItem = Menu_FindItemByName(menuHUD, st_armorTicName[i]);

            if (!focusItem)	// This is bad
            {
                continue;
            }

            memcpy(calcColor, colorWhite, sizeof(vec4_t));

            if (currValue <= 0)	// don't show tic
            {
                break;
            }
            else if (currValue < inc)	// partial tic (alpha it out)
            {
                percent = (float) currValue / (float)inc;
                calcColor[3] *= percent;
            }

            trap->R_SetColor( calcColor);

                CG_DrawPic(
                        focusItem->window.rect.x * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            currValue -= inc;
        }
    }

	focusItem = Menu_FindItemByName(menuHUD, "armoramount");
    if(focusItem) {
        if (stSelectedHud != stHudQuake)
        {
            // Print armor amount
            trap->R_SetColor(focusItem->window.foreColor);

            CG_DrawNumField(
                    focusItem->window.rect.x * stHudRatio,
                    focusItem->window.rect.y,
                    3,
                    ps->stats[STAT_ARMOR],
                    focusItem->window.rect.w * stHudRatio,
                    focusItem->window.rect.h,
                    NUM_FONT_SMALL,
                    qfalse);
        } else if (stSelectedHud == stHudQuake){
            Com_sprintf(numString, sizeof(numString), "%i", ps->stats[STAT_ARMOR]);
            CG_Text_Paint(focusItem->window.rect.x * stHudRatio, focusItem->window.rect.y, 1.0f, colorWhite, numString, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
            CG_Text_Paint(focusItem->window.rect.x * stHudRatio + CG_Text_Width(numString, 1.0f, FONT_MEDIUM), focusItem->window.rect.y + CG_Text_Height(numString, 1.0f, FONT_MEDIUM) - CG_Text_Height(numString, 0.6f, FONT_MEDIUM), 0.6f, colorWhite, " /100", 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
        }
    }

	// If armor is low, flash a graphic to warn the player
	if (ps->stats[STAT_ARMOR])	// Is there armor? Draw the HUD Armor TIC
	{
		quarterArmor = (float) (ps->stats[STAT_MAX_HEALTH] / 4.0f);

		// Make tic flash if armor is at 25% of full armor
		if (ps->stats[STAT_ARMOR] < quarterArmor)		// Do whatever the flash timer says
		{
			if (cg.HUDTickFlashTime < cg.time)			// Flip at the same time
			{
				cg.HUDTickFlashTime = cg.time + 400;
				if (cg.HUDArmorFlag)
				{
					cg.HUDArmorFlag = qfalse;
				}
				else
				{
					cg.HUDArmorFlag = qtrue;
				}
			}
		}
		else
		{
			cg.HUDArmorFlag=qtrue;
		}
	}
	else						// No armor? Don't show it.
	{
		cg.HUDArmorFlag=qfalse;
	}

}

static void ST_HudAmmo( centity_t	*cent,menuDef_t *menuHUD)
{
	playerState_t	*ps;
	int				i;
	vec4_t			calcColor;
	float			value=0.0f,inc = 0.0f,percent;
	itemDef_t		*focusItem;
    char            ammoStr[8];
    char            ammoStr2[8];

    ps = &cg.snap->ps;

	// Can we find the menu?
	if (!menuHUD)
	{
		return;
	}

	if (!cent->currentState.weapon ) // We don't have a weapon right now
	{
		return;
	}

	value = ps->ammo[weaponData[cent->currentState.weapon].ammoIndex];
	if (value < 0)	// No ammo
	{
		return;
	}

	//
	// ammo
	//
	if (cg.oldammo < value)
	{
		cg.oldAmmoTime = cg.time + 200;
	}

	cg.oldammo = value;

	focusItem = Menu_FindItemByName(menuHUD, "ammoamount");
	trap->R_SetColor( colorWhite );

	if (weaponData[cent->currentState.weapon].energyPerShot == 0 &&
		weaponData[cent->currentState.weapon].altEnergyPerShot == 0)

	{ //just draw "infinite"
		inc = 8 / MAX_HUD_TICS;
		value = 8;

		focusItem = Menu_FindItemByName(menuHUD, "ammoinfinite");
		trap->R_SetColor( colorWhite );
		if (focusItem)
		{
			CG_DrawProportionalString( SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio, focusItem->window.rect.y, "--", NUM_FONT_SMALL, focusItem->window.foreColor );
		}
	}
	else
	{
		focusItem = Menu_FindItemByName(menuHUD, "ammoamount");

		// Firing or reloading?
		if (( cg.predictedPlayerState.weaponstate == WEAPON_FIRING
			&& cg.predictedPlayerState.weaponTime > 100 ))
		{
			memcpy(calcColor, colorTable[CT_LTGREY], sizeof(vec4_t));
		}
		else
		{
			if ( value > 0 )
			{
				if (cg.oldAmmoTime > cg.time)
				{
					memcpy(calcColor, colorTable[CT_YELLOW], sizeof(vec4_t));
				}
				else
				{
					memcpy(calcColor, focusItem->window.foreColor, sizeof(vec4_t));
				}
			}
			else
			{
				memcpy(calcColor, colorTable[CT_RED], sizeof(vec4_t));
			}
		}


		trap->R_SetColor( calcColor );
		if (focusItem && stSelectedHud != stHudQuake)
		{

			if ( (cent->currentState.eFlags & EF_DOUBLE_AMMO) )
			{
				inc = (float) (ammoData[weaponData[cent->currentState.weapon].ammoIndex].max*2.0f) / MAX_HUD_TICS;
			}
			else
			{
				inc = (float) ammoData[weaponData[cent->currentState.weapon].ammoIndex].max / MAX_HUD_TICS;
			}
			value = ps->ammo[weaponData[cent->currentState.weapon].ammoIndex];

			CG_DrawNumField (
				SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
				focusItem->window.rect.y,
				3,
				value,
				focusItem->window.rect.w * stHudRatio,
				focusItem->window.rect.h,
				NUM_FONT_SMALL,
				qfalse);
		}else if(focusItem && stSelectedHud == stHudQuake){
            if ( (cent->currentState.eFlags & EF_DOUBLE_AMMO) )
            {
                inc = (float) (ammoData[weaponData[cent->currentState.weapon].ammoIndex].max*2.0f) / MAX_HUD_TICS;
            }
            else
            {
                inc = (float) ammoData[weaponData[cent->currentState.weapon].ammoIndex].max / MAX_HUD_TICS;
            }
            value = ps->ammo[weaponData[cent->currentState.weapon].ammoIndex];

            Com_sprintf(ammoStr, sizeof(ammoStr), "%i", ps->ammo[weaponData[cent->currentState.weapon].ammoIndex]);
            Com_sprintf(ammoStr2, sizeof(ammoStr2), " /%i", ammoData[weaponData[cent->currentState.weapon].ammoIndex].max);
            CG_Text_Paint(SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio -  CG_Text_Width(ammoStr, 1.0f, FONT_MEDIUM), focusItem->window.rect.y, 1.0f, colorWhite, ammoStr, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
            CG_Text_Paint(SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio, focusItem->window.rect.y + CG_Text_Height(ammoStr, 1.0f, FONT_MEDIUM) - CG_Text_Height(ammoStr2, 0.6f, FONT_MEDIUM), 0.6f, colorWhite, ammoStr2, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
        }
    }

	trap->R_SetColor( colorWhite );

	// Draw tics
	for (i=MAX_HUD_TICS-1;i>=0;i--)
	{
        if(cent->currentState.weapon == WP_STUN_BATON || cent->currentState.weapon == WP_MELEE || cent->currentState.weapon == WP_SABER)
            break;
		focusItem = Menu_FindItemByName(menuHUD, ammoTicName[i]);

		if (!focusItem)
		{
			continue;
		}

		memcpy(calcColor, colorWhite, sizeof(vec4_t));

		if ( value <= 0 )	// done
		{
			break;
		}
		else if (value < inc)	// partial tic
		{
			percent = value / inc;
			calcColor[3] = percent;
		}

		trap->R_SetColor( calcColor);

		CG_DrawPic(
			SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
			focusItem->window.rect.y,
			focusItem->window.rect.w * stHudRatio,
			focusItem->window.rect.h,
			focusItem->window.background
			);

		value -= inc;
	}
    trap->R_SetColor( colorWhite );
    if(stSelectedHud == stHudQuake){
        switch (cent->currentState.weapon){
            case WP_DISRUPTOR:
            case WP_BOWCASTER:
            case WP_DEMP2:
                focusItem = Menu_FindItemByName(menuHUD, "power_cell_ammo");
                if (!focusItem) break;
                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
                break;
            case WP_CONCUSSION:
            case WP_REPEATER:
            case WP_FLECHETTE:
                focusItem = Menu_FindItemByName(menuHUD, "metallic_bolts_ammo");
                if (!focusItem) break;
                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
                break;
            case WP_BRYAR_OLD:
            case WP_BLASTER:
                focusItem = Menu_FindItemByName(menuHUD, "blaster_ammo");
                if (!focusItem) break;
                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
                break;
            case WP_ROCKET_LAUNCHER:
                focusItem = Menu_FindItemByName(menuHUD, "rockets_ammo");
                if (!focusItem) break;
                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
                break;
            case WP_BRYAR_PISTOL:
                focusItem = Menu_FindItemByName(menuHUD, "ammo_infinite");
                if (!focusItem) break;
                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
                break;
            case WP_STUN_BATON:
            case WP_SABER:
            default:
                break;
        }
    }
}

static void ST_HudForcePower( menuDef_t *menuHUD )
{
	int				i;
	vec4_t			calcColor;
    vec4_t			calcColor2;

    float			value,inc,percent;
	itemDef_t		*focusItem;
	const int		maxForcePower = 100;
    char            fpString[8];

    qboolean	flash=qfalse;

	// Can we find the menu?
	if (!menuHUD)
	{
		return;
	}

	// Make the hud flash by setting forceHUDTotalFlashTime above cg.time
	if (cg.forceHUDTotalFlashTime > cg.time )
	{
		flash = qtrue;
		if (cg.forceHUDNextFlashTime < cg.time)
		{
			cg.forceHUDNextFlashTime = cg.time + 400;
			trap->S_StartSound (NULL, 0, CHAN_LOCAL, cgs.media.noforceSound );

			if (cg.forceHUDActive)
			{
				cg.forceHUDActive = qfalse;
			}
			else
			{
				cg.forceHUDActive = qtrue;
			}

		}
	}
	else	// turn HUD back on if it had just finished flashing time.
	{
		cg.forceHUDNextFlashTime = 0;
		cg.forceHUDActive = qtrue;
	}

//	if (!cg.forceHUDActive)
//	{
//		return;
//	}

	inc = (float)  maxForcePower / MAX_HUD_TICS;
	value = cg.snap->ps.fd.forcePower;

	for (i=MAX_HUD_TICS-1;i>=0;i--)
	{
		focusItem = Menu_FindItemByName(menuHUD, forceTicName[i]);

		if (!focusItem)
		{
			continue;
		}

//		memcpy(calcColor, colorWhite, sizeof(vec4_t));

		if ( value <= 0 )	// done
		{
			break;
		}
		else if (value < inc)	// partial tic
		{
			if (flash)
			{
				memcpy(calcColor,  colorTable[CT_RED], sizeof(vec4_t));
			}
			else
			{
				memcpy(calcColor,  colorTable[CT_WHITE], sizeof(vec4_t));
			}

			percent = value / inc;
			calcColor[3] = percent;
		}
		else
		{
			if (flash)
			{
				memcpy(calcColor,  colorTable[CT_RED], sizeof(vec4_t));
			}
			else
			{
				memcpy(calcColor,  colorTable[CT_WHITE], sizeof(vec4_t));
			}
		}

		trap->R_SetColor( calcColor);

		CG_DrawPic(
			SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
			focusItem->window.rect.y,
			focusItem->window.rect.w * stHudRatio,
			focusItem->window.rect.h,
			focusItem->window.background
			);

		value -= inc;
	}

	focusItem = Menu_FindItemByName(menuHUD, "forceamount");

	if (focusItem && stSelectedHud != stHudQuake)
	{
		// Print force amount
		if ( flash )
		{
			trap->R_SetColor( colorTable[CT_RED] );
		}
		else
		{
			trap->R_SetColor( focusItem->window.foreColor );
		}

		CG_DrawNumField (
			SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
			focusItem->window.rect.y,
			3,
			cg.snap->ps.fd.forcePower,
			focusItem->window.rect.w * stHudRatio,
			focusItem->window.rect.h,
			NUM_FONT_SMALL,
			qfalse);
    } else if (focusItem && stSelectedHud == stHudQuake)
    {

        if ( flash ) {
            memcpy(calcColor2, colorTable[CT_RED], sizeof(vec4_t));
        }
        else
        {
            memcpy(calcColor2, focusItem->window.foreColor, sizeof(vec4_t));
        }

        Com_sprintf(fpString, sizeof(fpString), "%i", (int)cg.snap->ps.fd.forcePower);
        CG_Text_Paint(SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio - CG_Text_Width(fpString, 1.0f, FONT_MEDIUM), focusItem->window.rect.y, 1.0f, calcColor2, fpString, 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
        CG_Text_Paint(SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio, focusItem->window.rect.y + CG_Text_Height(fpString, 1.0f, FONT_MEDIUM) - CG_Text_Height(fpString, 0.6f, FONT_MEDIUM), 0.6f, calcColor2, " /100", 0, 0, ITEM_TEXTSTYLE_SHADOWED, FONT_MEDIUM);
    }
}

static void ST_HudSaberStyle( centity_t *cent, menuDef_t *menuHUD)
{
	itemDef_t		*focusItem;

	if (!cent->currentState.weapon ) // We don't have a weapon right now
	{
		return;
	}

	if ( cent->currentState.weapon != WP_SABER )
	{
		return;
	}

	// Can we find the menu?
	if (!menuHUD)
	{
		return;
	}

    trap->R_SetColor( colorTable[CT_WHITE] );
    // draw the current saber style in this window
    switch (cg.predictedPlayerState.fd.saberDrawAnimLevel) {
        case SS_FAST:
            focusItem = Menu_FindItemByName(menuHUD, "saberstyle_fast");

            if (focusItem) {
                //trap->R_SetColor(colorWhite);

                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            }
            break;
        case SS_MEDIUM:
            focusItem = Menu_FindItemByName(menuHUD, "saberstyle_medium");

            if (focusItem) {
                //trap->R_SetColor(colorWhite);

                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            }
            break;
        case SS_STRONG:
            focusItem = Menu_FindItemByName(menuHUD, "saberstyle_strong");

            if (focusItem) {
                //trap->R_SetColor(colorWhite);

                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            }
            break;
        case SS_DUAL:
            focusItem = Menu_FindItemByName(menuHUD, "saberstyle_dual");

            if (focusItem) {
                //trap->R_SetColor(colorWhite);

                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            }
            break;
        case SS_STAFF:
            focusItem = Menu_FindItemByName(menuHUD, "saberstyle_staff");

            if (focusItem) {
                //trap->R_SetColor(colorWhite);

                CG_DrawPic(
                        SCREEN_WIDTH - (SCREEN_WIDTH - focusItem->window.rect.x) * stHudRatio,
                        focusItem->window.rect.y,
                        focusItem->window.rect.w * stHudRatio,
                        focusItem->window.rect.h,
                        focusItem->window.background
                );
            }
            break;
    return;
    }
}

static void ST_HudJK2HUDLeftFrame1(float x, float y)
{
	// Inner gray wire frame
	trap->R_SetColor(colorWhite);
	CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDInnerLeft);
}

static void ST_HudJK2HUDLeftFrame2(float x, float y)
{
	// Inner gray wire frame
	trap->R_SetColor(colorWhite);
	CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDLeftFrame);		// Metal frame
}

static void ST_HudHealthJK2(float x, float y)
{
	vec4_t calcColor;
	float	healthPercent, armorPercent;
	playerState_t	*ps;
	int healthAmt;
	char num[16];
	int l;

	ps = &cg.snap->ps;

	Com_sprintf(num, sizeof(num), "%i", ps->stats[STAT_HEALTH]);
	l = strlen(num);
	if (l > 3)
		l = 3;

	healthAmt = ps->stats[STAT_HEALTH];

	if (healthAmt > ps->stats[STAT_MAX_HEALTH])
	{
		healthAmt = ps->stats[STAT_MAX_HEALTH];
	}

	memcpy(calcColor, colorTable[CT_HUD_RED], sizeof(vec4_t));
	healthPercent = (float)healthAmt / ps->stats[STAT_MAX_HEALTH];
	calcColor[0] *= healthPercent;
	calcColor[1] *= healthPercent;
	calcColor[2] *= healthPercent;
	trap->R_SetColor(calcColor);
	CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDHealth);

	armorPercent = (float)(ps->stats[STAT_ARMOR] - (ps->stats[STAT_MAX_HEALTH] / 2)) / (ps->stats[STAT_MAX_HEALTH] / 2);

	// Make tic flash if health is at 20% of full
	if (healthPercent>.20)
	{
		cg.HUDHealthFlag = qtrue;
	}
	else
	{
		if (cg.HUDTickFlashTime < cg.time)			// Flip at the same time
		{
			cg.HUDTickFlashTime = cg.time + 100;

			if ((armorPercent>0) && (armorPercent<.5))		// Keep the tics in sync if flashing
			{
				cg.HUDHealthFlag = cg.HUDArmorFlag;
			}
			else
			{
				if (cg.HUDHealthFlag)
				{
					cg.HUDHealthFlag = qfalse;
				}
				else
				{
					cg.HUDHealthFlag = qtrue;
				}
			}
		}
	}

	// Draw the ticks
	if (cg.HUDHealthFlag)
	{
		if ((ps->stats[STAT_HOLDABLE_ITEMS] & (1 << HI_MEDPAC)) || (ps->stats[STAT_HOLDABLE_ITEMS] & (1 << HI_MEDPAC_BIG)))
			trap->R_SetColor(colorTable[CT_BLUE]);
		else
			trap->R_SetColor(colorTable[CT_HUD_RED]);

		CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDHealthTic);
	}

	trap->R_SetColor(colorTable[CT_HUD_RED]);
	CG_DrawNumField(x - l + (l + 16.0f)*stHudRatio, y + 40, 3, ps->stats[STAT_HEALTH], 6*stHudRatio, 12,
		NUM_FONT_SMALL, qfalse);

}

static void ST_HudArmorJK2(float x, float y)
{
	vec4_t			calcColor;
	float			armorPercent, hold;
	playerState_t	*ps;
	int				armor;
	char			num[16];
	int				l;

	ps = &cg.snap->ps;

	Com_sprintf(num, sizeof(num), "%i", ps->stats[STAT_ARMOR]);
	l = strlen(num);
	if (l > 3)
		l = 3;

	//	Outer Armor circular
	memcpy(calcColor, colorTable[CT_HUD_GREEN], sizeof(vec4_t));

	armor = ps->stats[STAT_ARMOR];

	if (armor> ps->stats[STAT_MAX_HEALTH])
	{
		armor = ps->stats[STAT_MAX_HEALTH];
	}

	hold = armor - (ps->stats[STAT_MAX_HEALTH] / 2);
	armorPercent = (float)hold / (ps->stats[STAT_MAX_HEALTH] / 2);
	if (armorPercent <0)
	{
		armorPercent = 0;
	}
	calcColor[0] *= armorPercent;
	calcColor[1] *= armorPercent;
	calcColor[2] *= armorPercent;
	trap->R_SetColor(calcColor);
	CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDArmor1);

	// Inner Armor circular
	if (armorPercent>0)
	{
		armorPercent = 1;
	}
	else
	{
		armorPercent = (float)ps->stats[STAT_ARMOR] / (ps->stats[STAT_MAX_HEALTH] / 2);
	}
	memcpy(calcColor, colorTable[CT_HUD_GREEN], sizeof(vec4_t));
	calcColor[0] *= armorPercent;
	calcColor[1] *= armorPercent;
	calcColor[2] *= armorPercent;
	trap->R_SetColor(calcColor);
	CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDArmor2);			//	Inner Armor circular

	if (ps->stats[STAT_ARMOR])	// Is there armor? Draw the HUD Armor TIC
	{
		// Make tic flash if inner armor is at 50% (25% of full armor)
		if (armorPercent<.5)		// Do whatever the flash timer says
		{
			if (cg.HUDTickFlashTime < cg.time)			// Flip at the same time
			{
				cg.HUDTickFlashTime = cg.time + 100;
				if (cg.HUDArmorFlag)
				{
					cg.HUDArmorFlag = qfalse;
				}
				else
				{
					cg.HUDArmorFlag = qtrue;
				}
			}
		}
		else
		{
			cg.HUDArmorFlag = qtrue;
		}
	}
	else						// No armor? Don't show it.
	{
		cg.HUDArmorFlag = qfalse;
	}

	if (cg.HUDArmorFlag)
	{
		trap->R_SetColor(colorTable[CT_HUD_GREEN]);
		CG_DrawPic(x, y, 80*stHudRatio, 80, stOutcast.JK2HUDArmorTic);
	}

	trap->R_SetColor(colorTable[CT_HUD_GREEN]);
	CG_DrawNumField(x - l + (l + 18.0f + 14.0f)*stHudRatio, y + 40 + 14, 3, ps->stats[STAT_ARMOR], 6*stHudRatio, 12,
		NUM_FONT_SMALL, qfalse);

}

static void ST_HudJK2HUDRightFrame1(float x, float y)
{
	trap->R_SetColor(colorWhite);
	// Inner gray wire frame
	CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80*stHudRatio, 80, stOutcast.JK2HUDInnerRight);		//
}

static void ST_HudJK2HUDRightFrame2(float x, float y)
{
	trap->R_SetColor(colorWhite);
	CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80*stHudRatio, 80, stOutcast.JK2HUDRightFrame);		// Metal frame
}

static void ST_HudAmmoJK2(centity_t *cent, float x, float y)
{
	playerState_t	*ps;
	int			numColor_i;
	int			i;
	vec4_t		calcColor;
	float		value,inc,percent;

	ps = &cg.snap->ps;

	if (!cent->currentState.weapon ) // We don't have a weapon right now
	{
		return;
	}

	if ( cent->currentState.weapon == WP_SABER )
	{
		trap->R_SetColor( colorTable[CT_WHITE] );
		// don't need to draw ammo, but we will draw the current saber style in this window
		switch ( cg.predictedPlayerState.fd.saberDrawAnimLevel )
		{
		case SS_FAST:
			CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80*stHudRatio, 40, stOutcast.JK2HUDSaberStyle1);
			break;
		case SS_MEDIUM:
			CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80*stHudRatio, 40, stOutcast.JK2HUDSaberStyle2);
			break;
		case SS_STRONG:
			CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80*stHudRatio, 40, stOutcast.JK2HUDSaberStyle3);
			break;
		case SS_DUAL:
            CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80 * stHudRatio, 40, stOutcast.JK2HUDSaberStyle5);
            break;
        case SS_STAFF:
			CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x)*stHudRatio, y, 80 * stHudRatio, 40, stOutcast.JK2HUDSaberStyle4);
            break;
		}
		return;
	}
	else
	{
		value = ps->ammo[weaponData[cent->currentState.weapon].ammoIndex];
	}

	numColor_i = CT_HUD_ORANGE;

	trap->R_SetColor( colorTable[numColor_i] );
	if (value < 0 || (weaponData[cent->currentState.weapon].energyPerShot == 0 && weaponData[cent->currentState.weapon].altEnergyPerShot == 0))  { // infinite ammo
		CG_DrawScaledProportionalString(SCREEN_WIDTH - (SCREEN_WIDTH - x - 40)*stHudRatio, y + 20, "--", NUM_FONT_SMALL, colorTable[numColor_i], 0.9);

		inc = 8.0f / ST_JK2_TICS;
		value = 8;
	}
	else {
		CG_DrawNumField(SCREEN_WIDTH - (SCREEN_WIDTH - x - 30)*stHudRatio, y + 26, 3, value, 6 * stHudRatio, 12, NUM_FONT_SMALL, qfalse);

		inc = (float)ammoData[weaponData[cent->currentState.weapon].ammoIndex].max / ST_JK2_TICS;
		value = ps->ammo[weaponData[cent->currentState.weapon].ammoIndex];
	}

	for (i=ST_JK2_TICS-1;i>=0;i--)
	{

		if (value <= 0)	// partial tic
		{
			memcpy(calcColor, colorTable[CT_BLACK], sizeof(vec4_t));
		}
		else if (value < inc)	// partial tic
		{
			memcpy(calcColor, colorTable[CT_WHITE], sizeof(vec4_t));
			percent = value / inc;
			calcColor[0] *= percent;
			calcColor[1] *= percent;
			calcColor[2] *= percent;
		}
		else
		{
			memcpy(calcColor, colorTable[CT_WHITE], sizeof(vec4_t));
		}

		trap->R_SetColor( calcColor );
		CG_DrawPic( SCREEN_WIDTH - (SCREEN_WIDTH - x - st_ammoTicPos[i].x)*stHudRatio,
			y + st_ammoTicPos[i].y,
			st_ammoTicPos[i].width*stHudRatio,
			st_ammoTicPos[i].height,
			st_ammoTicPos[i].tic );

		value -= inc;
	}

}

static void ST_HudForcePowerJK2(float x, float y)
{
	int			i;
	vec4_t		calcColor;
	float		value, inc, percent;
//	qboolean	flash = qfalse;

	inc = (float)100 / ST_JK2_TICS;
	value = cg.snap->ps.fd.forcePower;

	// Make the hud flash by setting forceHUDTotalFlashTime above cg.time
	if (cg.forceHUDTotalFlashTime > cg.time)
	{
//		flash = qtrue;
		if ( cg.forceHUDNextFlashTime < cg.time )
		{
			cg.forceHUDNextFlashTime = cg.time + 400;
			trap->S_StartLocalSound(cgs.media.noforceSound, CHAN_LOCAL);
			if ( cg.forceHUDActive )
			{
				cg.forceHUDActive = qfalse;
			}
			else
			{
				cg.forceHUDActive = qtrue;
			}

		}
	}
	else	// turn HUD back on if it had just finished flashing time.
	{
		cg.forceHUDNextFlashTime = 0;
		cg.forceHUDActive = qtrue;
	}

	for (i = ST_JK2_TICS - 1; i >= 0; i--)
	{

		if (value <= 0)	// partial tic
		{
			memcpy(calcColor, colorTable[CT_BLACK], sizeof(vec4_t));
		}
		else if (value < inc)	// partial tic
		{
			memcpy(calcColor, colorTable[CT_WHITE], sizeof(vec4_t));
			percent = value / inc;
			calcColor[0] *= percent;
			calcColor[1] *= percent;
			calcColor[2] *= percent;
		}
		else
		{
			memcpy(calcColor, colorTable[CT_WHITE], sizeof(vec4_t));
		}

		trap->R_SetColor(calcColor);
		CG_DrawPic(SCREEN_WIDTH - (SCREEN_WIDTH - x - st_forceTicPos[i].x)*stHudRatio,
			y + st_forceTicPos[i].y,
			st_forceTicPos[i].width*stHudRatio,
			st_forceTicPos[i].height,
			st_forceTicPos[i].tic);

		value -= inc;
	}
}
