// The existing getsabercvars / updatesabercvars load and save ui_saberHand.
itemDef {
 name st_ingame_hand
 text "Dominant hand:"
 rect 15 136 180 22
 type ITEM_TYPE_MULTI
 cvar ui_saberHand
 cvarFloatList { "Right" 0 "Left" 1 }
 font 4 textscale .70
 textalignx 0 textaligny 0
 forecolor .76 .86 .93 1
 visible 1
 descText "Choose your saber hand, then select Apply Changes."
}
itemDef {
 name st_ingame_hand_note
 text "Applies on next spawn."
 rect 15 159 180 16
 font 4 textscale .55
 textalignx 0 textaligny 0
 forecolor .55 .72 .83 1
 visible 1 decoration
}
