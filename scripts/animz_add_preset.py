"""Add a new AnimZ pop-up preset to fileset/template/auto_pop_up.blend (developer tool).

Command line (saves the template):
    blender -b fileset/template/auto_pop_up.blend --python scripts/animz_add_preset.py -- In "Spin Pop"
    blender -b fileset/template/auto_pop_up.blend --python scripts/animz_add_preset.py -- Out "Spin Away" --from 4

Inside Blender (template open): paste into the Text Editor, set DIRECTION / NAME / COPY_FROM below,
run it, edit the curves, then save the file.

What it does:
    1. Copies "AnimZ Preset Template" (or an existing preset with --from N) to "<In|Out> <NN> | <Name>".
    2. Adds it to "AnimZ <In|Out> Library" as the next index and links all three switches.
    3. Raises the max of the "In Presets" / "Out Presets" socket of auto_pop_up.

The addon reads the preset list from the group names, so the new preset appears in the AnimZ menu
after the addon reloads. Bump TEMPLATE_VERSION in fileset/animz_tools.py and "animz_version" on
auto_pop_up so existing files offer the upgrade.
"""
import re
import sys

import bpy

DIRECTION = "In"   # "In" or "Out"
NAME = "New Preset"
COPY_FROM = None   # None = blank template, or an index of an existing preset of the same direction

TEMPLATE_NAME = "AnimZ Preset Template"
CHANNELS = ("Translate", "Rotation", "Scale")
PRESET_NAME_RE = re.compile(r"^(In|Out) (\d+) \| (.+)$")


def parse_args():
    global DIRECTION, NAME, COPY_FROM
    if "--" not in sys.argv:
        return
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) < 2:
        raise SystemExit('Usage: -- <In|Out> "<Name>" [--from N]')
    DIRECTION, NAME = args[0].capitalize(), args[1]
    if "--from" in args:
        COPY_FROM = int(args[args.index("--from") + 1])


def presets(direction):
    found = {}
    for g in bpy.data.node_groups:
        m = PRESET_NAME_RE.match(g.name)
        if m and m.group(1) == direction:
            found[int(m.group(2))] = g
    return found


def main():
    parse_args()
    if DIRECTION not in ("In", "Out"):
        raise SystemExit(f"Direction must be In or Out, got {DIRECTION!r}")
    library = bpy.data.node_groups.get(f"AnimZ {DIRECTION} Library")
    pop = bpy.data.node_groups.get("auto_pop_up")
    if library is None or pop is None:
        raise SystemExit("Open fileset/template/auto_pop_up.blend (v4 or newer) first")

    existing = presets(DIRECTION)
    index = max(existing) + 1 if existing else 0
    if COPY_FROM is None:
        source = bpy.data.node_groups[TEMPLATE_NAME]
    elif COPY_FROM in existing:
        source = existing[COPY_FROM]
    else:
        raise SystemExit(f"No {DIRECTION} preset {COPY_FROM}")

    preset = source.copy()
    preset.use_fake_user = False
    preset.name = f"{DIRECTION} {index:02d} | {NAME}"
    preset.description = f"AnimZ {DIRECTION} preset {index}: {NAME}. Curves map Factor 0-1 to Translate, Rotation and Scale"
    # The copy of a preset with an unused channel has no node for it; make sure all outputs exist
    out_node = next(n for n in preset.nodes if n.bl_idname == "NodeGroupOutput")
    missing = [ch for ch in CHANNELS if not out_node.inputs[ch].is_linked]

    switches = {n.label.replace(" Switch", ""): n for n in library.nodes if n.bl_idname == "GeometryNodeIndexSwitch"}
    group_in = next(n for n in library.nodes if n.bl_idname == "NodeGroupInput")
    group_nodes = [n for n in library.nodes if n.bl_idname == "GeometryNodeGroup"]
    lowest = min((n.location.y for n in group_nodes), default=600)

    node = library.nodes.new("GeometryNodeGroup")
    node.node_tree = preset
    node.label = preset.name
    node.location = (-200, lowest - 200)
    library.links.new(group_in.outputs["Factor"], node.inputs[0])
    for ch in CHANNELS:
        switch = switches[ch]
        switch.index_switch_items.new()
        # inputs[0] is Index, inputs[1 + i] is item i (a trailing extension socket may follow)
        library.links.new(node.outputs[ch], switch.inputs[1 + index])
    # Optional switches (In Library "Ground"): every switch needs one item per preset to keep indices aligned
    for name, switch in switches.items():
        if name in CHANNELS:
            continue
        switch.index_switch_items.new()
        if name in node.outputs:
            library.links.new(node.outputs[name], switch.inputs[1 + index])

    for item in pop.interface.items_tree:
        if item.item_type == 'SOCKET' and item.name == f"{DIRECTION} Presets":
            item.max_value = index

    print(f"AnimZ: added '{preset.name}' (index {index}) from '{source.name}'")
    if missing:
        print(f"AnimZ: {', '.join(missing)} not driven by the source preset (stays 0). "
              f"Use the blank template to animate them")
    print("AnimZ: next, edit the curves, bump TEMPLATE_VERSION and animz_version, and add a duration hint "
          "to PRESET_HINTS in fileset/animz_tools.py if it is not 30 frames")
    if bpy.app.background:
        bpy.ops.wm.save_mainfile(compress=True)
        print(f"AnimZ: saved {bpy.data.filepath}")


main()
