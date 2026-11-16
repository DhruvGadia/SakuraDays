# SakuraDays art direction

Prompt 13's later supplied campus, riverside, overlook, café, alley, station, sunset and festival references are mapped to the existing street in [the reference update](PROMPT13_REFERENCE_UPDATE.md). Style A/B retain priority; the current street remains a spring-afternoon scene.

SakuraDays should feel like a walk through a sunlit Japanese neighborhood rendered with anime-inspired color, simplified surface detail, and clearly drawn forms. Warm cream buildings, blue-gray roofs, pink sakura, and cool street shadows establish the scene. Utility wires, compact façades, shop signs, and small street props give it a lived-in character.

This guide records visual observations and proposes a future Unreal Engine 5.8 approach. Numerical colors, dimensions, and rendering values below are starting points chosen for production. The images alone cannot establish the original renderer, shaders, camera settings, or asset construction.

The reference hierarchy determines how future visual decisions should be made.

| Reference | Role in SakuraDays |
|---|---|
| Style A | Primary style authority for a whole street, material simplicity, daylight, color relationships, greenery, and distant readability. |
| Style B | Equal primary style authority for nearby buildings, signs, stonework, structural edges, strong accent colors, and weeping sakura. |
| Main Street | Composition reference for the café frontage, receding shop rhythm, tree placement, and pedestrian route. |
| Existing first-street target | A scene proposal to compare against the primary style references. Its café, player route, and sakura placement can inform the milestone layout. |

The supplied first-street target is treated as a reference image. Its appearance has not been verified as a capture of the current Unreal project. Style A and Style B contain interface graphics, and Style B contains a browser fullscreen message. Those overlays are outside the environment art specification. Source files are available locally. [Style A](<C:/Users/HP/Documents/SakuraDays_Codex_Prompt_Pack/References/Style_A.png>) · [Style B](<C:/Users/HP/Documents/SakuraDays_Codex_Prompt_Pack/References/Style_B.png>) · [Main Street](<C:/Users/HP/Downloads/01_Main_Street.png>) · [Existing target](<C:/Users/HP/Documents/SakuraDays_Codex_Prompt_Pack/References/00_First_Street_Target.png>)

**The two primary references agree on simple surfaces and strong spatial structure.** Style A places pale blue-gray siding opposite a warm beige house. Dark roof edges and cables make the street legible, while green roadside strips, yellow road paint, and pink crowns provide distinct color groups. The angular shrubs on the right use large green patches with very little individual leaf detail. Style B brings the same treatment close to the camera. Its cream wall is broad and quiet, while windows, sign borders, stone steps, and the gate use crisp geometric divisions.

Style B permits stronger local saturation than Style A's wide street view. Its vermilion gate, yellow hazard stripes, and dense pink canopy are prominent accents. The shared direction is therefore selective saturation, with most façade area reserved for restrained neutrals. Both images show some soft lighting transitions alongside firmer edges. They support a controlled mixture of smooth and simplified shading.

**Color should be organized by surface and importance.** The following approximate sRGB swatches describe a proposed working palette. They are visual estimates from the displayed references, rather than measured material values. Match the final rendered relationships after exposure and tone mapping.

| Color family | Suggested swatches | Use |
|---|---|---|
| Sky | `#79ACD6`, `#B7D0DF` | Clear blue overhead, lighter toward the horizon. |
| Warm plaster | `#DDC9AD`, `#E8DBCA` | Café upper floor and residential façades. |
| Cool siding | `#A7B5C0`, `#7E889D` | Neighboring houses and shaded secondary walls. |
| Roofs and drawn edges | `#393344`, `#51485A` | Eaves, frames, structural contours, cables, and deep recesses. |
| Wood | `#725548`, `#A37B60` | Café framing, signs, doors, and benches. |
| Road and stone | `#777785`, `#B8B1A9` | Asphalt and paving, with cooler variations in shade. |
| Sakura | `#E9A5CE`, `#F4C7DF`, `#B878A4` | Main bloom color, lit clusters, and shaded interior groups. |
| Greenery | `#78A257`, `#4C7958` | Broad shrub faces and darker interior planes. |
| Painted accents | `#E74D30`, `#D6B340`, `#78B3A0` | Small red signs, yellow markings, and optional green road margins. |
| Shadow family | `#62647D`, `#848398` | Visual targets for cool shade on otherwise neutral surfaces. |

Allocate most of the image to sky, walls, road, and foliage masses. Concentrate the richest pink near the sakura, and a few red or yellow accents near meaningful street features. The café should read through its silhouette, sign, entrance, and relationship to the path. Its identity can be carried by a small warm interior accent.

**Lighting should establish clear, warm daylight with readable cool shade.** Both style references show directional sunlight, distinct shadows beneath roofs, and long enough cast shadows to describe façades, poles, and trees. Their sky contributes open blue fill. Shadowed walls still retain recognizable local color. The references show much less luminous café-window emphasis than the existing target.

For the first lighting study, use a single directional sun and restrained skylight. A sun elevation around 30–45 degrees is a proposed starting range. Choose its azimuth from the café-facing camera so the awning, roof, and trees create useful shadow shapes. Balance illumination and exposure using a cream wall and the road as anchors, then tune pink highlights to preserve blossom detail. Keep bloom subtle and atmospheric haze concentrated in the far distance. Soft cloud streaks suit the sky. A bright spring day should remain readable when the player turns toward the shaded café.

**Anime shading should simplify the value structure while retaining depth.** Style A's shrub planes, Style B's gate, and the broad walls suggest two or three main value families for many objects. Rounded poles and some walls retain gradual transitions. A practical visual target is one main color, a clear shadow family, and a restrained highlight where the material needs it. Small props may use painted color patches. Broad façades need enough illumination variation to show overhangs and adjacent walls.

Dark edges are strongest around roof silhouettes, windows, signs, rails, branch structures, and intersecting architectural planes. Some are actual dark trim or shadowed recesses. The screenshots do not prove that a universal outline shader was used. Model the important dark borders first. Where an added outline is useful, favor a dark plum-gray with thinner treatment on interior seams. A proposed screen-space starting width is about 1 pixel for ordinary edges and 1–2 pixels for a nearby focal silhouette at 1080p. Reduce line strength with distance. Leave enough separation between bloom clusters for sakura crowns to remain pink at street scale.

**Architecture should use believable human scale and economical detail.** Both primary references show compact two- and three-story buildings, plain upper walls, modest roof pitches, shallow setbacks, and readable doors and windows. Style A supplies siding, balcony laundry, a carport, boundary walls, road markings, and utility poles. Style B supplies projecting signs, a shop entrance, an air conditioner, stone steps, a noticeboard, and a small shrine frontage. These are examples of a convincing neighborhood vocabulary. The milestone needs the subset that supports its café and street.

| Element | Proposed modeling scale and treatment |
|---|---|
| Doors and floors | Start with doors around 2.0–2.2 m high and floors around 2.7–3.2 m. Check against the existing player capsule. |
| Shop frontage | Start with a café bay around 4–6 m wide. Give the entrance a clear recess, awning, and sign. |
| Walking route | Aim for roughly 1.8–2.5 m of usable width at the café, adjusting for the player and camera. Place signs and pots outside the main movement corridor. |
| Street | Begin around 5–6 m for the roadway if using the target's vehicular layout. Adjust from playable camera tests. |
| Roofs and windows | Give eaves enough thickness to cast a readable shadow. Use bold window frames and a small set of repeated window sizes. |
| Detail density | Prioritize a few recognizably shaped fixtures at eye level. Let upper walls contain larger uninterrupted areas. |

These are gameplay blockout proposals, not measurements recovered from the references. Preserve everyday scale relationships as objects are simplified. Bevels should support readable silhouettes and lighting. Siding seams, roof courses, and pavement joints should remain subordinate to the overall building. Signs should use authored, legible lettering with reviewed Japanese text. The main reference's dense timber shopfronts can guide shop placement, while the primary references determine the amount of surface detail.

**Foliage should read as designed clusters with distinct silhouettes.** Style A uses broad rounded sakura crowns with visible branching and gaps between groups. Style B emphasizes a weeping form, with long descending branches and hanging pink masses. Those two tree shapes can coexist along the street. Use larger crowns to frame the route and reserve a memorable weeping tree for a focal location near the café.

Build each tree from a readable dark trunk, a limited set of main branches, and several overlapping bloom clusters. Give the crown an asymmetric silhouette. Let selected gaps reveal sky and dark branch lines. Use blush and lavender-pink variation across groups, with modest pale highlights. Nearby blossoms can resolve into simple petal shapes. Distant crowns should retain large pink areas. The primary references support dense flowers, especially in Style B, but their flowers are less individually articulated than the large foreground blossoms in the existing target.

The shrubs are especially important to the style match. Use a few rounded or faceted masses, broad green color variation, and occasional lighter patches. Place pot plants as recognizable groups of stems and leaves. Scale down fine leaf veins, bark noise, and tiny specular highlights so they do not dominate the street view.

Falling petals should appear as occasional drifting silhouettes. Use varied orientation, slow lateral motion, uneven spacing, and a small number of close foreground petals. Accumulations along curbs and tree bases should form a few readable patches. Keep the NPC's face and dialogue region visually clear. The still images establish petal shape and placement, while motion speed and density will require an in-engine study.

**Shadows, materials, and textures should reinforce the large forms.** The pavement, plaster, and stone in Style B have broad matte areas with restrained surface variation. Contact shade under the shop awning and at the base of props gives depth. Street shadows in Style A form broad cool regions. Fine foliage shadows can enrich a focal patch of pavement, but the larger shadow pattern should remain readable while moving.

| Surface | Appearance target | Proposed material starting point |
|---|---|---|
| Plaster, stone, asphalt | Matte, low texture contrast, clear color grouping | Metallic 0, roughness roughly 0.75–0.95, subtle normal detail. |
| Timber | A few directional grain strokes and broad color changes | Roughness roughly 0.65–0.9, restrained normal amplitude. |
| Painted doors, signs, fixtures | Clean local color, controlled highlights | Roughness roughly 0.5–0.8. |
| Windows | Broad pale reflection shapes and dark framing | Tune a simple glass study from the café camera. Balance interior visibility against sky reflection. |
| Blossom clusters | Matte pink masses with modest backlighting | Test masked, two-sided foliage cards and low-complexity geometry. |

These ranges are proposed artist controls. Judge them under the selected daylight. Use texture space for signs, deliberate seams, large variation, and silhouette detail. Keep fine grunge sparse. Distant texture mipmaps should preserve readable color groups. Windows in Style A include simple diagonal light streaks, which suggest a useful authored reflection treatment for secondary buildings. Grounding comes from local contact shadow and structural recesses, with dark creases used selectively.

**Composition should lead a walking player toward the café and NPC.** Style A uses a long street perspective, repeated pole spacing, rooflines, and converging cables. Style B shows a nearby destination with layered frontage, steps, signage, and trees behind it. Its large foreground pole demonstrates strong depth separation, though the café's interaction area will need an unobstructed view.

Main Street contributes a welcoming café at the near left, receding storefronts, sakura on the opposite side, and an inviting route into the distance. Translate those arrangements into the neutral daylight, simplified architecture, and controlled texture density of Style A and Style B. Keep its pink canopy rhythm and café/path relationship as layout ideas. Its amber windows, dense decorative timber, rich flower detail, and polished illustrative finish should be evaluated against the primary references before adoption.

Use the existing third-person gameplay requirement as the camera constraint. The style references show street-level environment views with no clearly visible player body. They do not specify SakuraDays' character design or final camera rig. Start a camera study at approximately 1.5–1.7 m above the ground with a 65–80 degree horizontal field of view at 16:9. Those are trial values, not recovered camera data. Adjust the actual third-person boom and framing to preserve the entrance and nearby NPC. Favor broad depth of field and a stable horizon. Compare a street overview, a café approach, and an NPC-distance view.

**The current target needs several visual adjustments to match the chosen style.**

| Aspect | Existing first-street target | Style A and Style B | Direction for a future revision |
|---|---|---|---|
| Overall finish | Highly polished illustration with dense decorative information | More visibly simplified real-time forms and broad quiet surfaces | Reduce small surface detail while maintaining neighborhood identity. |
| Café lighting | Bright amber pendants and warm light fill a richly dressed window | Daylight and cool recesses dominate, with compact accent areas | Reduce the luminous window area and emphasize the entrance, sign, and awning. |
| Surface shading | Many smooth tonal transitions across wood, paving, and façades | Larger value groups with selective smooth transitions | Simplify base-color variation and keep shadow shapes clear. |
| Vegetation | Detailed mixed flowers, individual leaves, and articulated foreground blossoms | Chunkier shrubs and grouped pink canopy forms | Use broad green masses and simplify the nearest blossom texture. |
| Sakura shape | Mostly spreading branches with bright pale-pink blossom edges | Spreading crowns plus a prominent weeping tree | Add the hanging silhouette vocabulary and preserve pink/lavender interiors. |
| Palette | Peach paving and façade tones, bright azure sky, warm wood, and pale blossoms | More gray-beige architecture, muted blue siding, cool road shade, and concentrated bright accents | Cool the neutral balance while preserving saturated pink and selected reds or yellows. |
| Line structure | Fine illustrative contours amid substantial interior detail | Bold structural borders and simple seams are easier to distinguish | Strengthen major roof, window, sign, and branch boundaries. |
| Street character | Broad tiled café sidewalk, continuous tactile strip, bollards, and a distant gate | Narrower residential road margins in A and localized commercial/shrine frontage in B | Retain a playable café sidewalk, borrowing the simpler neighborhood proportions. |
| Camera and character | A large, centered walking character anchors the image | Environment-led street views | Keep third-person play and review how much the body obscures the café route. Character styling needs its own reference study. |

The target already shares the necessary spring setting, utility wires, low-rise Japanese street, sakura, and inviting café frontage. The principal change is how these elements are rendered and simplified. Main Street is used to settle layout questions when the style references leave those open.

**Unreal Engine reproduction should begin with a small material and lighting study.** Use the planned `Content/SakuraDays/` area for a future study containing one café wall, a window, a roof edge, a road patch, a shrub, a sakura cluster, and the player for scale. Compare it with both primary references at gameplay distance before expanding the street.

The current `Config/DefaultEngine.ini` enables DX12, deferred rendering, Lumen GI and reflections, hardware ray tracing, Virtual Shadow Maps, and project Nanite support. It disables automatic exposure, motion blur, and lens flare by default, while enabling bloom. It records `r.AntiAliasingMethod=0` and `r.CustomDepth=1`. These are project defaults inspected for this guide. A camera, volume, scalability setting, or runtime override may produce a different active state. [Project rendering configuration](<C:/Users/HP/Documents/Unreal Projects/sakuradays/Config/DefaultEngine.ini>)

Begin with restrained Default Lit materials, deliberate mesh normals, and low-contrast textures. Default Lit provides direct and indirect lighting and specular response. This lets roof shadows, nearby objects, and daylight behave coherently while the art carries most of the simplification. For blossom cards, evaluate the Two Sided Foliage shading model with controlled Subsurface Color to give backlit surfaces a readable pink. [Epic shading-model documentation](https://dev.epicgames.com/documentation/unreal-engine/shading-models-in-unreal-engine)

Set up the study's directional light, skylight, and a Post Process Volume with fixed exposure and modest grading. First match the relative brightness of cream plaster, road shade, and blossom highlights. Use low bloom and broad focus. Inspect the café recess so indirect lighting preserves its shape. Assess the existing Lumen configuration visually and by profiling on the development laptop before changing rendering systems.

If the lit study still has too many smooth tonal steps, evaluate a localized toon treatment on one test material. A normal-to-sun ramp can organize two or three color bands, with the sun direction supplied through a material parameter collection. An Unlit ramp requires an explicit plan for cast shadows and other lighting influences. Multiplying such a ramp into a lit material can compound its shading. A full-screen posterization pass also affects sky, glass, and emissive details. Prototype the result on the study before choosing any of these approaches. These are proposed implementation options, not deductions about the reference images' shader code.

For outlines, first compare the geometry and dark trim with the references. If additional contours are needed, prototype depth and normal edge detection in a post-process material. Use Custom Depth and Custom Stencil for selected object groups, attenuate distant edges, and test occlusion so silhouettes remain correctly hidden behind foreground geometry. Tune the pass location against the active antialiasing method, since depth and normal sampling interact with temporal processing. [Epic post-process material documentation](https://dev.epicgames.com/documentation/unreal-engine/post-process-materials-in-unreal-engine)

Selective stencil masking would require the project setting Custom Depth-Stencil Pass to use Enabled with Stencil, plus appropriate per-object participation. The current numeric default alone does not establish stencil availability or object tagging. Review the active settings during a future implementation. [Epic rendering settings](https://dev.epicgames.com/documentation/unreal-engine/rendering-settings-in-the-unreal-engine-project-settings?lang=en-US)

For the sakura study, compare masked cards with simple cluster geometry. Match crown mass and branch rhythm before increasing flower count. Use gentle World Position Offset only on the parts that need motion. Check opacity coverage, overdraw, and shadows from the walking camera. Test temporal antialiasing at the intended output resolution, especially on wires, foliage edges, outlines, and animated clusters. TSR and other temporal methods need particular care with animated materials and motion information. [Epic Temporal Super Resolution documentation](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-in-unreal-engine)

Use a bounded Niagara system for falling petals. A Mesh Renderer can instance a small petal mesh with varied rotation and gentle drift. Try fewer nearby mesh petals and simpler distant coverage, with static ground patches for accumulation. Tune screen density while the player walks and while dialogue is open. [Epic Niagara renderer reference](https://dev.epicgames.com/documentation/unreal-engine/render-module-reference-for-niagara-effects-in-unreal-engine?lang=en-US)

**Future art reviews should compare the same three playable views.** Capture the street overview, café approach, and NPC-distance view at consistent exposure and output resolution. Review them beside Style A and Style B for the following results.

- Cream and blue-gray architecture occupies broad calm areas, with pink, red, and yellow accents concentrated around meaningful features.
- The café entrance reads immediately from the route, with sufficient contrast for the NPC and prompt.
- Sakura reads as clustered pink volume with visible branch structure. Shrubs remain simple green masses.
- Roofs, windows, signs, and street props have clear boundaries at ordinary gameplay distance.
- Shadowed surfaces retain local color, and bright petals retain variation.
- A walking camera preserves the same appearance without distracting edge shimmer, petal trails, or exposure changes.
- Layout decisions from Main Street remain consistent with the surface treatment and daylight of the two primary style references.

The next visual decision should be approval of a small in-engine style study against these criteria, followed by extension into the milestone street.
