# HexagonVR

Native stereo VR for supported games in Hexagon's Windows 2015 client.

**Launch SteamVR and connect your headset before using HexagonVR.** Tested with a Meta Quest 3S connected wirelessly to SteamVR.

# Warning!

This project was created by AI, if you do not like it then you shouldn't use it.

## Download and run

1. Download **HexagonVR.exe** from [Releases](https://github.com/mrboyplayz/HexagonVR/releases).
2. Launch SteamVR and connect your headset/controllers.
3. Open HexagonVR. The console will tell you `enter a game with support for hexagonVR`.
4. Join a game with the HexagonVR scripts installed. The helper detects support and starts VR locally.

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

Point at the 3D menu with the right controller and pull its trigger. Settings includes a live **Arm Forward** adjustment. The default moves the arm anchor 10 cm along controller aim. The keyboard enters your selected text through the normal game chat box.

Use `/vr` or `/unvr` to toggle VR manually. A connected helper enables it automatically when tracking starts.

## Add support to your game

Drag an XML `.rbxlx` place onto `Add-VR-To-Place.cmd` from the full release ZIP. It creates a separate `-VR.rbxlx` copy. Publish that copy to Hexagon using the 2015 client version.

The source alternative is:

```powershell
python bridge.py --install MyGame.rbxlx
```

The installer adds the server/client scripts and menu modules from `roblox/`. `VRConfig.AllowedUserIds = {}` permits all players. Set a list of numeric IDs to restrict access. Keep `AutoEnable = false` so ordinary PC players retain their normal rigs; the local client requests VR after receiving valid headset tracking.

R6 characters are required. The helper supports the exact Player and Studio executable hashes in the source. It does not add tracked VR avatars to games without the support scripts.

## Studio test

Run `HexagonVR.exe --studio-test` or `Start-Studio-Test.cmd` from the full ZIP. It opens the bundled offline test in an installed supported Hexagon Studio and shows the menu automatically. SteamVR and the headset must be connected.

## Rendering and client access

The native module draws scene geometry separately for each eye into Direct3D 11 GPU textures, using the headset's projections and eye separation. Shared GPU textures go to SteamVR with the pose associated with each rendered frame. The native view does not use desktop capture. Eye resolution follows SteamVR's recommendation; the tested Quest session used 2528×2704 per eye.

**This modifies the running client:** the helper loads a graphics module, hooks Direct3D calls, and reads/writes the game-created local pose mailbox. It checks the executable hash before loading the module. It does not replace the game executable on disk. The hooks stay loaded until the game exits; stereo GPU work stops when the helper's heartbeat expires.

This is a beta. Some screen-space effects and ordinary 2D CoreGui screens are outside the native path. The game-created 3D menu supplies VR controls. Native display has been tested in Studio, and the actual online Player produced separate full-resolution GPU eye images in a test using cached Quest calibration and simulated tracking. End-to-end online Player headset delivery is still pending because the wireless headset was disconnected during that check. The multi-player server logic has automated isolation tests; a simultaneous two-headset online session still needs validation. Reopen the game after changing headset eye configuration or native resolution.

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
