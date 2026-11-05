# v0.3.0-beta.1 — physical hats and weapons

**Every VR player must update. v0.2.1-beta.1 and earlier do not send grip-button input, so they cannot grab the new items.** Close the old helper and game, start SteamVR, open the new EXE, then join a fresh server.

- Grip your hat or another player's hat at the point you touch. Wrist rotation pivots it around that point. Release near any player's head to equip it there; release elsewhere to drop a shared physical pickup. Repeated swaps preserve the original fit. Legacy body-touch auto-equipping is suppressed.
- Adds shared crowbar, pistol, and AK-47 pickups with public Roblox meshes/textures/audio, physical magazines, manual racking, recoil, haptics, and two-hand aiming. Ordinary players can see the weapons without installing the helper.
- Stabilizes local gun/magazine poses, reload entry and seating, two-hand aim, and dropped-item visibility. Sends grip inputs with short dropout protection.
- Y is the only menu shortcut. Smooth turn speed is adjustable and saved. The torso follows head yaw around a connected neck, with the camera at the eyes.
- Repairs stale launcher associations so starting an ordinary game does not keep launching an old helper.

The updated support scripts are live in [Hexagon VR Test](https://www.hexagon.pw/games/105279), version 14. Existing servers keep their old scripts; rejoin a fresh one. The full ZIP contains an offline demo and installer for your own XML places. The online map is not part of the public download.

Validation: 85 unit tests; native Hexagon 2015 weapon, moving-grip, body/visibility, and hat checks; separate local server plus two Studio clients for independent VR weapon pickup and cross-player hat transfers. EXE asset/installer smoke checks passed. Physical headset feel and a simultaneous live two-headset session still need user testing.
