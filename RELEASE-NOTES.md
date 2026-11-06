# v0.4.2-beta.1 - Gun-only shoulder poses

Shoulder-to-grip arm poses now apply only to hands holding a gun or its foregrip. Empty hands and hands holding hats, crowbars, or magazines keep their normal controller-following rotation and arm length. Releasing a foregrip restores that arm immediately. Both hand positions still aim the gun using its fixed support grip.

The idle pullback fix remains. The updated scripts are published to [Hexagon VR Test](https://www.hexagon.pw/games/105279), version 18. Join a fresh server; current v0.4 helpers also work online. This download updates the bundled offline demo and installer.

Validation: 98 unit tests; native gun/free-hand/crowbar pose checks, arm tracking, magazine motion, and unanchored idle/walking/stopping/jumping checks. Physical headset feel still needs user testing.
