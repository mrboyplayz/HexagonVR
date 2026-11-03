# Release validation

## v0.2.1-beta.1

- The user reported double vision/warping in the normal late-attached Player. Disabling render-pose submission did not improve it and was reverted.
- Early Player initialization (the same ordering used in Studio), with the game VR camera explicitly active, received the user confirmation: **Looks like Studio now**. The confirmed live Player remains running; it was not replaced for packaging tests.
- The permanent launch route uses the normal Hexagon launch URI, an authenticated per-user pipe, and a loader-owned verified 2015 Player. Normal exit restores the previous Windows launch command. Unit tests cover exact restoration, preserving external association changes, real Windows pipe transport, URI validation, and sending tickets through stdin rather than files.
- Repeated game enable requests remain enabled. Explicit camera state and fresh acknowledgements gate native presentation; older game support retains a viewport-based compatibility check.
- 55 automated tests pass, covering multiplayer isolation, native launch/transport, focus-independent chat requests, per-recipient filtering failures, history persistence, late joins, privacy, wrapped-message scrolling, and roster pagination. Native C++ stereo geometry passes. An isolated native Studio regression test rendered 239 stereo frames at a diagnostic 64 x 64 resolution, verified deferred headset configuration, and received the new camera-active acknowledgement without touching the live user Player.
- The real Windows `hexagon-player:` route successfully started the early-initialized online Player. Its native GPU renderer and local tracking remained active in the user's game.
- An isolated 2015 Studio engine test exercised the chat request, server receipt, draft clearing, and local display without desktop keyboard input. It used a deterministic test-only filter stub, so this does **not** validate Hexagon's live filtering service. The same engine test retained 151 messages across menu recreation, reached both ends of wrapped history, and confirmed that text-layout events no longer reset manual scrolling. Test stubs are absent from the shipped game scripts.
- Updated scripts are published to the main test place and a separate fresh preview place. Live server filtering and the user's new menu checks remain pending; the existing occupied server was left running.
- The rebuilt standalone EXE passes help, SteamVR/headset detection, and place installation checks. Its installed place includes the new chat modules and scroll controls without test stubs.
- A simultaneous two-headset online session remains unverified.

## v0.2.0-beta.1

- 17 automated Python/Lua tests pass on Windows with Python 3.13, including two simultaneous server sessions, independent pose/rate limits, isolated tracking timeout, reset, death, respawn, disconnect, allowlist behavior, and invalid pose rejection.
- Native C++ stereo-matrix test passes as part of the build.
- Standalone EXE reports installed SteamVR and a present headset.
- Standalone place installer produces the multiplayer scripts, unrestricted default allowlist, PC-safe AutoEnable setting, and eight hosted menu asset references.
- Standalone EXE opens its embedded Studio demo with simulated tracking, connects to the actual client mailbox, and receives render acknowledgements and camera viewport data. This checks packaging and local transport without claiming a headset visual test of this release.
- Actual online 2015 Player GPU rendering verified using the release native modules, cached Quest calibration, and simulated tracking: 802 native stereo frames at 2528 x 2704 per eye; both eye images captured and visually inspected. Shared texture transport received 1108 texture pairs. This did not submit to a headset.
- Earlier native Studio headset testing was accepted as sharper with depth. End-to-end online Player headset delivery and a simultaneous two-headset session still require validation; SteamVR reported WirelessHmdNotConnected during the Player check.

Each VR user needs SteamVR and their own local helper. Existing published places need the updated game support scripts before they gain multiplayer support.
