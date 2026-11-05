# v0.4.0-beta.1 — fixed support grips, M16, and scoped AWP

Close the old helper and game, open this EXE, then join a fresh server of [Hexagon VR Test](https://www.hexagon.pw/games/105279). Both the updated place scripts and native renderer are needed for the scope.

- Both hands still steer aim. The support hand uses a preset fore-end position and wrist rotation, with a short engagement blend. Its wrist cannot freely roll the rifle. Shoulder-to-wrist arm poses let the body move while the hand remains attached. The shared avatar hand uses the same grip.
- Adds the M16 with 30-round magazines, manual charging handle, automatic fire, and empty-bolt hold-open.
- Adds the AWP with 10-round magazines and a manual bolt: lift, pull back, push forward, lower to lock. Spent casings eject when opening the bolt. Releasing an open bolt leaves it open, and each shot requires another cycle.
- Adds a native 4x picture-in-picture scope with a mil-dot reticle, eye-box alignment, depth-tested lens placement, and obstruction checks. The surrounding headset projection remains unchanged. The scope automatically activates when you look through it.
- Uses Marketplace rifle models and recordings, converted to legacy meshes and uploaded to Roblox. All 37 public asset URLs were verified through Hexagon. The public download contains the offline demo; the online map stays private.

Validation: 98 unit tests; native geometry tests; weapon, fixed-grip, arm, rifle-loading, manual bolt/casing, scope-alignment, and multiplayer checks; real Direct3D scope capture with magnified target measurement. Physical headset feel still needs user testing.
