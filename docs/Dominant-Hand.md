# Dominant saber hand

Start the game with **Launch-SaberTrials-Overhaul.cmd** in the SaberTrials
folder. This feature requires the included updated Saber Trials client.

Open **Profile**, then click **Apply** to reach saber selection. Choose
**Dominant hand…**, select **Right** or **Left**, and click **Apply**.
The preview changes immediately. Gameplay uses the saved choice on your next
spawn on a compatible Saber Trials server. **Back** or **Esc** cancels an
unsaved hand change.

While connected to a server, press **Esc → Player → Saber**, click
**Dominant hand: Right/Left**, then **Apply Changes**. The same next-spawn
rule applies. Restart the client once after the pause-menu update to load it.

- Single sabers switch the main grip and stance.
- Dual sabers switch the primary and secondary hands.
- Staff sabers switch the dominant grip and stance.
- Your character's clothing, hair, scars and other asymmetric details stay on
  their original side; the pose changes rather than mirroring the model mesh.
- Saber locks remain available between right- and left-handed fighters.

If unusual custom equipment cannot form the new lock pose, both fighters use
the original lock pose for that lock. The selected hand returns afterward.
The lock's duration, controls and win/loss rules are unchanged. Vehicle combat
keeps its original animations and grips; dismounting restores the chosen hand.

Servers enable this feature with `g_saberHandedness 1` (the new build's default).
It requires the matching Saber Trials engine and native modules on the server
and clients. Older servers continue to use their original handedness behavior.
The saved console preference is `saberHand 0` for right or `saberHand 1` for left.

Use matching character and saber assets on server and client. A client that
temporarily cannot construct a lock uses a paired visual fallback and retries;
that fallback cannot guarantee exact visual agreement with server collision
when the local assets differ.

The automated checks cover native rendered grips and blades, single/dual/staff
locks, menu saving, scaled humanoids, animation timing, and paired fallback and
restoration logic. Live multiplayer acceptance remains a separate in-game
check. No local game server was started as part of these checks.
