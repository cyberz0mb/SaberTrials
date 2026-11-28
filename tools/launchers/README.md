# Launching Saber Trials

On Windows, open the Jedi Academy **GameData** folder. Double-click
**SaberTrials.x86_64.exe** to play or **SaberTrialsDed.x86_64.exe** to host.
The [command launcher](SaberTrials.cmd) also starts the client.

Keep `z_sabertrials_studio_intro.pk3` in `GameData/SaberTrials/`. On a normal
launch, the client plays the four-second MOTU Interactive intro before the
main menu. The existing `com_bootlogo` setting controls playback. Launching
directly into a server with `+connect` skips the intro.
