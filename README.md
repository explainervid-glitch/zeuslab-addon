# ZeusLab

ZeusLab is a Blender addon that bundles the animation tools used in Zeus's production workflow. It covers bone snapping, prop attach/detach, Mixamo rig baking, procedural pop-up animation, and pack/playblast export.

| | |
|---|---|
| Version | 1.9.3 |
| Blender | 5.0.1 or newer |
| Author | Putra Tegar |
| Location | 3D Viewport > Sidebar (N) > **ZeusLab** tab |
| Manual | [ZeusLab Manual (Notion)](https://zeusanim.notion.site/ZeusLab-Manual-306b85d5ae5a808fb3e9eecd8d05f511) |

## Installation

1. Build the zip with `npm run package` (see [Packaging](#packaging)), or download a release zip.
2. In Blender, open **Edit > Preferences > Add-ons**.
3. Click the dropdown at the top right and choose **Install from Disk...**.
4. Select `ZeusLab-v<version>.zip` and enable **ZeusLab**.
5. Open the 3D Viewport sidebar with `N` and go to the **ZeusLab** tab.

The addon folder must be named `ZeusLab`. The preferences class and the updater both look for that name, so do not rename the folder after install.

## Features

All panels live in the **ZeusLab** sidebar tab. You can show or hide each panel in the addon preferences (see [Preferences](#preferences)).

### Snap Bone

Pins an IK bone to a world position using an Empty, so feet or hands stay planted during a shot. Works in Pose Mode on an armature.

- **Create Snap**: adds an Empty at the selected bone and creates `snapLoc` / `snapRot` constraints. Toggle **Follow Rotation** to also copy rotation.
- **Snap / Unsnap**: keys constraint influence on and off. The offset fields set how many frames the blend takes.
- **Update Empty / Apply**: moves the target Empty to the current bone position. Adjust the Empty by hand, then press **Apply** to key it and return to Pose Mode.
- **Tweak**: creates an Empty of the chosen type and constrains the bone to it, with optional **Set Inverse**.
- **Bake**: bakes the edited action back to keyframes.

### Simple Take

Attaches and detaches an object (a prop, for example) to an armature bone using layered **Child Of** constraints.

- Pick a **Target** armature and **Bone**, then set **Maintain Offset** and **New Constraint**.
- **Take / Linked**: creates or updates a Child Of layer and keys influence to 1.
- **Put / Unlinked**: keys the active layer influence to 0.
- The constraint layer list shows every Child Of on the object. Use the side buttons to remove a layer or key influence 1 / 0 on the active layer.

### Mixamo Rig to Bones

Converts a custom Mixamo rig animation into plain baked bones.

1. **Prepare Bake**: duplicates the selected collection as "Baked Animation" and enables all bone collections on the target armature.
2. Set the **Start** / **End** frame range and pick a skeleton style.
3. **Bake Action**: bakes the action and cleans up the bones for the selected style.

Hidden by default. Enable it in preferences.

### AnimZ

Procedural pop-up and wiggle animation for selected Mesh, Curve and Text objects, driven by Geometry Nodes groups shipped in `fileset/template/auto_pop_up.blend`. The node groups are appended automatically the first time you use them.

AnimZ is in two places with the same controls:

- **Sidebar**: 3D Viewport > `N` > **ZeusLab** tab. Show or hide it in preferences.
- **Popup**: press `Alt` + `` ` `` in the 3D Viewport to open a compact AnimZ panel at the mouse cursor. The popup works even when the sidebar panel is hidden. It has three rows:
  - In: type, refresh, duration, **In**.
  - Out: type, refresh, duration, **Out**.
  - **Wiggle** (add), copy, remove, settings (gear) and Delete Animations (trash). The gear shows the active object's wiggle settings.
 To change the key, go to **Edit > Preferences > Keymap**, search for `wm.call_panel` and edit the entry for `ANIMZ_PT_popup`.

- **In Animation**: pick a type, set the duration in frames, then press **Animate In**. Types: Ease Out, Ease In Out, Bounce, Jump & Bounce, Jump Rotate & Bounce, Slide Elastic (down), Slide Ease Out (up, down, right, left), Rotate & Back, Bounce & Swing X, Drop Jiggle (grows in the air, falls, rocks on the ground to rest; 60 to 90 frames).
- **Out Animation**: same controls with **Animate Out**. Types: Ease In, Ease In Out, Back, Jump & Bounce, Jump Rotate & Bounce, X-Axis Scale, Slide Ease Out (up, down, right, left), Rotate & Back.
- Animating again replaces the previous In (or Out) keyframes. AnimZ warns when an Out starts before the In has finished.
- **Refresh** button next to each type: changes the animation type on existing objects and keeps the keyframes.
- **Delete Animations**: removes the `auto_pop_up` modifier and its keyframes from the selected objects. Other animation is left alone, and keyframes in an action shared with other objects are kept. **Purge Node Group** removes the node group only when no object uses it any more.

The full preset reference, the node structure and how to add a new preset are in `fileset/template/Presets.md`. The preset menu is read from the template, so a new preset needs no code change.

#### Wiggle Loop

A seamless looping wiggle on location, rotation and scale, as a separate `auto_wiggle` modifier. Only objects with a wiggle are recalculated every frame, so pop-up animation stays fast on heavy objects.

- **Add Wiggle**: adds the wiggle to the selected objects, each with its own random seed. When the active object already has a wiggle, its settings are copied.
- **Copy** (arrow icon): copies the active object's wiggle settings to the other selected objects. Each object keeps its own seed.
- **Remove** (X icon): removes the wiggle and its keyframes from the selected objects.
- The active object's settings are shown in the panel:

| Setting | What it does |
|---|---|
| Strength | Master amount, 0 to 1. Keyframe it to fade the wiggle in or out |
| Loop Duration | Seconds until the motion repeats exactly |
| Randomness | 0 (default) = smooth even sine wave, 1 = irregular organic noise |
| Random Offset | 0 = all axes move together in one rhythm, 1 = every axis and object starts at a random point of the loop (default 0.5) |
| Location | Max offset per axis, times the object's largest side |
| Rotation | Max rotation per axis |
| Scale | Max scale change per axis (0.05 = 5%) |
| Uniform Scale | Off: axes scale independently (squash and stretch) |
| Seed | Pattern of Random Offset and Randomness per object |

Files with the older `auto_wiggle` (v1) show the upgrade warning. Upgrading keeps values and keyframes, but resets Randomness (0) and Random Offset (0.5) to the new defaults so the wiggle becomes the new smooth wave.

Notes on the node groups:

- Keyframes on the `In` / `Out` sockets are set to Linear. The easing comes from the Float Curves inside each preset.
- Rotation is the same for every object size. Translate scales with the object's largest side, so flat objects still move.
- `In Power` / `Out Power` (0 to 10, default 0.5) set the strength of translate and rotate. At 0.5 a 2 m cube moves exactly as the preset was designed.
- The template node group carries a version number (`animz_version`, currently 5). When a .blend file has an older `auto_pop_up`, the AnimZ panel shows a warning with an **Upgrade Node Group** button. Upgrading keeps modifiers and keyframes, but the motion of existing objects may change, so it asks for confirmation first. Objects that used the old built-in Wiggle get the new Wiggle modifier with default settings.
- Presets newer than the file's node group are blocked until you upgrade.

### Zeus Pack Assistant

Tools to build and render character animation packs.

- **18 / 19**: append the pack style collection for that style from `fileset/template/`.
- **Profile**: sets Cycles GPU (OptiX), adaptive sampling, a 320 x 430 resolution and H.264 MP4 output. It also creates the `COPY THIS FOLDER` and `DONT COPY THIS FOLDER` collections.
- **RENDER!**: renders the animation to `<blend name>.mp4` next to the .blend file.

**For Intern** subpanel (playblast export):

- **18 / 19**: append the camera collection (`Camera.Front`, `Camera.Side`) for that style.
- **Profile**: applies the playblast resolution.
- **Export Playblast**: saves the file, renders a viewport playblast from both cameras, and joins them side by side into `<blend name>.mp4` with FFmpeg. The addon looks for FFmpeg next to the Blender binary first, then on the system `PATH`.

Hidden by default. Enable it in preferences.

### FPS Converter

Operators `fps.convert_to_30` and `fps.convert_to_60` convert a scene's animation to 30 or 60 FPS while keeping the same timing. They retime object keyframes and material node keyframes, and support both the legacy action API and the Blender 5 layered action (channelbag) system. These operators have no button in the current UI. Run them from F3 search.

## Preferences

Open **Edit > Preferences > Add-ons > ZeusLab**. There are two tabs:

- **Manage Panels**: toggle which panels appear in the sidebar. Changes apply immediately.
- **Update**: shows the installed version. **Cek Update** checks the latest [GitHub release](https://github.com/explainervid-glitch/zeuslab-addon/releases), shows its notes as the changelog, and offers **Install Update**. The updater downloads the release zip, backs up the current addon folder to the system temp directory, installs the new files, and asks you to restart Blender. It refuses to install over a development copy (a git repo or a symlinked folder), so it never overwrites the source repo.

| Panel | Default |
|---|---|
| Snap Bone | Shown |
| Simple Take | Shown |
| AnimZ | Shown |
| Mixamo Rig to Bones | Hidden |
| Zeus Pack Assistant | Hidden |

## Usage counts for zeploy

On PCs where the studio's deployment tool zeploy is installed, ZeusLab counts which features get used, so the zeploy dashboard can show which tools the team relies on. Each run of a ZeusLab operator (Snap Bone, Simple Take, Mixamo Rig to Bones, AnimZ, FPS Converter, Pack, Playblast) adds one line to `%LOCALAPPDATA%\zeploy\usage\ZeusLab.jsonl`, which zeploy's agent collects every minute. A cancelled run is not counted; one that raises counts as an error. An operator run by another ZeusLab operator (Prepare Bake runs Duplicate Collection and Bake) counts once, as the outer one. List buttons, helpers and the updater are not counted. No file names, scene data or user names are recorded, Blender sends nothing over the network, and on a PC without zeploy nothing is written.

The feature names are in `zeploy_counts.py` (`FEATURES`); add a new operator's `bl_idname` there to count it. `zeploy_usage.py` is zeploy's helper, copied unchanged from the zeploy repository.

## Project Structure

```
ZeusLab/
├── __init__.py            # bl_info, module registration
├── preferences.py         # Addon preferences (Manage Panels / Update tabs)
├── manage.py              # Panel visibility section drawing
├── version.json           # Version source for packaging and releases
├── zeploy_counts.py       # Which operators count as features for zeploy
├── zeploy_usage.py        # zeploy's usage helper (copied unchanged)
├── bonver/
│   ├── bonesnap.py        # Snap Bone panel and operators
│   ├── simpletake.py      # Simple Take (Child Of attach/detach)
│   └── bonver_operator.py # Mixamo Rig to Bones
├── fileset/
│   ├── animz_tools.py     # AnimZ pop-up and wiggle animation
│   ├── pack_exporter.py   # Pack profile, render and append operators
│   ├── playblast_operator.py # Playblast split-screen export
│   ├── fileset_panel.py   # Zeus Pack Assistant panels
│   ├── fps_converter.py   # 30 / 60 FPS conversion
│   └── template/          # .blend templates (node groups, cameras, pack styles)
├── panel/                 # Legacy main panel (not registered)
├── updater/               # Update checker and installer
└── scripts/               # Dev only: package.js, release.js, animz_add_preset.py
```

## Packaging

Requires [Node.js](https://nodejs.org/) 18 or newer. No npm dependencies.

```bash
npm run package
```

The script writes `dist/ZeusLab-v<version>.zip`. The version comes from `version.json`. The zip contains a top-level `ZeusLab/` folder, ready for **Install from Disk**.

These items are left out of the zip:

- `dist/`, `scripts/`, `node_modules/`, `.git/`, `.vscode/`
- `package.json`, `.gitignore`
- `__pycache__/` and `*.pyc`
- Blender backups (`*.blend1`, `*.blend2`, ...) and `*.backup*` files

## Releasing an Update

Requires the [GitHub CLI](https://cli.github.com/) (`gh auth login`) with push access to the repo.

1. Commit all changes on `main`.
2. Preview the release first. This changes nothing:

   ```bash
   npm run release -- patch --dry-run
   ```

3. Run the release. Use `patch`, `minor`, `major` or an exact version such as `2.0.0`:

   ```bash
   npm run release -- minor --notes "1. New Wiggle Loop\n2. Bug fixes"
   ```

Installed addons see the new release on their next **Cek Update**. Draft and pre-release versions are skipped.

The release script does these steps:

- Checks that you are on `main`, the working tree is clean, `main` is not behind `origin`, and the tag is free.
- Writes the new version to `bl_info` (`__init__.py`), `version.json` and `package.json`.
- In `version.json`, sets `changelog` and points `download_url` to the zip on the GitHub release.
- Builds the zip with `npm run package`.
- Commits `chore(release): v<version>`, creates tag `v<version>` and pushes both.
- Creates the GitHub release with the zip attached.

Without `--notes`, the changelog is the list of commit subjects since the last tag.

## License

Internal tool for Zeus's animation team. All rights reserved by the author.
