# Emotes in Saber Trials

In **Profile → Emotes**, select one of five groups and one of its eight slots. Selecting an emote immediately loops its preview on the current character. Choose **Assign to slot** to equip it. **Clear slot**, **Rename group**, and **Bind key** save immediately. Direct bindings ask for an unused key or controller button.

Bind **Emote Wheel** under **Controls → Key Bindings → Communication**. If the new key or button is taken, choose **Replace** or, if the selected slot already has a binding, **Swap**. Then apply the changes. Hold the binding, point with the mouse or right stick, then release to play. The left stick still moves your character while the wheel is open. Number keys select slots. The mouse wheel and controller bumpers cycle groups. Enter or the controller confirm button plays the selection. Esc or the controller back button closes the wheel. To open the wheel without holding a button, choose **Wheel activation → Toggle** in the Emotes editor.

## Install a pack

Place the `.pk3` in `SaberTrials/dlc/emotes` and restart the game. A matching pack must be present on an emote-capable server and on any player client that wants to see the DLC animation. If a pack is missing or its animation differs from the server version, the wheel keeps the saved slot and marks the emote unavailable. DLC packs using this format require a Saber Trials server running with `sv_pure 0`. Stock emotes can operate on a pure Saber Trials server.

On the current Saber Trials server build the wheel uses cosmetic animations in FFA and Team FFA. Server operators can disable these with `g_stEmotes 0`. Taunt, Bow, Flourish, and Celebrate play over normal movement. Meditate and DLC clips require standing on the ground, and moving ends those clips. Attacks, damage, death and leaving the match end playback. Stock JKA commands and their Duel restrictions continue to apply when playing on an older server.

## Create a pack

Use a stationary, one-shot clip authored on the canonical 53-bone JKA humanoid skeleton. Keep the skeleton and bind data byte-for-byte compatible with the Saber Trials humanoid. Export a JKA version 6 GLA with the animation baked at a constant frame rate. Inspect body scale, feet placement, hand positions, and held weapons before sharing. Raw FBX needs conversion to GLA first.

Run this from the source checkout, substituting the range and frame rate from your exported animation.

```powershell
py tools/Pack-Emote.py MyCharacter.gla MyWave.pk3 --id my_wave --label "Wave" --first 1800 --frames 40 --fps 20
```

The pack contains `emote.txt` and `poses.bin`. The tool writes the version, stable ID, duration, display label, and skeleton fingerprint, then extracts the frame data. Use a unique lowercase ID of at most 20 characters and keep that ID stable in future releases. Use a plain-text label of up to 40 printable ASCII characters. A pack holds one clip of 2–240 frames at 10–60 FPS. Up to 32 DLC clips are loaded. Prefer a creator prefix on public pack IDs.

The game reads only those two entries. Other files inside an emote pack are ignored. Clips are appended in memory without replacing the existing stance library or installed model assets. Models using a private animation skeleton can use their existing stock gestures in matches. Profile previews and DLC gestures currently target models using the shared humanoid GLA. New menu labels are currently in English.

Distribute only animation data you have permission to share. Include a README with author, source, redistribution terms, emote ID, and installation instructions. The QA example can be generated locally from an installed JA+ animation archive by using that archive as input and setting the range to `13518` for `29` frames at `20` FPS. It is the Silence gesture. The project does not distribute the extracted JA+ motion.
