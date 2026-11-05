# v0.3.1-beta.1 — two-hand aiming, tracked arms, and activity input

Close the old helper and game, open this EXE, then join a fresh server. The matching scripts are live in [Hexagon VR Test](https://www.hexagon.pw/games/105279), version 15.

- Reworks two-hand aiming: the foregrip engages immediately on squeeze, both hand positions determine pitch/yaw, and the rear wrist controls roll. Removes the 65-degree limit and extra aiming filter. Coincident hands keep the last valid direction; support release eases back to one hand.
- Adds private first-person arms with 45% transparency. Controller/grip poses drive them independently of body physics. Shared arms stay opaque. Removes the default sideways hand offset and fixes torso turning across the rear-facing yaw boundary.
- Reports active VR use to the legacy client's input handler. Delivery is scoped to the connected process and recent VR activity; inactive cameras/tracking and static tracking noise do not keep it active. Repeated input delivery was checked in two isolated processes. The live Player's 20-minute timeout still needs real-session verification.
- Deletes loose hats without server-recorded VR provenance while preserving worn hats and hats handled/dropped through VR. Existing physical hat swaps and head equipping remain supported.

The full ZIP includes the offline demo and installer. The online map remains private. v0.2.1-beta.1 and earlier lack grip input; every VR player should upgrade.

Validation: 91 unit tests; native weapon/moving-grip, body, arm, and hat checks; separate local server plus two Studio clients for weapon pickup and hat transfers; repeated scoped activity-input checks; EXE installer/asset smoke checks. Physical headset feel still needs user testing.
