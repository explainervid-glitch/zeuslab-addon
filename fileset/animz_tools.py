import bpy
from bpy.app.handlers import persistent
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import IntProperty, EnumProperty, BoolProperty
from bpy_extras import anim_utils
from ..preferences import get_addon_preferences
import os
import random
import re

NODE_GROUP_NAME = "auto_pop_up"
WIGGLE_NODE_GROUP_NAME = "auto_wiggle"
# Harus sama dengan custom property "animz_version" pada node group di template/auto_pop_up.blend
TEMPLATE_VERSION = 5
WIGGLE_VERSION = 2

# Tipe object yang bisa memakai modifier Geometry Nodes AnimZ
SUPPORTED_TYPES = {'MESH', 'CURVE', 'FONT'}
NO_SELECTION_MESSAGE = "No Mesh, Curve or Text objects selected"


def get_supported_selected(context):
    """Object terpilih yang bisa dianimasikan AnimZ"""
    return [obj for obj in context.selected_objects if obj.type in SUPPORTED_TYPES]

# =======================================================
# Function
# =======================================================

def get_fcurves(obj):
    """
    Ambil fcurves object, kompatibel Blender 4.x (action.fcurves) dan
    Blender 5.0+ (layered action / channelbag, action.fcurves sudah dihapus).
    """
    anim = obj.animation_data
    if not anim or not anim.action:
        return None
    action = anim.action
    if hasattr(action, 'fcurves'):
        return action.fcurves
    slot = getattr(anim, 'action_slot', None)
    if slot is None:
        return None
    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
    return channelbag.fcurves if channelbag else None


def set_fcurve_bezier(obj, data_path):
    """Set interpolasi BEZIER, supaya timing bisa diatur lewat handle di Graph Editor"""
    fcurves = get_fcurves(obj)
    if not fcurves:
        return
    for fcurve in fcurves:
        if fcurve.data_path == data_path:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
            fcurve.update()
            break


def find_socket_by_name(node_group, name, socket_type):
    """Cari identifier input socket berdasarkan nama dan tipe"""
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == socket_type and
            item.name == name):
            return item.identifier
    return None


def _modifier_inputs(modifier):
    """
    Blender 5.2+: nilai input Geometry Nodes ada di modifier.properties.inputs.
    Blender 5.0/5.1: masih IDProperty langsung di modifier (None di sini).
    """
    props = getattr(modifier, 'properties', None)
    return getattr(props, 'inputs', None)


def has_input(modifier, identifier):
    inputs = _modifier_inputs(modifier)
    if inputs is not None:
        return hasattr(inputs, identifier)
    return identifier in modifier


def get_input(modifier, identifier):
    inputs = _modifier_inputs(modifier)
    if inputs is not None:
        return getattr(inputs, identifier).value
    return modifier[identifier]


def set_input(modifier, identifier, value):
    inputs = _modifier_inputs(modifier)
    if inputs is not None:
        getattr(inputs, identifier).value = value
    else:
        modifier[identifier] = value
    # Menulis lewat Python tidak selalu me-refresh object yang dievaluasi (5.0/5.1 IDProperty,
    # dan object lain yang diubah dari script), jadi viewport tetap menampilkan nilai lama
    modifier.id_data.update_tag()


def input_data_path(modifier, identifier):
    """Data path untuk keyframe input modifier, relatif terhadap object"""
    if _modifier_inputs(modifier) is not None:
        return f'modifiers["{modifier.name}"].properties.inputs.{identifier}.value'
    return f'modifiers["{modifier.name}"]["{identifier}"]'


def draw_input(layout, modifier, identifier, text=None):
    """Tampilkan input modifier di panel (API 5.2+ dan 5.0/5.1)"""
    inputs = _modifier_inputs(modifier)
    if inputs is not None:
        layout.prop(getattr(inputs, identifier), "value", text=text if text is not None else "")
    else:
        layout.prop(modifier, f'["{identifier}"]', text=text if text is not None else "")


def find_modifier(obj, node_group):
    """Modifier Geometry Nodes di obj yang memakai node_group"""
    if node_group is None:
        return None
    for mod in obj.modifiers:
        if mod.type == 'NODES' and mod.node_group == node_group:
            return mod
    return None


def get_input_max(node_group, identifier):
    """Nilai max socket input di interface node group"""
    for item in node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.identifier == identifier:
            return getattr(item, 'max_value', None)
    return None


def check_preset_supported(node_group, socket_id, value):
    """
    Preset baru (mis. In 11) tidak ada di node group versi lama. Index Switch di
    luar range memberi scale 0, object hilang permanen. Returns pesan error atau None.
    """
    max_value = get_input_max(node_group, socket_id) if socket_id else None
    if max_value is not None and value > max_value:
        return (f"This preset needs node group v{TEMPLATE_VERSION} "
                f"(file has v{get_node_group_version(node_group)}). Click 'Upgrade Node Group' first")
    return None


def clear_keyframes(obj, data_path):
    """Hapus semua keyframe di fcurve data_path, supaya animasi baru menggantikan yang lama"""
    fcurves = get_fcurves(obj)
    if not fcurves:
        return
    for fcurve in fcurves:
        if fcurve.data_path == data_path:
            points = fcurve.keyframe_points
            for i in range(len(points) - 1, -1, -1):
                points.remove(points[i], fast=True)
            fcurve.update()
            break


def get_key_range(obj, data_path):
    """(frame pertama, frame terakhir) keyframe di data_path, atau None"""
    fcurves = get_fcurves(obj)
    if not fcurves:
        return None
    for fcurve in fcurves:
        if fcurve.data_path == data_path and len(fcurve.keyframe_points):
            frames = [kp.co.x for kp in fcurve.keyframe_points]
            return (min(frames), max(frames))
    return None


def is_animation_shared(obj):
    """True bila object lain memakai action + slot yang sama (fcurve dipakai bersama)"""
    anim = obj.animation_data
    if not anim or not anim.action:
        return False
    slot = getattr(anim, 'action_slot', None)
    for other in bpy.data.objects:
        if other == obj or not other.animation_data:
            continue
        if other.animation_data.action == anim.action and getattr(other.animation_data, 'action_slot', None) == slot:
            return True
    return False


def remove_modifier_fcurves(obj, modifier_name):
    """
    Hapus fcurve milik modifier tertentu saja. Fcurve lain (termasuk milik
    tool lain) tidak disentuh. Returns jumlah fcurve terhapus, -1 bila action dipakai bersama.
    """
    fcurves = get_fcurves(obj)
    if not fcurves:
        return 0
    if is_animation_shared(obj):
        return -1
    prefix = f'modifiers["{modifier_name}"]'
    removed = 0
    for i in range(len(fcurves) - 1, -1, -1):
        if fcurves[i].data_path.startswith(prefix):
            fcurves.remove(fcurves[i])
            removed += 1
    return removed


def report_overlaps(operator, objects, node_group):
    """Warning bila animasi Out dimulai sebelum animasi In selesai"""
    in_id = find_float_socket(node_group)
    out_id = find_out_float_socket(node_group)
    overlapping = []
    for obj in objects:
        modifier = find_modifier(obj, node_group)
        if modifier is None:
            continue
        in_range = get_key_range(obj, input_data_path(modifier, in_id)) if in_id else None
        out_range = get_key_range(obj, input_data_path(modifier, out_id)) if out_id else None
        if in_range and out_range and out_range[0] < in_range[1]:
            overlapping.append(obj.name)
    if overlapping:
        names = ", ".join(overlapping[:3]) + (" ..." if len(overlapping) > 3 else "")
        operator.report({'WARNING'}, f"Out starts before In ends on {len(overlapping)} object(s): {names}")


def node_group_in_use(node_group):
    """Jumlah user nyata (fake user tidak dihitung)"""
    return node_group.users - (1 if node_group.use_fake_user else 0) > 0


def get_node_group_version(node_group):
    """Versi template node group. Template lama belum punya penanda versi (= 1)"""
    return int(node_group.get("animz_version", 1))


def get_template_path():
    """Path template auto_pop_up.blend di folder addon"""
    addon_path = os.path.dirname(os.path.realpath(__file__))
    template_file = os.path.join(addon_path, "template", "auto_pop_up.blend")
    if not os.path.exists(template_file):
        # Alternatif: file .blend di root folder fileset
        alt_template = os.path.join(addon_path, "auto_pop_up.blend")
        if os.path.exists(alt_template):
            return alt_template
    return template_file


# =======================================================
# Preset list (read from the template node group names)
# =======================================================

# Preset groups in the template are named "<In|Out> <NN> | <Name>", e.g. "In 05 | Slide ↓ Elastic".
# NN is the index in the In/Out library. A new group with the next number appears in the menu.
PRESET_NAME_RE = re.compile(r"^(In|Out) (\d+) \| (.+)$")

# Used only when the template cannot be read
FALLBACK_PRESETS = {
    "In": ["Ease Out", "Ease In Out", "Bounce", "Jump & Bounce", "Jump, Rotate & Bounce", "Slide ↓ Elastic",
           "Slide ↑ Ease Out", "Slide ↓ Ease Out", "Slide → Ease Out", "Slide ← Ease Out", "Rotate ← & Back",
           "Bounce & Swing X", "Drop Jiggle"],
    "Out": ["Ease In", "Ease In Out", "Back", "Jump & Bounce", "Jump, Rotate & Bounce", "X-Axis Scale",
            "Slide ↑ Ease Out", "Slide ↓ Ease Out", "Slide → Ease Out", "Slide ← Ease Out", "Rotate ← & Back"],
}

# Suggested duration shown in the tooltip. Presets not listed show "30 Frame".
PRESET_HINTS = {
    "In": {5: "60-90 Frame, Linear", 6: "20-45 Frame", 7: "20-45 Frame", 8: "20-45 Frame", 9: "20-45 Frame",
           12: "60-90 Frame"},
    "Out": {6: "20-45 Frame", 7: "20-45 Frame", 8: "20-45 Frame", 9: "20-45 Frame"},
}

# Enum items must stay referenced while Blender uses them, so keep them in a module cache
_preset_items_cache = {}


def read_template_presets():
    """{"In": {index: name}, "Out": {...}} from the template node group names (names only, nothing is appended)"""
    found = {"In": {}, "Out": {}}
    path = get_template_path()
    if not os.path.exists(path):
        return found
    try:
        if bpy.data.filepath and os.path.samefile(bpy.data.filepath, path):
            names = [g.name for g in bpy.data.node_groups]  # Editing the template itself
        else:
            with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
                names = list(data_from.node_groups)
    except Exception as e:
        print(f"AnimZ: could not read presets from template: {e}")
        return found
    for name in names:
        match = PRESET_NAME_RE.match(name)
        if match:
            found[match.group(1)][int(match.group(2))] = match.group(3)
    return found


def preset_items(direction):
    """EnumProperty items for 'In' or 'Out': (identifier, name, description, value)"""
    if direction not in _preset_items_cache:
        presets = read_template_presets()[direction] or dict(enumerate(FALLBACK_PRESETS[direction]))
        hints = PRESET_HINTS[direction]
        _preset_items_cache[direction] = [
            (str(k), name, f"{k} | {hints.get(k, '30 Frame')}", k) for k, name in sorted(presets.items())
        ]
    return _preset_items_cache[direction]


def preset_label(direction, identifier):
    """Display name of a preset identifier, e.g. preset_label('In', '3') -> 'Jump & Bounce'"""
    return next((item[1] for item in preset_items(direction) if item[0] == identifier), "Unknown")


def append_template_node_group(name=NODE_GROUP_NAME):
    """
    Append node group dari template. Bila nama sudah dipakai, Blender memberi
    akhiran .001, nilai return selalu node group hasil append.
    """
    template_file = get_template_path()
    if not os.path.exists(template_file):
        return None
    with bpy.data.libraries.load(template_file, link=False) as (data_from, data_to):
        if name not in data_from.node_groups:
            return None
        data_to.node_groups = [name]
    node_group = data_to.node_groups[0] if data_to.node_groups else None
    if node_group:
        node_group.use_fake_user = False
    return node_group


def collect_nested_groups(node_group, found=None):
    """Semua node group di dalam node_group (rekursif)"""
    if found is None:
        found = set()
    for node in node_group.nodes:
        tree = getattr(node, 'node_tree', None)
        if tree and tree not in found:
            found.add(tree)
            collect_nested_groups(tree, found)
    return found


def get_or_append_node_group(name=NODE_GROUP_NAME):
    """Pakai node group yang sudah ada di file, append dari template bila belum ada"""
    node_group = bpy.data.node_groups.get(name)
    if node_group:
        return node_group
    node_group = append_template_node_group(name)
    if node_group:
        node_group.name = name
    return node_group


def add_wiggle_modifier(obj, wiggle_group, source=None):
    """
    Tambah (atau pakai yang ada) modifier auto_wiggle dengan seed acak.
    source: modifier wiggle lain untuk disalin nilainya (kecuali Seed).
    Returns modifier.
    """
    modifier = find_modifier(obj, wiggle_group)
    if modifier is None:
        modifier = obj.modifiers.new(name=WIGGLE_NODE_GROUP_NAME, type='NODES')
        modifier.node_group = wiggle_group
    seed_id = find_socket_by_name(wiggle_group, "Seed", 'NodeSocketInt')
    if source is not None and source != modifier:
        copy_wiggle_settings(wiggle_group, source, modifier)
    if seed_id and has_input(modifier, seed_id):
        set_input(modifier, seed_id, random.randint(0, 99999))
    return modifier


def copy_wiggle_settings(wiggle_group, source, target):
    """Salin semua nilai wiggle dari source ke target, kecuali Seed"""
    for item in wiggle_group.interface.items_tree:
        if (item.item_type != 'SOCKET' or item.in_out != 'INPUT' or
                item.socket_type == 'NodeSocketGeometry' or item.name == "Seed"):
            continue
        if has_input(source, item.identifier) and has_input(target, item.identifier):
            value = get_input(source, item.identifier)
            set_input(target, item.identifier, tuple(value) if hasattr(value, '__len__') else value)


# Live sync: setting wiggle yang diubah di object aktif ikut ke object terpilih lain yang punya wiggle.
# Snapshot menyimpan nilai terakhir object aktif, jadi hanya socket yang benar-benar diubah yang disalin,
# dan ganti object aktif / pilih object lain tidak menimpa setting siapa pun.
_wiggle_sync = {"key": None, "values": {}, "busy": False}


def wiggle_values(wiggle_group, modifier):
    """Nilai input wiggle (kecuali Geometry dan Seed), vector jadi tuple supaya bisa dibandingkan"""
    values = {}
    for item in wiggle_group.interface.items_tree:
        if (item.item_type != 'SOCKET' or item.in_out != 'INPUT' or
                item.socket_type == 'NodeSocketGeometry' or item.name == "Seed"):
            continue
        if has_input(modifier, item.identifier):
            value = get_input(modifier, item.identifier)
            values[item.identifier] = tuple(value) if hasattr(value, '__len__') else value
    return values


def reset_wiggle_sync(*_args):
    """Lupakan snapshot (undo, redo, buka file), supaya perubahan itu tidak dianggap edit user"""
    _wiggle_sync["key"] = None
    _wiggle_sync["values"] = {}


@persistent
def wiggle_sync_handler(scene, depsgraph):
    if _wiggle_sync["busy"]:
        return
    props = getattr(scene, "animz_properties", None)
    view_layer = bpy.context.view_layer
    wiggle_group = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
    if props is None or not props.wiggle_sync or view_layer is None or wiggle_group is None:
        reset_wiggle_sync()
        return
    active = view_layer.objects.active
    modifier = find_modifier(active, wiggle_group) if active else None
    if modifier is None:
        reset_wiggle_sync()
        return

    key = (scene.name, active.name, modifier.name)
    values = wiggle_values(wiggle_group, modifier)
    previous = _wiggle_sync["values"]
    changed = {} if key != _wiggle_sync["key"] else {k: v for k, v in values.items() if previous.get(k) != v}
    _wiggle_sync["key"] = key
    _wiggle_sync["values"] = values
    if not changed:
        return

    _wiggle_sync["busy"] = True
    synced = []
    try:
        for obj in view_layer.objects.selected:
            if obj == active:
                continue
            target = find_modifier(obj, wiggle_group)
            if target is None:
                continue
            for identifier, value in changed.items():
                if has_input(target, identifier) and wiggle_values_differ(target, identifier, value):
                    set_input(target, identifier, value)
                    if obj.name not in synced:
                        synced.append(obj.name)
    finally:
        _wiggle_sync["busy"] = False
    if synced:
        # Tag yang dibuat di dalam depsgraph_update_post dibuang setelah handler selesai,
        # jadi object tujuan tidak pernah dievaluasi ulang. Tag ulang dari timer (di luar update).
        bpy.app.timers.register(lambda names=tuple(synced): refresh_objects(names), first_interval=0.0)


def refresh_objects(names):
    """Evaluasi ulang object (dipanggil dari timer) dan gambar ulang viewport"""
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.update_tag()
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return None  # sekali jalan


def wiggle_values_differ(modifier, identifier, value):
    """Set hanya bila beda, supaya tidak memicu update depsgraph yang tidak perlu"""
    current = get_input(modifier, identifier)
    return (tuple(current) if hasattr(current, '__len__') else current) != value


def upgrade_node_group():
    """
    Ganti node group lama dengan versi template terbaru. Modifier dan keyframe
    tetap terhubung karena identifier socket tidak berubah.
    Object yang memakai Wiggle lama (v2) mendapat modifier auto_wiggle baru.
    Returns: (success: bool, message: str)
    """
    old = bpy.data.node_groups.get(NODE_GROUP_NAME)

    # Object dengan Wiggle lama aktif (Wiggle dulu ada di dalam auto_pop_up)
    wiggle_objects = []
    if old is not None:
        old_wiggle_id = find_socket_by_name(old, "Wiggle", 'NodeSocketBool')
        if old_wiggle_id:
            for obj in bpy.data.objects:
                mod = find_modifier(obj, old)
                if mod and has_input(mod, old_wiggle_id) and get_input(mod, old_wiggle_id):
                    wiggle_objects.append(obj)

    new = append_template_node_group()
    if new is None:
        return (False, f"Template not found: {get_template_path()}")
    if old is None:
        new.name = NODE_GROUP_NAME
        return (True, f"Appended node group v{TEMPLATE_VERSION}")

    old_version = get_node_group_version(old)
    old_subgroups = collect_nested_groups(old)
    old.user_remap(new)
    bpy.data.node_groups.remove(old)
    for sub in old_subgroups:
        if sub.users == 0:
            bpy.data.node_groups.remove(sub)

    # Kembalikan nama asli (tanpa akhiran .001)
    new.name = NODE_GROUP_NAME
    for sub in collect_nested_groups(new):
        base = re.sub(r"\.\d{3}$", "", sub.name)
        if base != sub.name and base not in bpy.data.node_groups:
            sub.name = base

    message = f"Upgraded node group v{old_version} -> v{TEMPLATE_VERSION}"
    if wiggle_objects:
        wiggle_group = get_or_append_node_group(WIGGLE_NODE_GROUP_NAME)
        if wiggle_group:
            for obj in wiggle_objects:
                add_wiggle_modifier(obj, wiggle_group)
            message += f" | Wiggle moved to separate modifier on {len(wiggle_objects)} object(s)"
    return (True, message)


def outdated_node_groups():
    """Node groups in this file older than the template: list of (name, file_version, template_version)"""
    found = []
    for name, target in ((NODE_GROUP_NAME, TEMPLATE_VERSION), (WIGGLE_NODE_GROUP_NAME, WIGGLE_VERSION)):
        group = bpy.data.node_groups.get(name)
        if group is not None and get_node_group_version(group) < target:
            found.append((name, get_node_group_version(group), target))
    return found


def outdated_text():
    """Short label for the panel warning, or None when everything is current"""
    found = outdated_node_groups()
    if not found:
        return None
    return " | ".join(f"{name} v{old} < v{new}" for name, old, new in found)


def upgrade_wiggle_group():
    """
    Ganti auto_wiggle lama dengan versi template. Modifier tetap memakai socket
    identifier yang sama, jadi nilai dan keyframe tetap terhubung.
    v1 -> v2: Randomness dulu = noise penuh, sekarang 0 = gelombang halus rata,
    jadi Randomness dan Random Offset di-reset ke default baru.
    Returns: (success: bool, message: str)
    """
    old = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
    if old is None or get_node_group_version(old) >= WIGGLE_VERSION:
        return (True, "")
    new = append_template_node_group(WIGGLE_NODE_GROUP_NAME)
    if new is None:
        return (False, f"Template not found: {get_template_path()}")

    old_version = get_node_group_version(old)
    modifiers = [m for obj in bpy.data.objects for m in obj.modifiers
                 if m.type == 'NODES' and m.node_group == old]
    for mod in modifiers:
        mod.node_group = new  # Reassign so the modifier picks up the new sockets
    old.user_remap(new)
    bpy.data.node_groups.remove(old)
    new.name = WIGGLE_NODE_GROUP_NAME
    new.use_fake_user = True

    if old_version < 2:
        reset = {}
        for name in ("Randomness", "Random Offset"):
            item = next((i for i in new.interface.items_tree
                         if i.item_type == 'SOCKET' and i.in_out == 'INPUT' and i.name == name), None)
            if item is not None:
                reset[item.identifier] = item.default_value
        for mod in modifiers:
            for identifier, value in reset.items():
                if has_input(mod, identifier):
                    set_input(mod, identifier, value)
    return (True, f"Upgraded auto_wiggle v{old_version} -> v{WIGGLE_VERSION} on {len(modifiers)} object(s)")


def find_float_socket(node_group):
    """
    Cari socket identifier untuk input float bernama 'In' di Geometry Node Group.
    Blender 5.0+ menggunakan node_group.interface.items_tree
    """
    if not node_group or not hasattr(node_group, 'interface'):
        return None
    
    # Prioritaskan socket dengan nama "In" bertipe float
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and 
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketFloat'):
            if item.name == "In":
                return item.identifier
    
    # Fallback: ambil socket float input pertama
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and 
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketFloat'):
            return item.identifier
    
    return None


def find_int_socket(node_group):
    """
    Cari socket identifier untuk input integer (biasanya socket_4) untuk tipe animasi.
    """
    if not node_group or not hasattr(node_group, 'interface'):
        return None
    
    # Prioritaskan socket "In Presets" (template sekarang) atau "Type" (template lama)
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt'):
            if item.name in ("In Presets", "Type"):
                return item.identifier
    
    # Fallback: ambil socket integer input pertama
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and 
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt'):
            return item.identifier
    
    return None


def setup_popup_modifier(obj, context, node_group, animation_type_value, add_keyframes=True):
    """
    Setup modifier auto_pop_up pada object (dengan atau tanpa keyframing).
    
    Args:
        obj: Object target
        context: Blender context
        node_group: Node group 'auto_pop_up'
        animation_type_value: Nilai integer untuk type animasi
        add_keyframes: Boolean - True untuk tambah keyframes, False untuk skip
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Cari socket IDs
        float_socket_id = find_float_socket(node_group)
        int_socket_id = find_int_socket(node_group)
        
        if not float_socket_id:
            return (False, f"Cannot find float socket on {obj.name}")
        
        # === 1. CARI ATAU BUAT MODIFIER ===
        modifier = None
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_group:
                modifier = mod
                break
        
        if modifier is None:
            modifier = obj.modifiers.new(name="auto_pop_up", type='NODES')
            modifier.node_group = node_group

        # === 2. PINDAHKAN MODIFIER KE INDEX 0 ===
        mod_index = obj.modifiers.find(modifier.name)
        if mod_index > 0:
            with context.temp_override(active_object=obj, object=obj):
                for _ in range(mod_index):
                    bpy.ops.object.modifier_move_up(modifier=modifier.name)
        
        # === 3. SET NILAI SOCKET INTEGER (TYPE ANIMASI) ===
        if int_socket_id and has_input(modifier, int_socket_id):
            try:
                set_input(modifier, int_socket_id, animation_type_value)
            except Exception as e:
                pass  # Non-critical
        
        # === 4. SETUP KEYFRAMES (OPSIONAL) ===
        if add_keyframes:
            scene = context.scene
            animz_props = scene.animz_properties
            
            current_frame = scene.frame_current
            end_frame = current_frame + animz_props.frame_duration
            
            data_path = input_data_path(modifier, float_socket_id)
            
            # Validasi akses socket float
            try:
                _ = get_input(modifier, float_socket_id)
            except Exception as e:
                return (False, f"Float socket inaccessible on {obj.name}: {str(e)}")
            
            # Ganti animasi lama (bukan menambah), supaya object tidak pop dua kali
            clear_keyframes(obj, data_path)
            
            # Insert keyframes (tipe Jitter / hijau, supaya mudah dibedakan di timeline)
            set_input(modifier, float_socket_id, 0.0)
            obj.keyframe_insert(data_path=data_path, frame=current_frame, keytype='JITTER')

            set_input(modifier, float_socket_id, 1.0)
            obj.keyframe_insert(data_path=data_path, frame=end_frame, keytype='JITTER')
            
            # Set interpolasi bezier
            set_fcurve_bezier(obj, data_path)
        
        return (True, "Success")
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return (False, str(e))

def find_out_float_socket(node_group):
    """Cari socket identifier untuk input float bernama 'Out'."""
    if not node_group or not hasattr(node_group, 'interface'):
        return None
    
    # Prioritaskan nama eksak "Out"
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketFloat' and
            item.name.strip() == "Out"):  # Strip whitespace!
            return item.identifier
    
    # Fallback: cari case-insensitive
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketFloat' and
            "out" in item.name.lower()):
            return item.identifier
    
    # Fallback akhir: ambil float input KEDUA
    floats = [i.identifier for i in node_group.interface.items_tree
              if i.item_type == 'SOCKET' and i.in_out == 'INPUT' 
              and i.socket_type == 'NodeSocketFloat']
    return floats[1] if len(floats) > 1 else (floats[0] if floats else None)

def find_out_int_socket(node_group):
    """Cari socket identifier untuk input integer bernama 'Out Presets'."""
    if not node_group or not hasattr(node_group, 'interface'):
        return None
    
    # Prioritaskan nama eksak "Out Presets"
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt' and
            item.name.strip() == "Out Presets"):  # Strip whitespace!
            return item.identifier
    
    # Fallback: cari case-insensitive
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt' and
            "out" in item.name.lower() and "preset" in item.name.lower()):
            return item.identifier
    
    # Fallback akhir: ambil integer input KEDUA
    ints = [i.identifier for i in node_group.interface.items_tree
            if i.item_type == 'SOCKET' and i.in_out == 'INPUT' 
            and i.socket_type == 'NodeSocketInt']
    return ints[1] if len(ints) > 1 else (ints[0] if ints else None)

def setup_popup_out_modifier(obj, context, node_group, animation_type_value, add_keyframes=True):
    try:
        float_socket_id = find_out_float_socket(node_group)  # Helper khusus OUT
        int_socket_id = find_out_int_socket(node_group)      # Helper khusus OUT
        
        if not float_socket_id:
            return (False, f"Cannot find OUT float socket on {obj.name}")
        
        # === 1. CARI/BUAT MODIFIER (sama seperti IN) ===
        modifier = None
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_group:
                modifier = mod
                break
        if modifier is None:
            modifier = obj.modifiers.new(name="auto_pop_up", type='NODES')
            modifier.node_group = node_group

        # === 2. PINDAH KE INDEX 0 (sama seperti IN) ===
        mod_index = obj.modifiers.find(modifier.name)
        if mod_index > 0:
            with context.temp_override(active_object=obj, object=obj):
                for _ in range(mod_index):
                    bpy.ops.object.modifier_move_up(modifier=modifier.name)
        
        # === 3. SET NILAI SOCKET INTEGER (OUT TYPE) + FORCE UPDATE ===
        if int_socket_id and has_input(modifier, int_socket_id):
            try:
                # LANGKAH KRITIS 1: Set nilai
                set_input(modifier, int_socket_id, animation_type_value)
                
                # LANGKAH KRITIS 2: Force depsgraph tag pada object
                obj.update_tag(refresh={'OBJECT'})
                
                # LANGKAH KRITIS 3: Force modifier re-evaluation
                # Metode paling reliable di Blender 5.x:
                if hasattr(modifier, "node_group"):
                    # Trigger recompile node tree
                    modifier.node_group.interface_update(context)
                
            except Exception as e:
                print(f"Warning: Failed to set OUT preset on {obj.name}: {e}")
        
        # === 4. SETUP KEYFRAMES KHUSUS OUT (0.0 → 1.0) ===
        if add_keyframes:
            scene = context.scene
            animz_props = scene.animz_properties
            current_frame = scene.frame_current
            end_frame = current_frame + animz_props.out_frame_duration
            data_path = input_data_path(modifier, float_socket_id)
            
            # Validasi akses socket
            try:
                _ = get_input(modifier, float_socket_id)
            except Exception as e:
                return (False, f"OUT float socket inaccessible: {str(e)}")
            
            # Ganti animasi lama (bukan menambah), supaya object tidak pop dua kali
            clear_keyframes(obj, data_path)
            
            # INSERT KEYFRAMES: OUT animation (0.0 → 1.0), tipe Jitter (hijau)
            set_input(modifier, float_socket_id, 0.0)
            obj.keyframe_insert(data_path=data_path, frame=current_frame, keytype='JITTER')
            set_input(modifier, float_socket_id, 1.0)
            obj.keyframe_insert(data_path=data_path, frame=end_frame, keytype='JITTER')
            
            # Set interpolasi bezier
            set_fcurve_bezier(obj, data_path)
        
        # === 5. FINAL VIEWPORT UPDATE (PENTING!) ===
        context.view_layer.update()
        # Force redraw viewport (opsional, gagal bila tidak ada window)
        try:
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        except RuntimeError:
            pass
        
        return (True, "Success")
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return (False, str(e))

# =======================================================
# Operator
# =======================================================

class ANIMZ_OT_append_node(Operator):
    """Append 'auto_pop_up' geometry node group from template file"""
    bl_idname = "animz.append_node"
    bl_label = "Append Node Group"
    bl_description = "Append 'auto_pop_up' geometry node group from addon template"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        existing = bpy.data.node_groups.get(NODE_GROUP_NAME)
        if existing:
            self.report({'INFO'}, f"Node group '{NODE_GROUP_NAME}' already exists in file (v{get_node_group_version(existing)})")
            return {'FINISHED'}

        try:
            node_group = get_or_append_node_group()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to append node group: {e}")
            return {'CANCELLED'}

        if node_group is None:
            self.report({'ERROR'}, f"Template not found or has no '{NODE_GROUP_NAME}' node group: {get_template_path()}")
            return {'CANCELLED'}
        if node_group.type != 'GEOMETRY':
            self.report({'WARNING'}, f"Appended node group '{NODE_GROUP_NAME}' is not a Geometry Node type (type: {node_group.type})")
            return {'CANCELLED'}

        self.report({'INFO'}, f"✓ Successfully appended '{NODE_GROUP_NAME}' geometry node group")
        return {'FINISHED'}


class ANIMZ_OT_upgrade_node_group(Operator):
    """Replace the auto_pop_up node group in this file with the latest template"""
    bl_idname = "animz.upgrade_node_group"
    bl_label = "Upgrade Node Group"
    bl_description = ("Replace outdated auto_pop_up / auto_wiggle node groups with the latest template. "
                      "Existing modifiers and keyframes are kept, but their motion may change")
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            messages = []
            success = True
            pop = bpy.data.node_groups.get(NODE_GROUP_NAME)
            if pop is not None and get_node_group_version(pop) < TEMPLATE_VERSION:
                success, msg = upgrade_node_group()
                messages.append(msg)
            if success:
                success, msg = upgrade_wiggle_group()
                messages.append(msg)
            message = " | ".join(m for m in messages if m) or "Node groups are up to date"
        except Exception as e:
            import traceback
            traceback.print_exc()
            success, message = False, str(e)
        if not success:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        for obj in context.scene.objects:
            obj.update_tag()
        context.view_layer.update()
        self.report({'INFO'}, message)
        return {'FINISHED'}

class ANIMZ_OT_animate_popup(Operator):
    """Animate auto_pop_up geometry node on selected objects (auto-append if missing)"""
    bl_idname = "animz.animate_popup"
    bl_label = "Animate PopUp"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        animz_props = scene.animz_properties
        
        selected_objects = get_supported_selected(context)
        
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}

        # === AUTO-APPEND NODE GROUP JIKA BELUM ADA ===
        node_group = get_or_append_node_group()
        if node_group is None:
            self.report({'ERROR'}, "Failed to append 'auto_pop_up' node group. Please check:\n"
                                  "1. Template file exists in addon's 'template/' folder\n"
                                  "2. Node group named 'auto_pop_up' exists in template file")
            return {'CANCELLED'}

        animation_type_value = int(animz_props.popup_type)
        error = check_preset_supported(node_group, find_int_socket(node_group), animation_type_value)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        # Dapatkan label type untuk report
        type_label = preset_label("In", animz_props.popup_type)

        animated_count = 0

        for obj in selected_objects:
            success, message = setup_popup_modifier(
                obj,
                context,
                node_group,
                animation_type_value,
                add_keyframes=True  # DENGAN keyframes
            )

            if success:
                animated_count += 1
            else:
                self.report({'WARNING'}, f"Failed: {message}")

        # Force viewport update
        context.view_layer.update()

        if animated_count == 0:
            self.report({'WARNING'}, "No objects animated successfully")
            return {'CANCELLED'}

        report_overlaps(self, selected_objects, node_group)
        self.report({'INFO'}, f"Animated {animated_count} object(s) | Type: {type_label}")
        return {'FINISHED'}

class ANIMZ_OT_animate_out_popup(Operator):
    """Animate OUT animation using auto_pop_up geometry node"""
    bl_idname = "animz.animate_out_popup"
    bl_label = "Animate Out PopUp"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        animz_props = scene.animz_properties
        selected_objects = get_supported_selected(context)
        
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}
        
        # Auto-append node group jika belum ada (sama seperti IN)
        node_group = get_or_append_node_group()
        if node_group is None:
            self.report({'ERROR'}, "Failed to append node group")
            return {'CANCELLED'}

        animation_type_value = int(animz_props.out_type)
        error = check_preset_supported(node_group, find_out_int_socket(node_group), animation_type_value)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        # Dapatkan label type
        type_label = preset_label("Out", animz_props.out_type)
        
        animated_count = 0
        for obj in selected_objects:
            success, message = setup_popup_out_modifier(
                obj, context, node_group, animation_type_value, add_keyframes=True
            )
            if success:
                animated_count += 1
            else:
                self.report({'WARNING'}, f"Failed on {obj.name}: {message}")
        
        context.view_layer.update()
        
        if animated_count == 0:
            self.report({'WARNING'}, "No objects animated successfully")
            return {'CANCELLED'}

        report_overlaps(self, selected_objects, node_group)
        self.report({'INFO'}, f"OUT Animated {animated_count} object(s) | Type: {type_label}")
        return {'FINISHED'}

class ANIMZ_OT_update_in_animation(Operator):
    """Update IN animation type by changing socket value only (preserves all keyframes)"""
    bl_idname = "animz.update_in_animation"
    bl_label = "Update In Type"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        animz_props = scene.animz_properties
        selected_objects = get_supported_selected(context)
        
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}

        if "auto_pop_up" not in bpy.data.node_groups:
            self.report({'ERROR'}, "Geometry Node 'auto_pop_up' not found in file")
            return {'CANCELLED'}
        
        node_group = bpy.data.node_groups["auto_pop_up"]
        animation_type_value = int(animz_props.popup_type)
        int_socket_id = find_int_socket(node_group)  # Socket untuk IN Presets (socket_4)
        
        if not int_socket_id:
            self.report({'ERROR'}, "Cannot find IN preset socket (socket_4)")
            return {'CANCELLED'}
        error = check_preset_supported(node_group, int_socket_id, animation_type_value)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        
        updated_count = 0
        for obj in selected_objects:
            # Cari modifier auto_pop_up yang ada
            modifier = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == node_group:
                    modifier = mod
                    break
            
            if not modifier or not has_input(modifier, int_socket_id):
                continue  # Skip object tanpa modifier atau socket tidak tersedia
            
            # === UPDATE NILAI SOCKET LANGSUNG (TANPA HAPUS MODIFIER) ===
            try:
                # Set nilai baru
                set_input(modifier, int_socket_id, animation_type_value)
                
                # Force depsgraph update (KRITIS untuk viewport refresh)
                obj.update_tag(refresh={'OBJECT'})
                context.view_layer.update()
                
                updated_count += 1
            except Exception as e:
                self.report({'WARNING'}, f"Failed on {obj.name}: {e}")
                continue
        
        # Dapatkan label type untuk report
        type_label = preset_label("In", animz_props.popup_type)
        
        if updated_count == 0:
            self.report({'WARNING'}, "No modifiers updated (check if objects have auto_pop_up modifier)")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"✓ Updated IN type to '{type_label}' on {updated_count} object(s)")
        return {'FINISHED'}

class ANIMZ_OT_update_out_animation(Operator):
    """Update OUT animation type by changing socket value only (preserves all keyframes)"""
    bl_idname = "animz.update_out_animation"
    bl_label = "Update Out Type"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        animz_props = scene.animz_properties
        selected_objects = get_supported_selected(context)
        
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}
        
        if "auto_pop_up" not in bpy.data.node_groups:
            self.report({'ERROR'}, "Geometry Node 'auto_pop_up' not found in file")
            return {'CANCELLED'}
        
        node_group = bpy.data.node_groups["auto_pop_up"]
        animation_type_value = int(animz_props.out_type)
        int_socket_id = find_out_int_socket(node_group)  # Socket untuk OUT Presets (socket_5)
        
        if not int_socket_id:
            self.report({'ERROR'}, "Cannot find OUT preset socket (socket_5)")
            return {'CANCELLED'}
        error = check_preset_supported(node_group, int_socket_id, animation_type_value)
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        
        updated_count = 0
        for obj in selected_objects:
            # Cari modifier auto_pop_up yang ada
            modifier = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == node_group:
                    modifier = mod
                    break
            
            if not modifier or not has_input(modifier, int_socket_id):
                continue  # Skip object tanpa modifier atau socket tidak tersedia
            
            # === UPDATE NILAI SOCKET LANGSUNG (TANPA HAPUS MODIFIER) ===
            try:
                # Set nilai baru
                set_input(modifier, int_socket_id, animation_type_value)
                
                # Force depsgraph update (KRITIS untuk viewport refresh - ini solusi bug Anda!)
                obj.update_tag(refresh={'OBJECT'})
                
                # Force Geometry Nodes re-evaluation (Blender 5.x specific)
                if hasattr(bpy.context, 'view_layer'):
                    bpy.context.view_layer.depsgraph.update()
                
                # Force viewport redraw (untuk immediate visual feedback)
                try:
                    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                except RuntimeError:
                    pass
                
                updated_count += 1
            except Exception as e:
                self.report({'WARNING'}, f"Failed on {obj.name}: {e}")
                continue
        
        # Dapatkan label type untuk report
        type_label = preset_label("Out", animz_props.out_type)
        
        if updated_count == 0:
            self.report({'WARNING'}, "No modifiers updated (check if objects have auto_pop_up modifier)")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"✓ Updated OUT type to '{type_label}' on {updated_count} object(s)")
        return {'FINISHED'}
    
class ANIMZ_OT_delete_animation(Operator):
    """Remove auto_pop_up modifier in selected objects. Optional: purge node group from file."""
    bl_idname = "animz.delete_animation"
    bl_label = "Delete Animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    purge_node_group: bpy.props.BoolProperty(
        name="Purge Node Group",
        description="Also remove node group from .blend file if not used by any object",
        default=False
    )
    
    def execute(self, context):
        selected_objects = get_supported_selected(context)
        
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}
        
        total_modifiers_removed = 0
        total_fcurves_cleaned = 0
        objects_processed = 0
        shared_skipped = []
        node_group = bpy.data.node_groups.get(NODE_GROUP_NAME)

        for obj in selected_objects:
            try:
                # === LANGKAH 1: CARI MODIFIER ===
                modifier = find_modifier(obj, node_group)
                if not modifier:
                    continue

                # === LANGKAH 2: HAPUS FCURVE MILIK MODIFIER INI SAJA ===
                # Action yang dipakai bersama object lain tidak disentuh
                cleaned = remove_modifier_fcurves(obj, modifier.name)
                if cleaned < 0:
                    shared_skipped.append(obj.name)
                else:
                    total_fcurves_cleaned += cleaned

                # === LANGKAH 3: HAPUS MODIFIER ===
                obj.modifiers.remove(modifier)
                total_modifiers_removed += 1
                objects_processed += 1

            except Exception as e:
                self.report({'WARNING'}, f"Failed to process {obj.name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue

        if shared_skipped:
            self.report({'WARNING'}, f"Keyframes kept on {len(shared_skipped)} object(s) that share their action with other objects")

        # === LANGKAH 4: PURGE NODE GROUP (JIKA DIPILIH & TIDAK DIGUNAKAN) ===
        # users menghitung semua modifier di semua tipe object (Mesh, Curve, Text)
        node_group_purged = False
        node_group_still_in_use = False
        if self.purge_node_group and node_group is not None:
            node_group_still_in_use = node_group_in_use(node_group)
            if not node_group_still_in_use:
                try:
                    bpy.data.node_groups.remove(node_group, do_unlink=True)
                    node_group_purged = True
                except Exception as e:
                    self.report({'WARNING'}, f"Failed to purge node group: {e}")

        # Force viewport update
        context.view_layer.update()
        
        # === REPORT HASIL ===
        if total_modifiers_removed == 0:
            self.report({'INFO'}, "No auto_pop_up modifiers found on selected objects")
            return {'CANCELLED'}
        
        report_parts = [
            f"Removed {total_modifiers_removed} modifier(s) from {objects_processed} object(s)"
        ]
        
        if total_fcurves_cleaned > 0:
            report_parts.append(f"Removed {total_fcurves_cleaned} animation curve(s)")
        
        if self.purge_node_group:
            if node_group_purged:
                report_parts.append("✓ Node group purged from file")
            elif node_group_still_in_use:
                report_parts.append("⚠️ Node group NOT purged (still used by other objects)")
            else:
                report_parts.append("⚠️ Node group purge skipped (still in use)")
        
        self.report({'INFO'}, " | ".join(report_parts))
        return {'FINISHED'}
    
    def invoke(self, context, event):
        # Tampilkan dialog konfirmasi dengan opsi purge
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "purge_node_group")
        if self.purge_node_group:
            layout.label(text="Warning: This will permanently remove", icon='ERROR')
            layout.label(text="the node group from your .blend file!", icon='ERROR')


class ANIMZ_OT_add_wiggle(Operator):
    """Add a looping wiggle (location, rotation, scale) to selected objects"""
    bl_idname = "animz.add_wiggle"
    bl_label = "Add Wiggle"
    bl_description = ("Add a seamless looping wiggle to selected objects. Each object gets its own seed. "
                      "Settings are copied from the active object when it already has a wiggle")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = get_supported_selected(context)
        if not selected_objects:
            self.report({'WARNING'}, NO_SELECTION_MESSAGE)
            return {'CANCELLED'}

        wiggle_group = get_or_append_node_group(WIGGLE_NODE_GROUP_NAME)
        if wiggle_group is None:
            self.report({'ERROR'}, f"Template not found or has no '{WIGGLE_NODE_GROUP_NAME}' node group: {get_template_path()}")
            return {'CANCELLED'}

        active = context.active_object
        source = find_modifier(active, wiggle_group) if active else None
        for obj in selected_objects:
            add_wiggle_modifier(obj, wiggle_group, source)
        context.view_layer.update()
        self.report({'INFO'}, f"Wiggle added to {len(selected_objects)} object(s)")
        return {'FINISHED'}


class ANIMZ_OT_copy_wiggle(Operator):
    """Copy the active object's wiggle settings to the other selected objects"""
    bl_idname = "animz.copy_wiggle"
    bl_label = "Copy Wiggle to Selected"
    bl_description = "Copy the active object's wiggle settings to selected objects (each keeps its own seed)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        wiggle_group = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
        return bool(context.active_object and find_modifier(context.active_object, wiggle_group))

    def execute(self, context):
        wiggle_group = bpy.data.node_groups[WIGGLE_NODE_GROUP_NAME]
        source = find_modifier(context.active_object, wiggle_group)
        targets = [obj for obj in get_supported_selected(context) if obj != context.active_object]
        for obj in targets:
            add_wiggle_modifier(obj, wiggle_group, source)
        context.view_layer.update()
        self.report({'INFO'}, f"Wiggle copied to {len(targets)} object(s)")
        return {'FINISHED'}


class ANIMZ_OT_remove_wiggle(Operator):
    """Remove the wiggle modifier from selected objects"""
    bl_idname = "animz.remove_wiggle"
    bl_label = "Remove Wiggle"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        wiggle_group = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
        removed = 0
        for obj in get_supported_selected(context):
            modifier = find_modifier(obj, wiggle_group)
            if modifier is None:
                continue
            remove_modifier_fcurves(obj, modifier.name)
            obj.modifiers.remove(modifier)
            removed += 1
        if removed == 0:
            self.report({'INFO'}, "No wiggle found on selected objects")
            return {'CANCELLED'}
        context.view_layer.update()
        self.report({'INFO'}, f"Wiggle removed from {removed} object(s)")
        return {'FINISHED'}


# =======================================================
# Panel
# =======================================================

class ANIMZ_PanelDraw:
    """Shared AnimZ panel content for the N-panel and the Alt + ` popup"""
    bl_label = "AnimZ™"
    bl_space_type = 'VIEW_3D'
    bl_description = "Auto Pop-Up for animator based on geo-node"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        animz_props = scene.animz_properties
        
        layout.label(text="Auto Pop-Up")

        # Peringatan bila node group di file ini versi lama
        outdated = outdated_text()
        if outdated:
            warn = layout.box()
            warn.alert = True
            warn.label(text=f"Outdated: {outdated}", icon='ERROR')
            warn.operator("animz.upgrade_node_group", icon='FILE_REFRESH')

        # Create a single box for both In and Out animations
        main_box = layout.box()
        
        # Create a row inside the box to hold left and right columns
        row = main_box.row()
        
        # Left Column (In Animation)
        col1 = row.column()
        col1.label(text="In Animation")
        
        row_in1 = col1.row()
        row_in1.scale_y = 1.3
        split_in = row_in1.split(factor=0.8, align=True)
        split_in.prop(animz_props, "popup_type", text="")
        split_in.operator("animz.update_in_animation", text="", icon='FILE_REFRESH')
        
        row_in2 = col1.row(align=True)
        row_in2.label(text="Dur:", icon='TIME')
        row_in2.prop(animz_props, "frame_duration", text="")
        
        row_in3 = col1.row(align=True)
        row_in3.scale_y = 1.3
        row_in3.scale_x = 10
        row_in3.operator("animz.animate_popup", text="Animate In", icon='PLAY')

        # Right Column (Out Animation)
        col2 = row.column()
        col2.label(text="Out Animation")
        
        row_out1 = col2.row()
        row_out1.scale_y = 1.3
        split_out = row_out1.split(factor=0.8, align=True)
        split_out.prop(animz_props, "out_type", text="")
        split_out.operator("animz.update_out_animation", text="", icon='FILE_REFRESH')
        
        row_out2 = col2.row(align=True)
        row_out2.label(text="Dur:", icon='TIME')
        row_out2.prop(animz_props, "out_frame_duration", text="")
        
        row_out3 = col2.row(align=True)
        row_out3.scale_y = 1.3
        row_out3.scale_x = 10
        row_out3.operator("animz.animate_out_popup", text="Animate Out", icon='PLAY')

        main_box.separator()

        # === DELETE ANIMATION ===
        row = main_box.row()
        row.scale_y = 1.5
        row.operator("animz.delete_animation", text="Delete Animations", icon='TRASH')

        # === WIGGLE (modifier terpisah, hanya object yang bergoyang dihitung ulang tiap frame) ===
        layout.label(text="Wiggle Loop")
        wiggle_box = layout.box()
        row = wiggle_box.row(align=True)
        row.scale_y = 1.3
        row.operator("animz.add_wiggle", text="Add Wiggle", icon='FORCE_TURBULENCE')
        row.operator("animz.copy_wiggle", text="", icon='COPYDOWN')
        row.prop(context.scene.animz_properties, "wiggle_sync", text="",
                 icon='LINKED' if context.scene.animz_properties.wiggle_sync else 'UNLINKED')
        row.operator("animz.remove_wiggle", text="", icon='X')

        wiggle_group = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
        active = context.active_object
        wiggle_mod = find_modifier(active, wiggle_group) if active else None
        if wiggle_mod is not None:
            wiggle_box.label(text=f"Active: {active.name}", icon='OBJECT_DATA')
            col = wiggle_box.column(align=True)
            for item in wiggle_group.interface.items_tree:
                if (item.item_type == 'SOCKET' and item.in_out == 'INPUT' and
                        item.socket_type != 'NodeSocketGeometry' and has_input(wiggle_mod, item.identifier)):
                    if item.socket_type == 'NodeSocketVector':
                        col.label(text=f"{item.name}:")
                        draw_input(col.row(align=True), wiggle_mod, item.identifier, text="")
                    else:
                        draw_input(col, wiggle_mod, item.identifier, text=item.name)
        elif wiggle_group is not None:
            wiggle_box.label(text="Active object has no wiggle", icon='INFO')

        # Selected objects count
        layout.label(text=f"Selected Objects: {len(context.selected_objects)}")
        
        # # Validasi node group
        # if "auto_pop_up" not in bpy.data.node_groups:
        #     box = layout.box()
        #     box.label(text="⚠️ Node group not found!", icon='ERROR')

# =======================================================
# Property
# =======================================================

class ANIMZ_properties(PropertyGroup):
    """Properties untuk Animz addon"""
    
    # Preset list comes from the template (node groups named "In 00 | Ease Out" etc.),
    # so a new preset in the template shows up here without code changes
    popup_type: EnumProperty(
        name="In Type",
        description="Animation behavior for the pop-up effect",
        items=lambda self, context: preset_items("In"),
        default=0
    )
    
    out_type: EnumProperty(
        name="Out Type",
        description="Animation behavior for the out effect",
        items=lambda self, context: preset_items("Out"),
        default=0
    )
    
    frame_duration: IntProperty(
        name="In Duration",
        description="Number of frames for the popup animation (from 0 to 1)",
        default=30,
        min=1,
        max=240,
        subtype='TIME'
    )
    
    out_frame_duration: IntProperty(
        name="Out Duration",
        description="Number of frames for the out animation (from 0 to 1)",
        default=30,
        min=1,
        max=240,
        subtype='TIME'
    )

    popup_show_wiggle: BoolProperty(
        name="Wiggle Settings",
        description="Show the active object's wiggle settings in the Alt + ` popup",
        default=False
    )

    wiggle_sync: BoolProperty(
        name="Sync Wiggle to Selected",
        description=("Changing a wiggle setting (Strength, Location, ...) on the active object also sets it "
                     "on the other selected objects that have a wiggle. Each object keeps its own seed"),
        default=True
    )

# =======================================================
# Register/Unregister
# =======================================================

class ANIMZ_PT_panel(ANIMZ_PanelDraw, Panel):
    """AnimZ panel in the 3D Viewport sidebar (N-panel), ZeusLab tab"""
    bl_idname = "ANIMZ_PT_panel"
    bl_region_type = 'UI'
    bl_category = 'ZeusLab'

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_animz_panel
        return True


class ANIMZ_PT_popup(ANIMZ_PanelDraw, Panel):
    """AnimZ panel as a floating popup in the 3D Viewport (Alt + `)"""
    bl_idname = "ANIMZ_PT_popup"
    bl_region_type = 'WINDOW'
    bl_ui_units_x = 12

    def draw(self, context):
        """Compact layout: one row per action, so the popup covers little of the viewport"""
        layout = self.layout
        props = context.scene.animz_properties
        col = layout.column(align=False)

        if outdated_node_groups():
            row = col.row(align=True)
            row.alert = True
            row.operator("animz.upgrade_node_group", icon='ERROR', text="Upgrade Node Groups")

        # In / Out: [type][refresh][duration][animate]
        for type_prop, update_op, dur_prop, animate_op, label in (
                ("popup_type", "animz.update_in_animation", "frame_duration", "animz.animate_popup", "In"),
                ("out_type", "animz.update_out_animation", "out_frame_duration", "animz.animate_out_popup", "Out")):
            split = col.split(factor=0.5, align=True)
            split.prop(props, type_prop, text="")
            row = split.row(align=True)
            row.operator(update_op, text="", icon='FILE_REFRESH')
            row.prop(props, dur_prop, text="")
            row.operator(animate_op, text=label, icon='PLAY')

        # Wiggle and Delete: [wiggle][copy][sync][remove][settings]   [delete]
        row = col.row(align=False)
        sub = row.row(align=True)
        sub.operator("animz.add_wiggle", text="Wiggle", icon='FORCE_TURBULENCE')
        sub.operator("animz.copy_wiggle", text="", icon='COPYDOWN')
        sub.prop(props, "wiggle_sync", text="", icon='LINKED' if props.wiggle_sync else 'UNLINKED')
        sub.operator("animz.remove_wiggle", text="", icon='X')
        sub.prop(props, "popup_show_wiggle", text="", icon='PREFERENCES')
        row.operator("animz.delete_animation", text="", icon='TRASH')

        if not props.popup_show_wiggle:
            return
        wiggle_group = bpy.data.node_groups.get(WIGGLE_NODE_GROUP_NAME)
        active = context.active_object
        wiggle_mod = find_modifier(active, wiggle_group) if active and wiggle_group else None
        if wiggle_mod is None:
            col.label(text="Active object has no wiggle", icon='INFO')
            return
        box = col.box().column(align=True)
        for item in wiggle_group.interface.items_tree:
            if (item.item_type != 'SOCKET' or item.in_out != 'INPUT' or
                    item.socket_type == 'NodeSocketGeometry' or not has_input(wiggle_mod, item.identifier)):
                continue
            if item.socket_type == 'NodeSocketVector':
                split = box.split(factor=0.22, align=True)
                split.label(text=item.name)
                draw_input(split.row(align=True), wiggle_mod, item.identifier, text="")
            else:
                draw_input(box, wiggle_mod, item.identifier, text=item.name)


# =======================================================
# Right-click menu (Object Mode)
# =======================================================

def draw_context_menu(self, context):
    """Tombol Auto Pop-up di menu klik kanan Object Mode, membuka panel yang sama dengan Alt + `"""
    if context.mode != 'OBJECT':
        return
    layout = self.layout
    layout.separator()
    op = layout.operator("wm.call_panel", text="Auto Pop-up", icon='PLAY')
    op.name = ANIMZ_PT_popup.bl_idname
    op.keep_open = True


# =======================================================
# Keymap
# =======================================================

addon_keymaps = []


def register_keymap():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:  # Background mode
        return
    km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
    kmi = km.keymap_items.new("wm.call_panel", type='ACCENT_GRAVE', value='PRESS', alt=True)
    kmi.properties.name = ANIMZ_PT_popup.bl_idname
    kmi.properties.keep_open = True
    addon_keymaps.append((km, kmi))


def unregister_keymap():
    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
    addon_keymaps.clear()


# =======================================================
# Register/Unregister
# =======================================================

classes = (
    ANIMZ_properties,
    ANIMZ_OT_append_node,
    ANIMZ_OT_upgrade_node_group,
    ANIMZ_OT_animate_popup,
    ANIMZ_OT_animate_out_popup,
    ANIMZ_OT_update_in_animation,
    ANIMZ_OT_update_out_animation,
    ANIMZ_OT_delete_animation,
    ANIMZ_OT_add_wiggle,
    ANIMZ_OT_copy_wiggle,
    ANIMZ_OT_remove_wiggle,
    ANIMZ_PT_panel,
    ANIMZ_PT_popup,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.animz_properties = bpy.props.PointerProperty(type=ANIMZ_properties)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_context_menu)
    register_keymap()
    reset_wiggle_sync()
    bpy.app.handlers.depsgraph_update_post.append(wiggle_sync_handler)
    for handlers in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post, bpy.app.handlers.load_post):
        handlers.append(reset_wiggle_sync)


def unregister():
    for handlers in (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.undo_post,
                     bpy.app.handlers.redo_post, bpy.app.handlers.load_post):
        for fn in (wiggle_sync_handler, reset_wiggle_sync):
            if fn in handlers:
                handlers.remove(fn)
    unregister_keymap()
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_context_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.animz_properties


    # Notes:
    # 1. Tombol Update masih tolol, (Karena dia menghapus modifier dulu)
    # 2. Tombol Delete masih belum sempurna, karena geo-node masih tersimpan di file blender, harus nya di purge