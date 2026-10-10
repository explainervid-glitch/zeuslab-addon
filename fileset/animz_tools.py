import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import IntProperty, EnumProperty
from ..preferences import get_addon_preferences
import os

# =======================================================
# Function
# =======================================================

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
    
    # Prioritaskan socket dengan nama "Type" bertipe integer
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and 
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt'):
            if item.name == "Type":
                return item.identifier
    
    # Fallback: ambil socket integer input pertama
    for item in node_group.interface.items_tree:
        if (item.item_type == 'SOCKET' and 
            item.in_out == 'INPUT' and
            item.socket_type == 'NodeSocketInt'):
            return item.identifier
    
    return None


def remove_keyframes_at_frame(obj, data_path, frame):
    """Hapus keyframe existing di frame tertentu untuk mencegah duplikasi"""
    if not obj.animation_data or not obj.animation_data.action:
        return
    
    action = obj.animation_data.action
    # Akses fcurves dengan pengecekan aman
    if not hasattr(action, 'fcurves'):
        return
    
    for fcurve in action.fcurves:
        if fcurve.data_path == data_path:
            # Hapus dari belakang untuk menghindari index shift
            for i in range(len(fcurve.keyframe_points) - 1, -1, -1):
                if abs(fcurve.keyframe_points[i].co.x - frame) < 0.01:  # Toleransi floating point
                    fcurve.keyframe_points.remove(i, fast=True)
            fcurve.update()
            break


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
        if int_socket_id and int_socket_id in modifier:
            try:
                modifier[int_socket_id] = animation_type_value
            except Exception as e:
                pass  # Non-critical
        
        # === 4. SETUP KEYFRAMES (OPSIONAL) ===
        if add_keyframes:
            scene = context.scene
            animz_props = scene.animz_properties
            
            current_frame = scene.frame_current
            end_frame = current_frame + animz_props.frame_duration
            
            data_path = f'modifiers["{modifier.name}"]["{float_socket_id}"]'
            
            # Validasi akses socket float
            try:
                _ = modifier[float_socket_id]
            except Exception as e:
                return (False, f"Float socket inaccessible on {obj.name}: {str(e)}")
            
            # Hapus keyframe existing
            remove_keyframes_at_frame(obj, data_path, current_frame)
            remove_keyframes_at_frame(obj, data_path, end_frame)
            
            # Insert keyframes
            modifier[float_socket_id] = 0.0
            obj.keyframe_insert(data_path=data_path, frame=current_frame)
            
            modifier[float_socket_id] = 1.0
            obj.keyframe_insert(data_path=data_path, frame=end_frame)
            
            # Set interpolasi linear
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                if hasattr(action, 'fcurves'):
                    for fcurve in action.fcurves:
                        if fcurve.data_path == data_path:
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = 'LINEAR'
                            fcurve.update()
                            break
        
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
        if int_socket_id and int_socket_id in modifier:
            try:
                # LANGKAH KRITIS 1: Set nilai
                modifier[int_socket_id] = animation_type_value
                
                # LANGKAH KRITIS 2: Force depsgraph tag pada object
                obj.update_tag(refresh={'OBJECT'})
                
                # LANGKAH KRITIS 3: Force modifier re-evaluation
                # Metode paling reliable di Blender 5.x:
                if hasattr(modifier, "node_group"):
                    # Trigger recompile node tree
                    modifier.node_group.interface_update()
                
            except Exception as e:
                print(f"Warning: Failed to set OUT preset on {obj.name}: {e}")
        
        # === 4. SETUP KEYFRAMES KHUSUS OUT (0.0 → 1.0) ===
        if add_keyframes:
            scene = context.scene
            animz_props = scene.animz_properties
            current_frame = scene.frame_current
            end_frame = current_frame + animz_props.out_frame_duration
            data_path = f'modifiers["{modifier.name}"]["{float_socket_id}"]'
            
            # Validasi akses socket
            try:
                _ = modifier[float_socket_id]
            except Exception as e:
                return (False, f"OUT float socket inaccessible: {str(e)}")
            
            # Hapus keyframe existing
            remove_keyframes_at_frame(obj, data_path, current_frame)
            remove_keyframes_at_frame(obj, data_path, end_frame)
            
            # INSERT KEYFRAMES: OUT animation (0.0 → 1.0)
            modifier[float_socket_id] = 0.0
            obj.keyframe_insert(data_path=data_path, frame=current_frame)
            modifier[float_socket_id] = 1.0
            obj.keyframe_insert(data_path=data_path, frame=end_frame)
            
            # Set interpolasi linear
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                if hasattr(action, 'fcurves'):
                    for fcurve in action.fcurves:
                        if fcurve.data_path == data_path:
                            for kp in fcurve.keyframe_points:
                                kp.interpolation = 'LINEAR'
                            fcurve.update()
                            break
        
        # === 5. FINAL VIEWPORT UPDATE (PENTING!) ===
        context.view_layer.update()
        # Force redraw viewport (opsional tapi efektif)
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        
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
        # Dapatkan path addon (handle kasus di Text Editor vs installed addon)
        if __file__.endswith("<string>"):
            # Jika dijalankan dari Text Editor, gunakan path file .blend aktif
            addon_path = os.path.dirname(bpy.data.filepath)
        else:
            addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file template yang berisi node group
        template_dir = os.path.join(addon_path, "template")
        template_file = os.path.join(template_dir, "auto_pop_up.blend")
        
        # Validasi keberadaan direktori template
        if not os.path.exists(template_dir):
            self.report({'ERROR'}, f"Template directory not found:\n{template_dir}")
            return {'CANCELLED'}
        
        # Validasi keberadaan file .blend
        if not os.path.exists(template_file):
            # Cari alternatif: file .blend di root addon jika tidak ada di /template
            alt_template = os.path.join(addon_path, "auto_pop_up.blend")
            if os.path.exists(alt_template):
                template_file = alt_template
                self.report({'INFO'}, f"Using alternative template path:\n{alt_template}")
            else:
                self.report({'ERROR'}, f"Template file not found:\n{template_file}\n\nPlease ensure 'auto_pop_up.blend' exists in:\n{template_dir}")
                return {'CANCELLED'}
        
        # Cek apakah node group sudah ada
        node_group_name = "auto_pop_up"
        if node_group_name in bpy.data.node_groups:
            self.report({'INFO'}, f"Node group '{node_group_name}' already exists in file")
            return {'FINISHED'}
        
        # Lakukan append node group
        try:
            # Inner path untuk Node Group di Blender
            inner_path = "NodeTree"
            
            # Append dengan bpy.ops.wm.append
            bpy.ops.wm.append(
                filepath=os.path.join(template_file, inner_path, node_group_name),
                directory=os.path.join(template_file, inner_path),
                filename=node_group_name,
                set_fake=False,  # Penting: mencegah node group terhapus saat save
                link=False       # Pastikan di-append (bukan di-link)
            )
            
            # Validasi hasil append
            if node_group_name in bpy.data.node_groups:
                node_group = bpy.data.node_groups[node_group_name]
                # Pastikan ini Geometry Node Group
                if node_group.type == 'GEOMETRY':
                    self.report({'INFO'}, f"✓ Successfully appended '{node_group_name}' geometry node group")
                    # Tambahkan fake user untuk mencegah auto-delete
                    node_group.use_fake_user = False
                    return {'FINISHED'}
                else:
                    self.report({'WARNING'}, f"Appended node group '{node_group_name}' is not a Geometry Node type (type: {node_group.type})")
                    return {'CANCELLED'}
            else:
                self.report({'ERROR'}, f"Node group '{node_group_name}' not found after append attempt")
                return {'CANCELLED'}
                
        except Exception as e:
            import traceback
            self.report({'ERROR'}, f"Failed to append node group:\n{str(e)}")
            print("Append error traceback:")
            traceback.print_exc()
            return {'CANCELLED'}

class ANIMZ_OT_animate_popup(Operator):
    """Animate auto_pop_up geometry node on selected objects (auto-append if missing)"""
    bl_idname = "animz.animate_popup"
    bl_label = "Animate PopUp"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        animz_props = scene.animz_properties
        
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' or obj.type == 'CURVE']
        
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # === AUTO-APPEND NODE GROUP JIKA BELUM ADA ===
        if "auto_pop_up" not in bpy.data.node_groups:
            self.report({'INFO'}, "Node group 'auto_pop_up' not found. Attempting auto-append...")
            
            # Panggil operator append
            append_result = bpy.ops.animz.append_node()
            
            # Validasi hasil append
            if append_result != {'FINISHED'} or "auto_pop_up" not in bpy.data.node_groups:
                self.report({'ERROR'}, "Failed to append 'auto_pop_up' node group. Please check:\n"
                                      "1. Template file exists in addon's 'template/' folder\n"
                                      "2. Node group named 'auto_pop_up' exists in template file")
                return {'CANCELLED'}
            
            self.report({'INFO'}, "✓ Successfully appended 'auto_pop_up' node group")
        
        # Lanjutkan proses animasi setelah node group tersedia
        node_group = bpy.data.node_groups["auto_pop_up"]
        animation_type_value = int(animz_props.popup_type)
        
        # Dapatkan label type untuk report
        type_label = 'Unknown'
        for item in ANIMZ_properties.popup_type_items:
            if item[0] == animz_props.popup_type:
                type_label = item[1]
                break
        
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
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' or obj.type == 'CURVE']
        
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        # Auto-append node group jika belum ada (sama seperti IN)
        if "auto_pop_up" not in bpy.data.node_groups:
            append_result = bpy.ops.animz.append_node()
            if append_result != {'FINISHED'} or "auto_pop_up" not in bpy.data.node_groups:
                self.report({'ERROR'}, "Failed to append node group")
                return {'CANCELLED'}
        
        node_group = bpy.data.node_groups["auto_pop_up"]
        animation_type_value = int(animz_props.out_type)
        
        # Dapatkan label type
        type_label = 'Unknown'
        for item in ANIMZ_properties.out_type_items:
            if item[0] == animz_props.out_type:
                type_label = item[1]
                break
        
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
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' or obj.type == 'CURVE']
        
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
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
        
        updated_count = 0
        for obj in selected_objects:
            # Cari modifier auto_pop_up yang ada
            modifier = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == node_group:
                    modifier = mod
                    break
            
            if not modifier or int_socket_id not in modifier:
                continue  # Skip object tanpa modifier atau socket tidak tersedia
            
            # === UPDATE NILAI SOCKET LANGSUNG (TANPA HAPUS MODIFIER) ===
            try:
                # Set nilai baru
                modifier[int_socket_id] = animation_type_value
                
                # Force depsgraph update (KRITIS untuk viewport refresh)
                obj.update_tag(refresh={'OBJECT'})
                context.view_layer.update()
                
                updated_count += 1
            except Exception as e:
                self.report({'WARNING'}, f"Failed on {obj.name}: {e}")
                continue
        
        # Dapatkan label type untuk report
        type_label = 'Unknown'
        for item in ANIMZ_properties.popup_type_items:
            if item[0] == animz_props.popup_type:
                type_label = item[1]
                break
        
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
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' or obj.type == 'CURVE']
        
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
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
        
        updated_count = 0
        for obj in selected_objects:
            # Cari modifier auto_pop_up yang ada
            modifier = None
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == node_group:
                    modifier = mod
                    break
            
            if not modifier or int_socket_id not in modifier:
                continue  # Skip object tanpa modifier atau socket tidak tersedia
            
            # === UPDATE NILAI SOCKET LANGSUNG (TANPA HAPUS MODIFIER) ===
            try:
                # Set nilai baru
                modifier[int_socket_id] = animation_type_value
                
                # Force depsgraph update (KRITIS untuk viewport refresh - ini solusi bug Anda!)
                obj.update_tag(refresh={'OBJECT'})
                
                # Force Geometry Nodes re-evaluation (Blender 5.x specific)
                if hasattr(bpy.context, 'view_layer'):
                    bpy.context.view_layer.depsgraph.update()
                
                # Force viewport redraw (untuk immediate visual feedback)
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                
                updated_count += 1
            except Exception as e:
                self.report({'WARNING'}, f"Failed on {obj.name}: {e}")
                continue
        
        # Dapatkan label type untuk report
        type_label = 'Unknown'
        for item in ANIMZ_properties.out_type_items:
            if item[0] == animz_props.out_type:
                type_label = item[1]
                break
        
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
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' or obj.type == 'CURVE']
        
        if not selected_objects:
            self.report({'WARNING'}, "No mesh objects selected")
            return {'CANCELLED'}
        
        total_modifiers_removed = 0
        total_fcurves_cleaned = 0
        objects_processed = 0
        
        # Track apakah node group masih digunakan oleh object lain
        node_group_still_in_use = False
        
        for obj in selected_objects:
            try:
                # === LANGKAH 1: CARI MODIFIER ===
                modifier = None
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and mod.node_group and mod.node_group.name == "auto_pop_up":
                        modifier = mod
                        break
                
                if not modifier:
                    continue
                
                modifier_name = modifier.name
                
                # === LANGKAH 2: HAPUS MODIFIER ===
                obj.modifiers.remove(modifier)
                total_modifiers_removed += 1
                
                # === LANGKAH 3: BERSIHKAN BROKEN KEYFRAMES ===
                fcurves_cleaned = 0
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action
                    if hasattr(action, 'fcurves'):
                        # Iterasi mundur karena menghapus saat iterasi
                        for i in range(len(action.fcurves) - 1, -1, -1):
                            fcurve = action.fcurves[i]
                            # Deteksi broken path dengan path_resolve
                            try:
                                obj.path_resolve(fcurve.data_path)
                            except (KeyError, AttributeError, ValueError):
                                action.fcurves.remove(fcurve)
                                fcurves_cleaned += 1
                            except Exception:
                                # Safety net untuk error tak terduga
                                action.fcurves.remove(fcurve)
                                fcurves_cleaned += 1
                
                total_fcurves_cleaned += fcurves_cleaned
                objects_processed += 1
                
            except Exception as e:
                self.report({'WARNING'}, f"Failed to process {obj.name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        # === LANGKAH 4: PURGE NODE GROUP (JIKA DIPILIH & TIDAK DIGUNAKAN) ===
        node_group_purged = False
        if self.purge_node_group and "auto_pop_up" in bpy.data.node_groups:
            node_group = bpy.data.node_groups["auto_pop_up"]
            
            # Cek apakah masih digunakan oleh object lain di seluruh scene
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.modifiers:
                    for mod in obj.modifiers:
                        if mod.type == 'NODES' and mod.node_group == node_group:
                            node_group_still_in_use = True
                            break
                    if node_group_still_in_use:
                        break
            
            # Hapus hanya jika tidak digunakan
            if not node_group_still_in_use:
                # Pastikan tidak ada fake user
                node_group.use_fake_user = False
                
                # Force removal
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
            report_parts.append(f"Cleaned {total_fcurves_cleaned} broken keyframe(s)")
        
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


# =======================================================
# Panel
# =======================================================

class ANIMZ_PT_panel(Panel):
    """Panel Animz di sidebar"""
    bl_label = "AnimZ™"
    bl_idname = "ANIMZ_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ZeusLab'
    bl_description = "Auto Pop-Up for animator based on geo-node"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_animz_panel
        return True
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        animz_props = scene.animz_properties
        
        layout.label(text="Auto Pop-Up")
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
    
    # Mapping untuk dropdown type animasi (3-tuple: identifier, name, description)
    popup_type_items = [
        ('0', "Ease Out", "0 | 30 Frame"),
        ('1', "Ease In Out", "1 | 30 Frame"),
        ('2', "Bounce", "2 | 30 Frame"),
        ('3', "Jump & Bounce", "3 | 30 Frame"),
        ('4', "Jump, Rotate & Bounce", "4 | 30 Frame"),
        ('5', "Slide ↓ Elastic", "5 | 60-90 Frame, Linear"),
        ('6', "Slide ↑ Ease Out", "6 | 20-45 Frame"),
        ('7', "Slide ↓ Ease Out", "7 | 20-45 Frame"),
        ('8', "Slide → Ease Out", "8 | 20-45 Frame"),
        ('9', "Slide ← Ease Out", "9 | 20-45 Frame"),
        ('10', "Rotate ← & Back", "10 | 30 Frame"),
    ]

    out_type_items = [
        ('0', "Ease In", "0 | 30 Frame"),
        ('1', "Ease In Out","1 | 30 Frame"),
        ('2', "Back", "2 | 30 Frame"),
        ('3', "Jump & Bounce", "3 | 30 Frame"),
        ('4', "Jump, Rotate & Bounce", "4 | 30 Frame"),
        ('5', "X-Axis Scale", "5 | 30 Frame"),
        ('6', "Slide ↑ Ease Out", "6 | 20-45 Frame"),
        ('7', "Slide ↓ Ease Out", "7 | 20-45 Frame"),
        ('8', "Slide → Ease Out", "8 | 20-45 Frame"),
        ('9', "Slide ← Ease Out", "9 | 20-45 Frame"),
        ('10', "Rotate ← & Back", "10 | 30 Frame"),
    ]
    
    popup_type: EnumProperty(
        name="In Type",
        description="Animation behavior for the pop-up effect",
        items=popup_type_items,
        default='0'
    )
    
    out_type: EnumProperty(
        name="Out Type",
        description="Animation behavior for the out effect",
        items=out_type_items,
        default='0'
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

# =======================================================
# Register/Unregister
# =======================================================

classes = (
    ANIMZ_properties,
    ANIMZ_OT_append_node,
    ANIMZ_OT_animate_popup,
    ANIMZ_OT_animate_out_popup,
    ANIMZ_OT_update_in_animation,
    ANIMZ_OT_update_out_animation,
    ANIMZ_OT_delete_animation,
    ANIMZ_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.animz_properties = bpy.props.PointerProperty(type=ANIMZ_properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.animz_properties


    # Notes:
    # 1. Tombol Update masih tolol, (Karena dia menghapus modifier dulu)
    # 2. Tombol Delete masih belum sempurna, karena geo-node masih tersimpan di file blender, harus nya di purge