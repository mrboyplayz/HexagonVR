# v0.4.1-beta.1 - Fix idle pullback

Fixes the character being pushed while the headset/controllers are still and no movement input is pressed. The invisible head and torso copies inside the first-person arm model became collidable in the legacy engine. Those copies are removed, and the appearance Humanoid uses a passive physics state. Shoulder-following arms and the actual avatar body remain.

The fix is published to [Hexagon VR Test](https://www.hexagon.pw/games/105279), version 17. Leave the old server and join a fresh server. The current v0.4.0 helper also works with the corrected online place; this download additionally updates the bundled offline demo and installer.

Validation: 98 unit tests; first-person arm tracking checks; a freely simulated R6 character stays still with neutral input, head turns, and overlapping arms. Walking, stopping, jumping, and VR cleanup also pass. Physical headset feel still needs user testing.
