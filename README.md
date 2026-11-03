# HexagonVR

Native stereo VR for supported games in Hexagon's Windows 2015 client.

**Launch SteamVR and connect your headset before using HexagonVR.** Tested with a Meta Quest 3S connected wirelessly to SteamVR.

# Warning!

This project was created by AI, if you do not like it then you shouldn't use it.

## Download and run

1. Download **HexagonVR.exe** from [Releases](https://github.com/mrboyplayz/HexagonVR/releases). Install the regular Hexagon 2015 client first. The chat/history changes on `main` are awaiting a live server check before the next binary release.
2. Launch SteamVR and connect your headset/controllers.
3. Open HexagonVR **before joining the game**. The console will tell you `enter a game with support for hexagonVR`.
4. Use the normal Hexagon website Play button for a game with the support scripts installed. HexagonVR starts the verified 2015 client with the renderer initialized before its shaders. Tracking and headset presentation begin after the game reports that its VR camera is active.

If the game was already open without HexagonVR, keep the helper open and rejoin through Hexagon. The helper does not close your game automatically. It can reconnect to a game whose native renderer is already running.

While the helper is running it temporarily routes the Windows `hexagon-player:` launch command through HexagonVR for early initialization. The previous per-user association is backed up and restored when the helper exits. If the helper was interrupted, the next launch restores the previous association and uses the original launcher. Other client versions and launch modes are forwarded to the original launcher. No administrator access is required. Launch tickets pass through an authenticated local pipe and stdin; the helper does not save them or read browser cookies.

Several players can use VR in the same server. **Each VR player runs their own helper and SteamVR on their own PC.** PC players can join normally without a helper. VR rigs, pose limits, tracking timeouts, and cleanup are independent for each player.

## Controls

| Control | Action |
| --- | --- |
| Left stick | Walk |
| Right stick | Snap turn |
| A | Jump |
| X | Recenter |
| Y | Open/close menu |
| B | Chat and keyboard |
| Right trigger | Select a menu button or use an equipped tool |

Point at the 3D menu with the right controller and pull its trigger. Settings includes a live **Arm Forward** adjustment. The default moves the arm anchor 10 cm along controller aim.

The keyboard sends public chat through the game's server, without desktop keyboard input or window focus. The server filters a separate copy for each recipient; filtering failures keep your draft and show an error. Enter clears the draft only after the server confirms it. Both PC and VR players with the support scripts receive these messages. Other chat commands, including whispers, use the ordinary game chat box; `/vr` and `/unvr` also work on the VR keyboard.

Chat keeps the messages received during your session, including across character respawns. Use the right stick or **Older / Newer / Latest** to read history, including wrapped long messages. The player list updates as players join or leave; use the right stick or **Previous / Next** to reach everyone. Chat from before you joined cannot be recovered by this client.

Use `/vr` or `/unvr` to toggle VR manually. A connected helper requests VR automatically when tracking starts. Repeated enable requests are idempotent, so network delays cannot turn VR off again.

## Add support to your game

Drag an XML `.rbxlx` place onto `Add-VR-To-Place.cmd` from the full release ZIP. It creates a separate `-VR.rbxlx` copy. Publish that copy to Hexagon using the 2015 client version.

The source alternative is:

```powershell
python bridge.py --install MyGame.rbxlx
```

The installer adds the server/client scripts and menu modules from `roblox/`. Publish the updated scripts and join a fresh server to use the new chat and menu features; an already running server retains its loaded scripts. `VRConfig.AllowedUserIds = {}` permits all players. Set a list of numeric IDs to restrict access. Keep `AutoEnable = false` so ordinary PC players retain their normal rigs; the local client requests VR after receiving valid headset tracking.

R6 characters are required. The helper supports the exact Player and Studio executable hashes in the source. It does not add tracked VR avatars to games without the support scripts.

## Studio test

Run `HexagonVR.exe --studio-test` or `Start-Studio-Test.cmd` from the full ZIP. It opens the bundled offline test in an installed supported Hexagon Studio and shows the menu automatically. SteamVR and the headset must be connected.

## Rendering and client access

The native module draws scene geometry separately for each eye into Direct3D 11 GPU textures, using the headset's projections and eye separation. Shared GPU textures go to SteamVR with the pose associated with each rendered frame. The native view does not use desktop capture. Eye resolution follows SteamVR's recommendation; the tested Quest session used 2528×2704 per eye.

**This modifies the running client:** the startup loader loads a graphics module into its own newly created, verified client before shader creation. That module hooks Direct3D calls; the helper reads/writes the game-created local pose mailbox. It checks the executable hash before loading the module. Late injection into an already running uninitialized game is no longer used. It does not replace the game executable on disk. The hooks stay loaded until the game exits; stereo GPU work stops when the helper's heartbeat expires.

This is a beta. Some screen-space effects and ordinary 2D CoreGui screens are outside the native path. The game-created 3D menu supplies VR controls. The user confirmed that the actual online Player view now looks like Studio with early graphics initialization and an active VR camera. The multi-player server logic has automated isolation tests; a simultaneous two-headset online session still needs validation. Reopen the game after changing headset eye configuration or native resolution.

The headset stays on the SteamVR background while the game VR camera is inactive. Updated support scripts provide an explicit camera-active acknowledgement.

The previous monoscopic mode is available with `--capture-preview`; native failures do not silently switch to it.

## Build from source

Windows x64 and Python 3.13 are required:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python build.py
```

The build downloads a pinned LLVM-MinGW compiler archive, verifies its SHA-256, builds the 32-bit graphics module/loader and 64-bit texture host, generates the example place, and bundles the EXE. Outputs are in `dist/`. A compiler override is available with `--toolchain PATH`.

```powershell
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

The build runs the native stereo-matrix test as well. GitHub Actions performs a Windows build and unit tests. Private account credentials, runtime settings, game-client executables, and logs are excluded from this repository.

## Files and licenses

- `roblox/`: multi-player server, local tracking, menu, and hosted texture mapping.
- `native/`: Direct3D renderer, verified-target loader, shared texture host, and math test.
- Python files: SteamVR tracking, local transport, native presentation, installer, and chat actions.
- `vendor/minhook/`: pinned MinHook source and its license.

Project code is MIT licensed. Third-party notices are in `native/THIRD-PARTY.md`. Menu textures are referenced through Hexagon asset URLs; the original client image files are not redistributed in the source tree.
