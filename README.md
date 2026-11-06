# HexagonVR

## Physical weapon build

This build adds physical hats, a crowbar, pistol, AK-47, M16, and scoped AWP to the existing 2015 VR support. Use the **new EXE and updated place together** for the current controls and controller vibration. Close the older helper and the game completely, start the new helper, then join a fresh server after installing an updated place. **Every VR player must upgrade: v0.2.1-beta.1 and earlier do not send grip-button input.**

- Hold either controller's grip near a ground pickup to grab it. Nearby surfaces have a 2.5-stud grab radius. Point at a pickup within 6 studs for distance grab, so you can pick it up without bending to the floor. Holding grip keeps trying as you approach. Release it to drop or throw.
- Touch your hat or another player's hat and hold grip to remove it. Your hand keeps the point where you grabbed it, so wrist rotation pivots the hat around that point. Release it near your head or another player's head to equip it there. Release it elsewhere for a physical ground pickup. The same original hat moves between players; everyone sees the transfer. Hats require a nearby touch rather than distance grab.
- The crowbar is 4.2 studs long and points forward from its shaft grip. Its original Marketplace texture coordinates are preserved. Swing it into a player or NPC. Slow contact does no damage; repeated contact is limited by a cooldown.
- Hold the pistol in either hand. Keep grip held on the magazine, guide its top into the bottom opening, then push it up the well until it clicks. It remains in your hand during insertion and only locks when fully seated. Releasing halfway drops it. AK magazines follow an assisted rock-in path.
- Grasp the slide on top, pull it back a few centimeters, then release it or move your hand forward. The enlarged grab area and assisted slide travel make this easier. The AK charging handle works the same way on the receiver's right side.
- Pull the trigger on the hand holding the pistol to fire one shot. Release and pull again for the next shot. Hold the AK trigger for automatic fire. Shots have immediate local sound, muzzle flash, spring recoil, controller vibration, and textured spinning cartridge cases. Damage and ammo remain server controlled.
- Grasp the bottom of the inserted magazine and draw it down the well to remove it. The magazine follows your hand during extraction. A chambered round remains until fired or ejected by racking the slide.
- The slide stays back after the final round. Insert another magazine, then pull and release the slide.
- The AK uses its own 30-round magazines and rejects pistol magazines. Its bolt returns forward when empty. Grip the fore-end with your other hand to stabilize aiming and reduce recoil. The support hand uses a preset position and wrist angle on the fore-end. Both controller positions steer aim while the trigger hand stays on the rear grip.
- Recoil now has visible rise, rearward kick, and a small sideways impulse. Both virtual hands stay on the weapon. Two hands reduce the kick; the server's firing direction follows the recoiling muzzle.
- Held weapons, slides, and magazines use a private local view so replicated position corrections cannot pull them away from your hands. Small tracking movements are filtered, while deliberate movements and wrist roll remain responsive. The seated magazine follows the same gun pose every frame. Grip changes send immediately; short controller tracking and squeeze-button dropouts no longer repeatedly detach the grip. The support grip is predicted locally, then confirmed by the server.
- The foregrip engages locally on squeeze at an authored hand position and wrist rotation. Both hand positions steer the gun; support-wrist rotation cannot roll it freely. Initial alignment eases in briefly, then the hand line controls aim directly. The virtual support hand stays on the preset grip even as your shoulder moves. Other players see the same attached hand.
- Fixes idle pullback caused by invisible head/torso copies in the private arm model. Those copies are removed, and the appearance Humanoid is passive. The actual avatar body still follows the headset. An unanchored engine test verifies standing, physical head turns, overlapping arms, walking, stopping, and jumping.
- Your first-person arms use shoulder-to-wrist poses with 45% transparency and a slimmer first-person profile. The wrists stay on tracked controllers or weapon grips while the shoulders follow the torso. Shared avatar arms retain their original size and transparency.
- The M16 uses 30-round M16 magazines. Push one into the magwell, then grip its rear charging handle, draw it back, and release or return it forward. Hold the trigger for automatic fire. It locks open when empty.
- The AWP uses 10-round AWP magazines and a manual bolt. Grip the bolt handle, lift it, draw it back, push it forward, then lower it to lock. Each shot leaves the spent casing inside until you open the bolt. An open bolt stays open when released. It will not auto-feed or fire another shot without a full cycle.
- Bring the AWP scope behind your aiming eye and look through it for a 4x magnified image with a mil-dot reticle. Magnification stays inside the lens; the surrounding headset projection is unchanged. Moving outside the eye box, dropping the gun, opening the menu, or obstructing the optic disables the scope image. This requires the current native renderer; the scope starts automatically without another button.
- Only worn hats and hats handled or dropped by a VR player are retained. Other loose hats, including nested ground hats and ordinary avatar drops, are cleaned up. VR provenance is recorded by the server when the grip is accepted.
- Each magazine has one final render pose. Mounted state takes priority during ownership updates; removal captures the local grip, preserves that grip when detached, and ignores delayed server grip changes during the same hold. Loading measures travel in the rendered gun's frame and bridges short guide-to-mount update gaps.
- Reload alignment starts locally as the magazine enters the well, then the server confirms it. At the mouth it keeps your hand's angle; assistance ramps up as you physically push the magazine in. Seating eases through the last gap. A previous magazine's progress or grip value cannot snap a fresh reload into place.
- Dropping sends the displayed weapon pose and bounded throw velocity to the server. Shared parts become visible again, and their physics stay server owned. Remote clients do not write another player's weapon transforms. This test place explicitly uses Filtering Disabled.
- Y is the only menu shortcut; B and X are unassigned. Chat and recentering are available inside the menu. The Studio test starts with the menu closed.

The kit spawns a crowbar, an unloaded pistol with four 12-round magazines, an unloaded AK-47 with three 30-round magazines, an M16 with three 30-round magazines, and an AWP with three 10-round magazines near `(0, 0, -5)`. Change `VRConfig.Weapons.SpawnPosition` for your map. The offline demo includes two respawning practice targets. Damage, capacity, range, cooldowns, and respawn time are configurable. Pickups are shared; ownership, ammunition, hit checks, and cleanup run on the server. Opening the VR menu drops held pickups and suppresses weapon actions.

Models and audio come from the [classic Crowbar](https://create.roblox.com/store/asset/61044725/Crowbar), [Roblox Pistol](https://create.roblox.com/store/asset/4842197274/Pistol), [AK-47 by Regole_CKC](https://create.roblox.com/store/asset/8974619704/AK47), and [AK47 sound pack](https://create.roblox.com/store/asset/7953557310). The new rifles use [M16 by OnlyJay_WasHere](https://create.roblox.com/store/asset/13380361404), [M16 charging-handle geometry/sounds](https://create.roblox.com/store/asset/5171779709), [AWP by ZombehTV, MuYhet, and TurboFusion](https://create.roblox.com/store/asset/1170862415), and [AWP bolt sounds](https://create.roblox.com/store/asset/9085637274). Original IDs, files, and hashes are recorded in `assets/MARKETPLACE-SOURCES.json`. Imported scripts are excluded. Mesh axes and scale are adapted to VR. The offline audio is converted to MP3 with a peak limiter; online delivery uses the original public recordings.

The live place uses public Roblox assets through Hexagon's delivery endpoint. The fifteen converted legacy meshes were uploaded to Roblox as Open Use and verified byte-for-byte with anonymous downloads. Public textures and sounds were verified as well; all 37 URLs are recorded in `assets/PUBLIC-ASSETS.json`. **PC players can see and hear weapons without an asset installer. Each VR player still needs the helper for tracking.** The separate offline demo uses bundled local files installed by the helper.

The scripts were published to [Hexagon VR Test](https://www.hexagon.pw/games/105279), with Filtering Disabled. The downloaded published version was verified against the local file by SHA-256; see `PUBLISH-RECEIPT.json` for its version. Join a fresh server to load the updated scripts. The public kit includes `VR-Demo.rbxlx` for a separate offline test; the online map remains private. The real 2015 engine passed weapon, moving-grip, and hat interaction checks. Two separate network clients passed independent weapon pickup, visibility, dropped physics, and hat transfers in FD. Physical headset/controller feel and a simultaneous live two-headset session still need user verification.

Native stereo VR for supported games in Hexagon's Windows 2015 client.

**Launch SteamVR and connect your headset before using HexagonVR.** Tested with a Meta Quest 3S and a Meta Quest 3 connected wirelessly to SteamVR.

# Warning!

This project was created by AI, if you do not like it then you shouldn't use it.

## Download and run

1. Download **HexagonVR.exe** from [Releases](https://github.com/mrboyplayz/HexagonVR/releases/tag/v0.4.1-beta.1). Install the regular Hexagon 2015 client first. This is a beta; live filtering for the new VR chat keyboard and simultaneous physical headsets still need user verification.
2. Launch SteamVR and connect your headset/controllers.
3. Open HexagonVR **before joining the game**. The console will tell you `enter a game with support for hexagonVR`.
4. Use the normal Hexagon website Play button for a game with the support scripts installed. HexagonVR starts the verified 2015 client with the renderer initialized before its shaders. Tracking and headset presentation begin after the game reports that its VR camera is active.

If the game was already open without HexagonVR, keep the helper open and rejoin through Hexagon. The helper does not close your game automatically. It can reconnect to a game whose native renderer is already running.

When upgrading from v0.2.1-beta.1 or earlier, close the existing Hexagon game and the old helper completely, then open the new helper before joining again. Restarting just the helper leaves the old graphics module loaded in the existing game. An old helper cannot grab weapons or hats because it does not transmit grips; the updated place alone cannot add that input.

While the helper is running it temporarily routes the Windows `hexagon-player:` launch command through HexagonVR for early initialization. The previous per-user association is backed up and restored when the helper exits. If the helper was interrupted, the next launch restores the previous association and uses the original launcher. Other client versions and launch modes are forwarded to the original launcher. No administrator access is required. Launch tickets pass through an authenticated local pipe and stdin; the helper does not save them or read browser cookies.

Launcher recovery rejects backups that point to another HexagonVR executable, which previously could leave VR registered as the normal launcher. A stale redirect forwards to the real Hexagon launcher and repairs itself. The protocol dispatch process stays hidden; explicitly starting HexagonVR still shows its status console. Close old helpers from Downloads before using this build. Physical pickups need both the current helper and an updated place in a fresh server; the helper cannot update an already running game's server scripts.

Several players can use VR in the same server. **Each VR player runs their own helper and SteamVR on their own PC.** PC players can join normally without a helper. VR rigs, pose limits, tracking timeouts, and cleanup are independent for each player.

Active headset/controller use is reported to the connected game's ordinary input system every 30 seconds, so VR play counts as activity. Reports require the VR camera and recent tracked movement, turning, walking, firing, or button changes. Static tracking noise does not keep reporting activity. Input delivery was verified in the 2015 engine, with another client receiving none; the live Player's 20-minute timeout still needs a real-session check.

## Controls

| Control | Action |
| --- | --- |
| Left stick | Walk |
| Right stick | Hold left/right for smooth turn; speed adjustable in Settings |
| A | Jump |
| Y | Open/close menu |
| B / X | Unassigned |
| Menu tabs | Chat keyboard and Settings → Recenter |
| Right trigger | Select a menu button or use an equipped tool |
| Either grip | Hold to grab a weapon, magazine, or hat; release to drop |
| Release a hat near a head | Equip it on that player |
| Holding hand's trigger | Fire pistol/AWP once / hold for AK or M16 automatic fire |

Point at the 3D menu with the right controller and pull its trigger. Open **Y → Settings → Turn Speed** and use **− / +** to change smooth turning from 15 to 180 degrees/s (default 65). It takes effect immediately and is saved locally for the next launch. Partial stick tilt turns more slowly. Settings also includes a live **Arm Forward** adjustment. The default moves the arm anchor 10 cm along controller aim.

The torso partially follows head yaw and follows the tracked neck position when leaning. The avatar head sits behind the tracked eyes, with the camera 0.45 studs forward and 0.12 studs above the head center. The headset view retains direct tracking. Smooth turns pivot around the eyes, so room-scale head offsets do not orbit around the character root. The original R6 body joint is restored when VR ends.

Torso follow unwraps head yaw across the rear-facing boundary. Looking around physically cannot move the private arms through the torso; their positions remain tied to tracking while the body twists underneath them.

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

Run `HexagonVR.exe --studio-test` or `Start-Studio-Test.cmd` from the full ZIP. It opens the bundled offline test in an installed supported Hexagon Studio with the menu closed. Press Y to open it. Studio can open before the headset is ready; tracking starts when SteamVR detects it.

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

With the supported Hexagon 2015 Studio installed, run `python tests/run_weapon_motion.py` for moving-grip engine checks. It opens an isolated hidden test, uses synthetic hand poses, and closes only its own process. The suite covers rear-wrist yaw, close/crossed hands, combined gun motion, stale magazine ownership/grip updates, extraction, loading, and interrupted reload cleanup. Headset feel still needs physical testing.

`python tests/run_weapon_network.py` starts an isolated local server and two hidden Studio clients. It checks FD, public mesh URLs, remote held-weapon visibility, private visual isolation, and dropped weapon visibility/physics. It closes only its own test processes.

`python tests/run_hat_interactions.py` checks off-center pivots, multipart hats, drops, re-equipping, and legacy touch-pickup suppression. `python tests/run_hat_network.py` checks taking another player's hat, swapping wearers, placing it on somebody else, ground drops, and returning its original fit with two separate clients.

`python tests/run_vr_arms.py` checks private arm transparency, stationary controllers while turning/leaning, torso yaw continuity, and cleanup when leaving VR.

## Files and licenses

- `roblox/`: multi-player server, local tracking, menu, and hosted texture mapping.
- `native/`: Direct3D renderer, verified-target loader, shared texture host, and math test.
- Python files: SteamVR tracking, local transport, native presentation, installer, and chat actions.
- `vendor/minhook/`: pinned MinHook source and its license.

Project code is MIT licensed. Third-party notices are in `native/THIRD-PARTY.md`. Menu textures are referenced through Hexagon asset URLs; the original client image files are not redistributed in the source tree.

`python tests/run_new_rifles.py` checks M16 loading and the AWP manual bolt/casing/scope cycle. After a native build, `python tests/run_scope_gpu.py` checks magnification using isolated hidden Studio GPU rendering, without a headset compositor.
