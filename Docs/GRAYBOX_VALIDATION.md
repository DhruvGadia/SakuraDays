# Sakura street graybox

Created and tested on 5 November 2026 in Unreal Engine 5.8.4.

Saved map, route results, and screenshots were reviewed on 14 November 2026 when this task resumed. No new playtest was run on that date. The final map file is dated 5 November, before the final captures. A compact copy of the recorded results is retained in [GRAYBOX_TEST_RESULTS.json](GRAYBOX_TEST_RESULTS.json).

## Opening and scope

Open `/Game/SakuraDays/Maps/L_SakuraStreet` and press Play. The original Third Person Blueprint game mode, character, input mappings, and gameplay camera are reused. The original template map and project startup maps are unchanged. Hardware ray tracing remains disabled.

The map contains 63 editor actors. All new meshes and materials live in the SakuraDays namespace. Graybox materials are in `/Game/SakuraDays/Environment/Graybox`; geometry uses the engine's cube, cylinder, and sphere meshes. Actors are grouped under `SakuraGraybox` in the Outliner. No detailed buildings, final foliage, NPC, dialogue, or petal effects are included.

## Scale and layout

Unreal units are centimeters. +X runs down the street; -Y is the café side.

| Element | Dimensions / placement |
|---|---|
| Site | 60 m long by 34 m wide; X -1000 to 5000 cm |
| Road | 6 m wide, Y -150 to 450 cm; surface Z 0 |
| Sidewalks | 3 m wide on each side; surface Z 15 cm |
| Café | 12 m frontage by 7 m depth, 6 m high; center X 300, Y -850 cm |
| Café door marker | 1.2 m wide by 2.2 m high; closed façade |
| House 01 | 9 by 9 m mass; center X 1900, Y -1000 cm |
| House 02 | 10 by 8 m mass; center X 1100, Y 1220 cm |
| House 03 | 10 by 8.5 m mass; center X 3300, Y 1250 cm |
| Houses | 6 m high; plot pads extend 0.8 m beyond mass on each side |
| Trees | Seven markers; 40 cm diameter colliding trunks; 3.6 m wide non-colliding crown volumes |
| Spawn | X 0, Y -320, Z 115 cm, looking along +X |

The café occupies the left foreground as in the supplied first-street target. Houses and alternating trees establish depth down the road. The separate Main Street reference informs the café-facing walk and repeated frontage rhythm. The graybox approximates these spatial relationships; it does not reproduce their finished architecture or art style.

Ground, sidewalks, building masses, trunks, roofs, awning, and perimeter use BlockAll collision. Flat road markings, door/window markers, tree pits, and crowns have no collision. Buildings are solid location markers. The raised curbs can be stepped over by the existing character. Tree placement leaves a continuous pedestrian route on both sidewalks.

## Reference camera and captures

`CAM_SakuraStreet_Reference`: location (-480, -180, 210) cm; pitch -4°, yaw -7°, roll 0°; horizontal FOV 75°; constrained 16:9. It is not automatically activated during normal play. Select and Pilot it for editor framing. The capture validation temporarily sets the PIE controller's view target to this camera, then restores the existing Third Person pawn camera.

Real 1920×1080 Unreal PIE captures are stored in `Docs/Images/`:

- `SakuraStreet_Graybox_Reference.png`: fixed reference camera with the spawned playable character.
- `SakuraStreet_Graybox_Gameplay.png`: ordinary Third Person camera at spawn.

These are engine screenshots, not generated illustrations. The previously prepared Dream Loop target and reference artwork are unchanged.

## Navigation verification

The final route run passed all 19 waypoint/contact checks, covering approximately 225.95 m. A temporary Slate callback supplied movement directions to the existing character's `add_movement_input` during real Play-in-Editor. CharacterMovement handled speed, gravity, floor detection, stepping, and collision. The route did not teleport the player or replace its controller. This validates traversability; it is not an NPC navigation-mesh or controller usability test.

Coverage:

- Spawn to café approach, then along the left sidewalk and House 01 frontage.
- Continue to the far end and cross the road onto the right sidewalk.
- Reach House 03 and House 02 frontages, then return along the right sidewalk.
- Cross the road at the near end and return to the café.
- Push against the café façade and far barrier: character stopped at their capsule contact boundaries.
- Approach the second tree trunk: minimum horizontal center separation was 54.93 cm, consistent with its 20 cm radius plus the character capsule's approximately 35 cm radius. It deflects the character around the trunk without penetration.
- Return along the sidewalk to spawn.

The first trunk assertion incorrectly expected the character to remain stopped against a round obstacle. Recorded movement showed it sliding around the trunk. The corrected contact test measures minimum separation, and the complete route was rerun successfully. The only subsequent geometry adjustment lowered non-colliding crown markers by 30 cm so they meet the trunks; walking collision did not change.

After the final capture pass, brief W and D keyboard inputs and Space were exercised through the normal gameplay viewport. Jump and landing were observed. The separate movement-monitor file on disk predates this final keyboard check, so it is not evidence of measured movement distances for that check.

Detailed samples and test scripts are local generated evidence under ignored `Saved/GrayboxValidation/` and `Saved/`. A byte-for-byte copy of the pre-graybox map is retained locally in `Saved/GrayboxBackup/`. The original template, character, and input assets have no Git changes. No packaging or performance benchmark was performed.

## Remaining layout issues

1. The road ends at a visible safety barrier. A later bend, background façade, or other deliberate terminus should conceal this edge and better match the reference's continuing street.
2. House plots are deliberately sparse. The gaps need a later decision on gardens, fences, alleys, or additional frontage; preserve the validated walkways when filling them.
3. Café and house door markers are not entrances. The café approach is reachable, but interior access, doorway thresholds, and an NPC interaction area still need design and testing.
4. Trees are volume markers. Their final silhouettes and canopies must be composed around the café, character, and street sightline; the first obstructing curb tree was moved to the café corner during this pass.
5. The camera is a repeatable graybox approximation. The reference's road curvature, dense frontage, and distant landmark are not built. Final framing will need another comparison after those decisions.
6. Lighting, aliasing, and smooth graybox materials remain provisional. They are sufficient to read collision and scale, but do not represent the chosen anime art direction or measured desktop performance.
