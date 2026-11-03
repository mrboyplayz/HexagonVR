# Release validation

## v0.2.0-beta.1

- 17 automated Python/Lua tests pass on Windows with Python 3.13, including two simultaneous server sessions, independent pose/rate limits, isolated tracking timeout, reset, death, respawn, disconnect, allowlist behavior, and invalid pose rejection.
- Native C++ stereo-matrix test passes as part of the build.
- Standalone EXE reports installed SteamVR and a present headset.
- Standalone place installer produces the multiplayer scripts, unrestricted default allowlist, PC-safe AutoEnable setting, and eight hosted menu asset references.
- Standalone EXE opens its embedded Studio demo with simulated tracking, connects to the actual client mailbox, and receives render acknowledgements and camera viewport data. This checks packaging and local transport without claiming a headset visual test of this release.
- Actual online 2015 Player GPU rendering verified using the release native modules, cached Quest calibration, and simulated tracking: 802 native stereo frames at 2528 x 2704 per eye; both eye images captured and visually inspected. Shared texture transport received 1108 texture pairs. This did not submit to a headset.
- Earlier native Studio headset testing was accepted as sharper with depth. End-to-end online Player headset delivery and a simultaneous two-headset session still require validation; SteamVR reported WirelessHmdNotConnected during the Player check.

Each VR user needs SteamVR and their own local helper. Existing published places need the updated game support scripts before they gain multiplayer support.
