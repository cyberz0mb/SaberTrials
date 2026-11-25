# Hosting multi-team TFFA

In **Host a Match**, choose **Team FFA**. Set **Teams** to any number from 2 through 8. The colors unlock in order: Red, Blue, Green, Yellow, White, Black, Orange, and Purple. The default is Red and Blue.

Choose **Players per team** to cap each roster at 2, 3, or 4. With eight teams, those settings provide 16, 24, or 32 playing spots. **Open** lets the server's maximum player count set the overall limit. Players can choose an available color in the join menu or type a command such as `team purple`.

Each enemy kill earns one point for the killer's team in multi-team TFFA. Assists appear on the player's scoreboard. The kill limit and the time limit compare all enabled teams. A tie for the lead goes to sudden death.

The host roster shows all 32 slots. Each open slot shows its team and can be switched between a human and a bot. A selected bot joins the color displayed on that slot. The scoreboard puts the highest-scoring team first and groups its players together. Teams tied on points keep their usual color order.

With team skins enabled, stock JKA characters wear muted team colors, including off-white and charcoal. Customizable Jedi retain their selected clothing pieces. With team saber colors enabled, Black Team uses a black blade with a light edge.

In Profile, select a stock character and click **Team skin** to cycle through Default and all eight colors. **Apply** saves the outfit color. **Cancel changes** restores the previous selection. In TFFA the assigned team takes priority when team skins are enabled. DLC characters show the team skins supplied with their model.

The stock uniform package can be rebuilt from the four original JKA `base/assets*.pk3` archives using `tools/Build-Stock-Team-Skins.py` with Pillow and NumPy. The script writes the package and an inventory to `dist/multiteam-02`.

## Dedicated server

For eight teams of four, put these settings before the map command in the server configuration. Apply changes to the team count or team size on the next map start or restart.

```cfg
set g_gametype 6
set g_tffaTeams 8
set g_tffaTeamSize 4
set sv_maxclients 32
```

Set `g_tffaTeamSize` to `0` for open rosters. Players and the server should use the updated Saber Trials build so all eight colors and the full scoreboard are available.
