# Saber Trials music player

The Windows player uses .NET Framework 4.8. Streaming controls use the Windows media session feature available in Windows 10 version 1809 and later, including Windows 11.

Open **Music player** at the top right of the Saber Trials pause menu. To open and close it with your own key, go to **Controls → Key Bindings → Camera / UI → Music player**. The **Desktop player** button opens the full Windows interface. You can also launch **SaberTrials Music.exe** from the game's **SaberTrials/client** folder.

Both players show the current album cover when the selected app or local file supplies artwork through Windows. Tracks without a cover show the Saber Trials record.

## Volume

Use **−** and **+** in the mini-player to change volume in five-point steps, or drag the desktop volume slider. Local files remember their volume. For a connected streaming app, the control changes that app's Windows mixer volume. A browser can share one volume setting across its tabs. When Windows cannot identify a single mixer session for the selected player, use the provider's volume control. Game sound effects and the Windows master volume have their own settings.

## Connect YouTube Music

1. In the desktop player, select **YouTube Music**, then **Open YouTube Music**.
2. Start a song in the browser or the installed YouTube Music web app. Sign in there if you want your library or playlists.
3. Return to the desktop player. Under **Playback session**, choose the browser entry displaying that song. Open the in-game player to see its title and the controls the browser offers.

If you close the browser player, start a song and choose its session again. Some browsers group several tabs into one Windows media session. Opening YouTube Music in its own browser window or web app can make it easier to identify. Play, pause, previous, next, and seeking depend on the controls the service exposes for the current track. The desktop progress slider supports seeking when available.

## Spotify and Apple Music

Select the service and start a song in its desktop app or web player. Saber Trials can connect automatically when Windows identifies a single matching desktop app. For a browser, choose the entry showing the song you started. Each service handles its own sign-in, playback, and subscription features.

## Search from a match

The mini-player's **Find results** button opens the selected service's search. Pick a result there to start listening. The following console commands use your selected music source and work in a key binding.

| Command | Action |
| --- | --- |
| `playnext` | Skip to the next track. |
| `playprev` | Return to the previous track. |
| `pausemusic` | Pause playback. |
| `search` | Open the mini-player with the search field ready to type. |
| `search Daft Punk` | Search for an artist, song, or album. Multiword names work. |
| `musicvolume 40` | Set music volume to 40%. The range is 0–100. |
| `musicvolume +5` or `musicvolume -5` | Raise or lower the current volume by five points. |

For example, enter `bind F7 playnext` or `bind F8 "musicvolume -5"` in the console. You can also assign the music actions in **Controls → Key Bindings → Camera / UI**.

To search a specific provider directly, use its name.

~~~text
ytmusic play Moonlight Sonata
spotify play Daft Punk
applemusic play Discovery
~~~

Use the provider name with **play** on its own to resume the linked session. For example, **ytmusic pause**, **ytmusic play**, and **ytmusic next** control the selected YouTube Music session. **st_music** opens or closes the mini-player.

## Local files

In the desktop player select **Local files → Add files**, then choose a track. Local search uses filenames and available song, artist, and album tags. A single match plays immediately. Multiple matches open a filtered list in the desktop player. The player advances through the library in order. Supported formats depend on the media codecs installed on Windows.

## Startup and privacy

After you first use music in a game profile, the helper starts in the background with that profile on subsequent launches. It waits for you to start playback. To start it only when you open Music, enter **seta st_musicAutoStart 0** in the console. Use **seta st_musicAutoStart 1** to enable startup again.

The helper runs on the player's Windows PC. Closing the mini-player returns to the previous menu or match and keeps playback going. The hidden helper exits when the game closes. A desktop window you leave open stays available independently. Music account credentials stay with the service. The game server receives no music commands, library paths, or track information.
