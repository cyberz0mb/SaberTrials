# Menu selection visibility

The Host a Match slot rows use Saber Trials blue (`.14 .70 1`) and red
(`1 .24 .34`), retaining their hue when focused. Closed slots keep their native
half brightness. Focused slots receive a themed field outline and team-colored
edge, without changing their click/cycle behavior or layout.

Native text lists now draw their selected row before the text: blue fill, cyan
rules, gold left marker and bright text. Hover has a separate, subtler cyan
state. Selection comes from the same `item->cursorPos` that drives feeder
selection, remains visible when focus leaves the list, and follows native
mouse, keyboard and controller selection. Names and vote actions are unchanged;
only the selected name's displayed color escapes are removed so black-colored
names remain readable. UTF-8 text continues through the existing language font
path.

This fixes the absent outline color in both Call Vote lists and the faint
post-text selection overlay in the host map list. The renderer change also
supplies a consistent selected row for other native vertical text lists. Image
grids, horizontal lists, and non-themed fallback rendering keep their existing
drawing. The menu frame, traveling light, layout, art and assets are preserved.

`tools/Build-Menu-Selection.py` layers the change over the receipt-verified
installed Vulkan-compatible UI source, builds only `uix86_64.dll`, and installs
that module plus the two targeted loose menus with transaction backups. The
gameplay update and saved settings are protected. No game is launched; the user
requested to perform in-game testing personally.
