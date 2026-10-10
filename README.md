# ZeusLab

ZeusLab is a Blender addon that bundles the animation tools used in Zeus's production workflow. It covers bone snapping, prop attach/detach, Mixamo rig baking, procedural pop-up animation, render style presets, and pack/playblast export.

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

Procedural pop-up animation for any selected objects, driven by the `auto_pop_up` Geometry Nodes group shipped in `fileset/template/auto_pop_up.blend`. The node group is appended automatically the first time you animate.

- **In Animation**: pick a type, set the duration in frames, then press **Animate In**. Types: Ease Out, Ease In Out, Bounce, Jump & Bounce, Jump Rotate & Bounce, Slide Elastic (down), Slide Ease Out (up, down, right, left), Rotate & Back.
- **Out Animation**: same controls with **Animate Out**. Types: Ease In, Ease In Out, Back, Jump & Bounce, Jump Rotate & Bounce, X-Axis Scale, Slide Ease Out (up, down, right, left), Rotate & Back.
- **Refresh** button next to each type: changes the animation type on existing objects and keeps the keyframes.
- **Delete Animations**: removes the `auto_pop_up` modifier from the selected objects, with an option to purge the node group from the file.

The full preset reference is in `fileset/template/Presets.md`.

### 3D Explainer Style

One-click render settings for each 3D Explainer style: **18, 19, 20** (Isometric), **21** (Isometric), **22** (No Face) and **23** (Realist). Each button sets the render engine, Cycles GPU device (OptiX or CUDA), sampling, resolution and output format for that style.

Hidden by default. Enable it in preferences.

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
- **Update**: shows the installed version. **Cek Update** checks the remote `version.json`, shows the changelog, and offers **Install Update**. The updater backs up the current addon folder to the system temp directory, installs the new files, and asks you to restart Blender.

| Panel | Default |
|---|---|
| Snap Bone | Shown |
| Simple Take | Shown |
| AnimZ | Shown |
| Mixamo Rig to Bones | Hidden |
| Zeus Pack Assistant | Hidden |
| 3D Explainer Style | Hidden |

## Project Structure

```
ZeusLab/
├── __init__.py            # bl_info, module registration
├── preferences.py         # Addon preferences (Manage Panels / Update tabs)
├── manage.py              # Panel visibility section drawing
├── version.json           # Version, download URL and changelog for the updater
├── bonver/
│   ├── bonesnap.py        # Snap Bone panel and operators
│   ├── simpletake.py      # Simple Take (Child Of attach/detach)
│   └── bonver_operator.py # Mixamo Rig to Bones
├── fileset/
│   ├── animz_tools.py     # AnimZ pop-up animation
│   ├── style_setting.py   # 3D Explainer style render presets
│   ├── pack_exporter.py   # Pack profile, render and append operators
│   ├── playblast_operator.py # Playblast split-screen export
│   ├── fileset_panel.py   # Zeus Pack Assistant panels
│   ├── fps_converter.py   # 30 / 60 FPS conversion
│   └── template/          # .blend templates (node groups, cameras, pack styles)
├── panel/                 # Legacy main panel (not registered)
├── updater/               # Update checker and installer
└── scripts/package.js     # Packaging script (dev only)
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

1. Bump `"version"` in `bl_info` (`__init__.py`), `version.json` and `package.json`.
2. Update the `changelog` in `version.json`.
3. Run `npm run package`.
4. Upload the zip and set its direct download link as `download_url` in `version.json`.
5. Upload the new `version.json` to the location in `updater/updater.py` (`version_url`).

## License

Internal tool for Zeus's animation team. All rights reserved by the author.
