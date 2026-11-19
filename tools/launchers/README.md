# Launching Saber Trials

On Windows, open the **Saber Trials** shortcut or run
[SaberTrials.cmd](SaberTrials.cmd). The launcher expects the matching client
executable and multiplayer modules in the Saber Trials installation.

Keep `z_sabertrials_studio_intro.pk3` in `GameData/SaberTrials/`. On a normal
launch, the client plays the four-second MOTU Interactive intro before the
main menu. The existing `com_bootlogo` setting controls playback. Launching
directly into a server with `+connect` skips the intro.
