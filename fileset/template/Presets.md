# AnimZ Presets

The pop-up presets live in `auto_pop_up.blend`. The AnimZ menu reads the list from the node group names, so the numbers below are the values of the `In Presets` / `Out Presets` sockets.

Channels: T = Translate, R = Rotation, S = Scale.

## In

| # | Preset | Channels | Suggested duration |
|---|---|---|---|
| 0 | Ease Out | S | 30 frames |
| 1 | Ease In Out | S | 30 frames |
| 2 | Bounce | S | 30 frames |
| 3 | Jump & Bounce | T, S | 30 frames |
| 4 | Jump, Rotate & Bounce | T, R, S | 30 frames |
| 5 | Slide ↓ Elastic | T, S | 60 to 90 frames, Linear |
| 6 | Slide ↑ Ease Out | T, S | 20 to 45 frames |
| 7 | Slide ↓ Ease Out | T, S | 20 to 45 frames |
| 8 | Slide → Ease Out | T, S | 20 to 45 frames |
| 9 | Slide ← Ease Out | T, S | 20 to 45 frames |
| 10 | Rotate ← & Back | R, S | 30 frames |
| 11 | Bounce & Swing X | R, S | 30 frames |
| 12 | Drop Jiggle | T, R, S, Ground | 60 to 90 frames |

Drop Jiggle grows in the air, falls, lands tilted, then rocks and spins to rest. Its settings are fixed in the preset (drop 1.5 x object size, spin 45°, tilt 15°, 3 jiggles, grow until 0.1, land at 0.45). In Power scales the drop, tilt and spin; 0.5 is the designed motion.

## Out

| # | Preset | Channels | Suggested duration |
|---|---|---|---|
| 0 | Ease In | S | 30 frames |
| 1 | Ease In Out | S | 30 frames |
| 2 | Back | S | 30 frames |
| 3 | Jump & Bounce | T, S | 30 frames |
| 4 | Jump, Rotate & Bounce | T, R, S | 30 frames |
| 5 | X-Axis Scale | S | 30 frames |
| 6 | Slide ↑ Ease Out | T, S | 20 to 45 frames |
| 7 | Slide ↓ Ease Out | T, S | 20 to 45 frames |
| 8 | Slide → Ease Out | T, S | 20 to 45 frames |
| 9 | Slide ← Ease Out | T, S | 20 to 45 frames |
| 10 | Rotate ← & Back | R, S | 30 frames |

## Node structure (template v4)

```
auto_pop_up
├── Source Geometry      own mesh, another object, or a collection
├── Object Size          largest bounding-box side (scales Translate)
├── In Animation         AnimZ In Library  -> x Power -> Transform In
└── Out Animation        AnimZ Out Library -> x Power -> Transform Out

AnimZ In Library / AnimZ Out Library
    Factor, Preset -> one group node per preset -> Index Switch (Translate, Rotation, Scale)

In 04 | Jump, Rotate & Bounce   (one group per preset)
    Factor -> Float Curves (labeled "Scale XYZ", "Rotation Z", ...) -> Combine XYZ -> Translate, Rotation, Scale
```

- `Factor` goes from 0 (start) to 1 (end). AnimZ keys it with green (Jitter) Bezier keys, so the Bezier easing adds to the curves' easing. Set the keys to Vector handles (or Linear) in the Graph Editor to get a curve's motion exactly as designed.
- Translate is multiplied by the object's largest side and `In Power` / `Out Power`. A value of 1 moves one object length at Power 1.
- Rotation is in radians, multiplied by Power x 2. At Power 0.5 the curve value is used as is.
- Scale is used as is. In presets end at 1, Out presets start at 1.
- A channel a preset does not use has no curve and stays 0.
- Optional `Ground` output (In only, template v5): 1 keeps the object's lowest point on its rest bottom plus Translate Z, so tilts rock on the ground instead of sinking in. Presets without it stay 0 and pay no extra cost.

## Adding a preset

Run the helper on the template. It copies `AnimZ Preset Template` (or an existing preset with `--from N`), names it with the next number, adds it to the library and raises the socket limit:

```bash
blender -b fileset/template/auto_pop_up.blend --python scripts/animz_add_preset.py -- In "Spin Pop"
```

```bash
blender -b fileset/template/auto_pop_up.blend --python scripts/animz_add_preset.py -- Out "Spin Away" --from 4
```

Then:

1. Open `auto_pop_up.blend`, open the new group (for example `In 12 | Spin Pop`) and edit its curves. Save.
2. Raise `TEMPLATE_VERSION` in `fileset/animz_tools.py` and the `animz_version` custom property on `auto_pop_up` to the same number, so older files offer **Upgrade Node Groups**.
3. If the preset is not meant for 30 frames, add its duration to `PRESET_HINTS` in `fileset/animz_tools.py`.
4. Reload the addon. The preset appears in the AnimZ menu.

To add one by hand instead: duplicate `AnimZ Preset Template`, name it `In 12 | Spin Pop` (next free number, two digits), add it to `AnimZ In Library`, add one item to each of the three Index Switch nodes, link the new group's outputs to those items, and set the max of `In Presets` on `auto_pop_up` to 12.

Keep the numbers continuous. A preset's number must match its item position in the library switches.
