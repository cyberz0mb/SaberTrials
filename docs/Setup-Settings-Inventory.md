# Setup settings inventory

Pinned baseline: current Controls candidate; defaults and flags below come from the owning engine/cgame source, not the browser preview.

| Tab | Setting | Variable | Default | Owner |
|---|---|---|---|---|
| Video | Renderer | `cl_renderer` | `rd-vanilla` | `engine\codemp\client\cl_main.cpp:2467` |
| Video | Resolution | `r_mode` | `4` | `engine\codemp\rd-dedicated\tr_init.cpp:346` |
| Video | Custom width | `r_customwidth` | `1600` | `engine\codemp\rd-dedicated\tr_init.cpp:350` |
| Video | Custom height | `r_customheight` | `1024` | `engine\codemp\rd-dedicated\tr_init.cpp:351` |
| Video | Fullscreen | `r_fullscreen` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:347` |
| Video | Brightness | `r_gamma` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:378` |
| Video | V-Sync | `r_swapInterval` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:376` |
| Video | Color depth | `r_colorbits` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:340` |
| Video | Geometry detail | `r_lodbias` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:362` |
| Video | Texture detail | `r_picmip` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:334` |
| Video | Texture depth | `r_texturebits` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:338` |
| Video | Texture filter | `r_texturemode` | `GL_LINEAR_MIPMAP_NEAREST` | `engine\codemp\rd-dedicated\tr_init.cpp:375` |
| Video | Antialiasing | `r_ext_multisample` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1439` |
| Video | Anisotropic filtering | `r_ext_texture_filter_anisotropic` | `16` | `engine\codemp\rd-dedicated\tr_init.cpp:326` |
| Video | Detailed shaders | `r_detailtextures` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:337` |
| Video | Texture compression | `r_ext_compress_textures` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:319` |
| Video | Curve subdivisions | `r_subdivisions` | `4` | `engine\codemp\rd-dedicated\tr_init.cpp:355` |
| Video | Dynamic lights | `r_dynamiclight` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:371` |
| Video | Dynamic glow | `r_dynamicglow` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:327` |
| Video | Light flares | `r_flares` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:364` |
| Video | Wall marks | `cg_marks` | `1` | `frontend\codemp\cgame\cg_xcvar.h:103` |
| Video | Texture intensity | `r_intensity` | `1` | `engine\codemp\rd-dedicated\tr_init.cpp:359` |
| Video | Vertex lighting | `r_vertexLight` | `0` | `engine\codemp\rd-dedicated\tr_init.cpp:353` |
| Video | HDR | `r_hdr` | `1` | `engine\codemp\rd-rend2\tr_init.cpp:1474` |
| Video | Tonemapping | `r_tonemap` | `1` | `engine\codemp\rd-rend2\tr_init.cpp:1477` |
| Video | Autoexposure | `r_autoexposure` | `1` | `engine\codemp\rd-rend2\tr_init.cpp:1483` |
| Video | HDR lightmaps | `r_floatLightmap` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1475` |
| Video | Deluxe mapping | `r_deluxemapping` | `1` | `engine\codemp\rd-rend2\tr_init.cpp:1495` |
| Video | Cubemapping | `r_cubemapping` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1498` |
| Video | Parallax mapping | `r_parallaxmapping` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1497` |
| Video | Generate normal maps | `r_genNormalMaps` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1510` |
| Video | SSAO | `r_ssao` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1491` |
| Video | Deluxe specular | `r_deluxeSpecular` | `1` | `engine\codemp\rd-rend2\tr_init.cpp:1496` |
| Video | Cubemap bounces | `r_cubemappingBounces` | `0` | `engine\codemp\rd-rend2\tr_init.cpp:1499` |
| Sound | Effects volume | `s_volume` | `0.5` | `engine\codemp\client\snd_dma.cpp:466` |
| Sound | Music volume | `s_musicvolume` | `0.25` | `engine\codemp\client\snd_dma.cpp:462` |
| Sound | Voice volume | `s_volumeVoice` | `1.0` | `engine\codemp\client\snd_dma.cpp:467` |
| Sound | Sound quality | `s_khz` | `44` | `engine\codemp\client\snd_dma.cpp:454` |
| Sound | OpenAL | `s_UseOpenAL` | `0` | `engine\codemp\client\snd_dma.cpp:488` |
| Sound | Voice language | `s_language` | `english` | `engine\codemp\client\snd_dma.cpp:455` |
| Sound | Chat sound | `cg_chatBeep` | `1` | `frontend\codemp\cgame\cg_xcvar.h:48` |
| Sound | Team chat sound | `cg_teamChatBeep` | `1` | `frontend\codemp\cgame\cg_xcvar.h:133` |
| Sound | Jump sounds | `cg_jumpSounds` | `0` | `frontend\codemp\cgame\cg_xcvar.h:101` |
| Interface | Chat box size (%) | `st_chatSize` | `100` | `development-source/client-game/codemp/cgame/cg_xcvar.h:221` |
| Interface | Chat box width (%) | `st_chatWidth` | `42` | `development-source/client-game/codemp/cgame/cg_xcvar.h:222` |
| Interface | Chat box height (%) | `st_chatHeight` | `20` | `development-source/client-game/codemp/cgame/cg_xcvar.h:223` |
| Interface | Chat box opacity (%) | `st_chatOpacity` | `65` | `development-source/client-game/codemp/cgame/cg_xcvar.h:220` |
| Interface | Universal translator | `st_translate` | `0` | `development-source/translator/cl_st_translation.inc:6` |
| Interface | Translate into | `st_translateTarget` | `1` | `development-source/translator/cl_st_translation.inc:8` |
| Interface | Message language | `st_translateSource` | `0` | `development-source/translator/cl_st_translation.inc:7` |
| Interface | Show original message | `st_translateOriginal` | `1` | `development-source/translator/cl_st_translation.inc:9` |
| Interface | HUD style | `st_hudStyle` | `1` | `frontend\codemp\cgame\cg_xcvar.h:216` |
| Interface | HUD size (%) | `st_hudScale` | `100` | `frontend\codemp\cgame\cg_xcvar.h:217` |
| Interface | Panel opacity (%) | `st_hudOpacity` | `55` | `frontend\codemp\cgame\cg_xcvar.h:218` |
| Interface | Show score | `cg_drawScores` | `1` | `frontend\codemp\cgame\cg_xcvar.h:68` |
| Interface | Low health pulse | `st_hudPulse` | `1` | `frontend\codemp\cgame\cg_xcvar.h:219` |
| Interface | Radar | `cg_drawRadar` | `0` | `development-source/client-game/codemp/cgame/cg_xcvar.h:66` |
| Interface | Health and ammo | `cg_drawStatus` | `1` | `frontend\codemp\cgame\cg_xcvar.h:70` |
| Interface | Match timer | `cg_drawTimer` | `0` | `frontend\codemp\cgame\cg_xcvar.h:72` |
| Interface | Portrait | `st_portraitMode` | `1` | `frontend\codemp\cgame\cg_xcvar.h:212` |
| Interface | Subject | `st_portraitTarget` | `0` | `frontend\codemp\cgame\cg_xcvar.h:213` |
| Interface | Portrait size | `st_portraitSize` | `80` | `frontend\codemp\cgame\cg_xcvar.h:214` |
| Interface | Damage reactions | `st_portraitDamage` | `1` | `frontend\codemp\cgame\cg_xcvar.h:215` |
| Interface | Crosshair | `cg_drawCrosshair` | `1` | `frontend\codemp\cgame\cg_xcvar.h:59` |
| Interface | Target names | `cg_drawCrosshairNames` | `1` | `frontend\codemp\cgame\cg_xcvar.h:60` |
| Interface | Dynamic crosshair | `cg_dynamicCrosshair` | `1` | `frontend\codemp\cgame\cg_xcvar.h:74` |
| Interface | Precise crosshair trace | `cg_dynamicCrosshairPrecision` | `1` | `frontend\codemp\cgame\cg_xcvar.h:75` |
| Interface | Vehicle lead indicator | `cg_drawVehLeadIndicator` | `1` | `frontend\codemp\cgame\cg_xcvar.h:73` |
| Interface | Team overlay | `cg_drawTeamOverlay` | `0` | `frontend\codemp\cgame\cg_xcvar.h:71` |
| Interface | Status notifications | `st_notifications` | `1` | `frontend\codemp\cgame\cg_xcvar.h:220` |
| Interface | Console overlay | `st_consoleOverlay` | `1` | `engine\codemp\client\cl_console.cpp:498` |
| Interface | Console opacity | `con_opacity` | `0.55` | `engine\codemp\client\cl_console.cpp:497` |
| Game Options | Force player models | `cg_forceModel` | `0` | `frontend\codemp\cgame\cg_xcvar.h:87` |
| Game Options | Defer player models | `cg_deferPlayers` | `1` | `frontend\codemp\cgame\cg_xcvar.h:83` |
| Game Options | Simple items | `cg_simpleItems` | `0` | `frontend\codemp\cgame\cg_xcvar.h:124` |
| Game Options | Team color skins | `cg_teamColorSkins` | `1` | `development-source/client-game/codemp/cgame/cg_xcvar.h:88` |
| Game Options | Team color lightsabers | `cg_teamColorSabers` | `1` | `development-source/client-game/codemp/cgame/cg_xcvar.h:89` |
| Game Options | Character shadows | `cg_shadows` | `1` | `frontend\codemp\cgame\cg_xcvar.h:123` |
| Game Options | Saber trail | `cg_saberTrail` | `1` | `frontend\codemp\cgame\cg_xcvar.h:119` |
| Game Options | Dismemberment | `cg_dismember` | `2` | `frontend\codemp\cgame\cg_xcvar.h:82` |
| Game Options | Speed trail | `cg_speedTrail` | `1` | `frontend\codemp\cgame\cg_xcvar.h:131` |
| Game Options | Projectile trails | `cg_noProjectileTrail` | `0` | `frontend\codemp\cgame\cg_xcvar.h:106` |
| Game Options | Team chat only | `cg_teamChatsOnly` | `0` | `frontend\codemp\cgame\cg_xcvar.h:134` |
| Game Options | Text language | `se_language` | `english` | `engine\codemp\qcommon\stringed_ingame.cpp:1178` |
| Game Options | Footsteps | `cg_footsteps` | `3` | `frontend\codemp\cgame\cg_xcvar.h:86` |
| Game Options | Vertical sway | `cg_bobup` | `0.005` | `frontend\codemp\cgame\cg_xcvar.h:44` |
| Game Options | Pitch sway | `cg_bobpitch` | `0.002` | `frontend\codemp\cgame\cg_xcvar.h:42` |
| Game Options | Roll sway | `cg_bobroll` | `0.002` | `frontend\codemp\cgame\cg_xcvar.h:43` |
| Game Options | Run pitch | `cg_runpitch` | `0.002` | `frontend\codemp\cgame\cg_xcvar.h:112` |
| Game Options | Run roll | `cg_runroll` | `0.005` | `frontend\codemp\cgame\cg_xcvar.h:113` |
| Network | Rate | `rate` | `25000` | `engine\codemp\client\cl_main.cpp:2883` |
| Network | Snapshots | `snaps` | `40` | `engine\codemp\client\cl_main.cpp:2884` |
| Network | Max packets | `cl_maxpackets` | `63` | `engine\codemp\client\cl_main.cpp:2813` |
| Network | Packet duplication | `cl_packetdup` | `1` | `engine\codemp\client\cl_main.cpp:2814` |
| Network | Time Nudge | `cl_timeNudge` | `0` | `engine\codemp\client\cl_main.cpp:2793` |
| Network | FPS limit | `com_maxfps` | `125` | `engine\shared\sys\sys_main.cpp:162` |
| Network | FPS counter | `cg_drawFPS` | `0` | `frontend\codemp\cgame\cg_xcvar.h:62` |
| Network | Lagometer | `cg_lagometer` | `0` | `frontend\codemp\cgame\cg_xcvar.h:102` |
| Network | Allow downloads | `cl_allowDownload` | `1` | `engine\codemp\client\cl_main.cpp:2830` |
| Recording | Clean Capture | `cg_draw2D` | `1` | `frontend\codemp\cgame\cg_xcvar.h:56` |
| Recording | Streamer mode | `st_streamerMode` | `0` | `frontend\codemp\cgame\cg_xcvar.h:171` |
| Recording | Replace ordinary HUD | `st_streamerCleanHud` | `1` | `frontend\codemp\cgame\cg_xcvar.h:172` |
| Recording | Names / scores | `st_streamerOverlay` | `1` | `frontend\codemp\cgame\cg_xcvar.h:173` |
| Recording | Kill feed | `st_streamerKillFeed` | `1` | `frontend\codemp\cgame\cg_xcvar.h:174` |
| Recording | Player labels | `st_streamerPlayerNames` | `1` | `frontend\codemp\cgame\cg_xcvar.h:175` |
| Recording | Team overlay | `st_streamerTeamOverlay` | `1` | `frontend\codemp\cgame\cg_xcvar.h:177` |
| Recording | Letterbox | `st_streamerLetterbox` | `0` | `frontend\codemp\cgame\cg_xcvar.h:179` |
| Recording | Match clock | `st_streamerMatchClock` | `2` | `frontend\codemp\cgame\cg_xcvar.h:178` |
| Recording | Smooth follow | `st_streamerCameraSmooth` | `1` | `frontend\codemp\cgame\cg_xcvar.h:176` |
| Recording | Camera FOV | `st_streamerFov` | `90` | `frontend\codemp\cgame\cg_xcvar.h:180` |
| Recording | Freecam speed | `st_streamerCameraSpeed` | `400` | `frontend\codemp\cgame\cg_xcvar.h:181` |
| Camera | Third person | `cg_thirdPerson` | `0` | `frontend\codemp\cgame\cg_xcvar.h:135` |
| Camera | Distance | `cg_thirdPersonRange` | `80` | `frontend\codemp\cgame\cg_xcvar.h:141` |
| Camera | Orbit angle | `cg_thirdPersonAngle` | `0` | `frontend\codemp\cgame\cg_xcvar.h:137` |
| Camera | Pitch | `cg_thirdPersonPitchOffset` | `0` | `frontend\codemp\cgame\cg_xcvar.h:140` |
| Camera | Height | `cg_thirdPersonVertOffset` | `16` | `frontend\codemp\cgame\cg_xcvar.h:144` |
| Camera | Shoulder offset | `st_cameraShoulder` | `0` | `development-source/client-game/codemp/cgame/cg_xcvar.h:142` |
| Camera | Camera damping | `cg_thirdPersonCameraDamp` | `0.3` | `development-source/client-game/codemp/cgame/cg_xcvar.h:140` |
| Camera | Target damping | `cg_thirdPersonTargetDamp` | `0.5` | `frontend\codemp\cgame\cg_xcvar.h:143` |
| Camera | Field of view | `cg_fov` | `80` | `frontend\codemp\cgame\cg_xcvar.h:88` |
| Camera | Weapon FOV | `cg_fovViewmodel` | `0` | `frontend\codemp\cgame\cg_xcvar.h:90` |
| Camera | Show weapon | `cg_drawGun` | `1` | `frontend\codemp\cgame\cg_xcvar.h:64` |

## Moved/adapted utilities

- UI proxy fields (`ui_r_*`, `st_uiHud*`, `st_uiPortraitSize`) bind to actual renderer/HUD/portrait variables above. Status proxies are not settings.
- Old Input controls remain solely in Controls; console appearance moves to Interface.
- View swaying is preserved as its five existing component variables rather than the transient `ui_disableWeaponSway` script field.
- Existing quality preset, driver info, installed Mods discovery and spectator Free Camera/Previous/Next actions remain utilities.
- Defaults becomes a confirmed, staged reset of this tab only.
- Saved Configs has one manager in Setup; Controls links to it.
- EAX is unavailable in this OpenJK menu baseline (legacy UI disables it); retain supported OpenAL backend and quality choices.
- Language selectors preserve the current value; packaged language choices will be enumerated from existing localization metadata.
