import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    PointerProperty,
    StringProperty,
    EnumProperty,
    BoolProperty,
    IntProperty,
)

import os
import sys
import zipfile
import urllib.request
import tempfile
from ..preferences import get_addon_preferences

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def childof_enum_items(self, context):
    items = [("__NEW__", "New (+)", "Create a new Child Of layer")]
    obj = context.object
    if not obj:
        return items
    for c in obj.constraints:
        if c.type == 'CHILD_OF':
            items.append((c.name, c.name, f"Child Of targeting {getattr(c.target, 'name', None)}::{c.subtarget}"))
    return items


def bone_enum_items(self, context):
    arm = self.armature
    items = []
    if arm and arm.type == 'ARMATURE' and arm.pose:
        for pb in arm.pose.bones:
            items.append((pb.name, pb.name, ""))
    return items


def ensure_unique_constraint_name(obj, base):
    name = base
    i = 1
    existing = {c.name for c in obj.constraints}
    while name in existing:
        i += 1
        name = f"{base}.{i:03d}"
    return name


def get_childof_constraint(obj, name):
    if not obj:
        return None
    for c in obj.constraints:
        if c.type == 'CHILD_OF' and c.name == name:
            return c
    return None


def set_constraint_active(context, obj, con):
    # Make obj active and con active for operators that need it
    view_layer = context.view_layer
    view_layer.objects.active = obj
    for c in obj.constraints:
        c.mute = c.mute  # noop to ensure RNA sync
    obj.constraints.active = con


def keyframe_influence(con, value, frame=None):
    if frame is None:
        frame = bpy.context.scene.frame_current
    con.influence = value
    con.keyframe_insert(data_path="influence", frame=frame)


def get_childof_constraints(obj):
    """Helper untuk mendapatkan semua Child Of constraints dari object"""
    if not obj:
        return []
    return [c for c in obj.constraints if c.type == 'CHILD_OF']


# -----------------------------------------------------------------------------
# Properties
# -----------------------------------------------------------------------------

class ATTACH_PG_Settings(PropertyGroup):
    """
    Settings utama - menggunakan active_layer_index untuk UIList
    """
    
    # Callback untuk update armature & bone saat index berubah
    def update_active_index(self, context):
        obj = context.object
        if not obj:
            return

        con = self.get_active_constraint(obj)
        if con and con.type == 'CHILD_OF':
            # Update armature jika target adalah armature
            if con.target and con.target.type == 'ARMATURE':
                self.armature = con.target
            else:
                self.armature = None

            # Update bone dari subtarget
            self.bone = con.subtarget or ""
        else:
            self.armature = None
            self.bone = ""
    
    # Index untuk UIList selection
    active_layer_index: IntProperty(
        name="Active Constraint Index",
        description="Index of currently selected Child Of constraint",
        default=0,
        min=0,
        update=update_active_index  # <--- tambahkan update callback
    )
    
    # Properties untuk armature dan bone selection
    armature: PointerProperty(
        name="Armature",
        description="Armature object that contains the target bone",
        type=bpy.types.Object,
    )
    bone: StringProperty(
        name="Bone",
        description="Select bone name"
    )
    
    # Options untuk behavior
    maintain_offset: BoolProperty(
        name="Keep Offset",
        description="Keep current world transform on attach",
        default=True,
    )
    new_constraint: BoolProperty(
        name="Edit Selected",
        description="Add new child of constraint",
        default=False,
    )
    auto_name_from_bone: BoolProperty(
        name="Auto-name from Bone",
        description="If creating a new layer, name it after the bone",
        default=True,
    )
    new_layer_name: StringProperty(
        name="New Layer Name",
        description="Name for a new Child Of layer when creating",
        default="ChildOf",
    )

    def get_active_constraint(self, obj):
        """
        Helper method untuk mendapatkan constraint yang sedang active
        berdasarkan index yang dipilih di UIList
        """
        if not obj:
            return None
            
        childof_constraints = get_childof_constraints(obj)
        
        if 0 <= self.active_layer_index < len(childof_constraints):
            return childof_constraints[self.active_layer_index]
        
        return None
    
    def get_active_constraint_name(self, obj):
        """Helper untuk mendapatkan nama constraint yang aktif"""
        con = self.get_active_constraint(obj)
        return con.name if con else "__NEW__"


# -----------------------------------------------------------------------------
# UI List
# -----------------------------------------------------------------------------

class ATTACH_UL_constraint_list(bpy.types.UIList):
    """
    Custom UIList untuk menampilkan Child Of constraints dalam format list
    yang mirip dengan Material List atau Modifier List di Blender
    """
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        """
        Method ini dipanggil untuk setiap item dalam list
        
        Parameters yang penting:
        - layout: UI layout untuk menggambar item
        - item: constraint object yang sedang digambar
        - icon: icon yang akan ditampilkan
        - active_data, active_propname: untuk menentukan item mana yang selected
        """
        
        # Pastikan item adalah constraint Child Of
        if item.type == 'CHILD_OF':
            # Buat layout horizontal sederhana untuk nama constraint saja
            row = layout.row(align=True)
            
            # Icon berdasarkan status influence untuk visual feedback
            if item.influence >= 1.0:
                # Constraint fully active - gunakan icon yang menunjukkan attachment
                icon_status = 'LINKED'
            elif item.influence > 0.0:
                # Constraint partially active - gunakan icon yang menunjukkan partial
                icon_status = 'DRIVER'  
            else:
                # Constraint inactive - gunakan icon yang menunjukkan unlinked
                icon_status = 'UNLINKED'
            
            # Tampilkan icon status dengan mute toggle
            row.prop(item, "mute", text="", icon=icon_status if not item.mute else 'HIDE_ON', emboss=False)
            
            # Nama constraint - bisa di-edit langsung
            row.prop(item, "name", text="", emboss=False)
        else:
            # Fallback untuk constraint jenis lain (seharusnya tidak terjadi)
            layout.label(text=item.name, icon='CONSTRAINT')


# -----------------------------------------------------------------------------
# Operators untuk UIList
# -----------------------------------------------------------------------------

class ATTACH_OT_constraint_list_add(bpy.types.Operator):
    """Operator untuk menambah constraint baru dari UIList"""
    bl_idname = "attach.constraint_list_add"
    bl_label = "Add Child Of Constraint"
    bl_description = "Add new Child Of constraint"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}

        settings = context.scene.attach_settings
        
        # Buat constraint baru
        base_name = "ChildOf"
        if settings.auto_name_from_bone and settings.bone:
            base_name = settings.bone
        elif settings.new_layer_name:
            base_name = settings.new_layer_name
            
        con_name = ensure_unique_constraint_name(obj, base_name)
        con = obj.constraints.new('CHILD_OF')
        con.name = con_name
        
        # Update active index ke constraint yang baru dibuat
        childof_constraints = get_childof_constraints(obj)
        settings.active_layer_index = len(childof_constraints) - 1
        
        self.report({'INFO'}, f"Added new Child Of constraint: {con_name}")
        return {'FINISHED'}


class ATTACH_OT_constraint_list_remove(bpy.types.Operator):
    """Operator untuk menghapus constraint dari UIList"""
    bl_idname = "attach.constraint_list_remove"
    bl_label = "Remove Child Of Constraint"
    bl_description = "Remove selected Child Of constraint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj:
            return False
        settings = context.scene.attach_settings
        return settings.get_active_constraint(obj) is not None

    def execute(self, context):
        obj = context.object
        settings = context.scene.attach_settings
        
        # Dapatkan constraint yang akan dihapus
        con = settings.get_active_constraint(obj)
        if not con:
            self.report({'ERROR'}, "No constraint selected")
            return {'CANCELLED'}
        
        con_name = con.name
        
        # Hapus constraint
        obj.constraints.remove(con)
        
        # Adjust active index setelah penghapusan
        childof_constraints = get_childof_constraints(obj)
        if childof_constraints:
            # Pastikan index masih dalam range
            settings.active_layer_index = min(settings.active_layer_index, len(childof_constraints) - 1)
        else:
            settings.active_layer_index = 0
        
        self.report({'INFO'}, f"Removed Child Of constraint: {con_name}")
        return {'FINISHED'}


class ATTACH_OT_constraint_list_move(bpy.types.Operator):
    """Operator untuk memindah urutan constraint di UIList"""
    bl_idname = "attach.constraint_list_move"
    bl_label = "Move Child Of Constraint"
    bl_description = "Move constraint up or down in the list"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[
            ('UP', 'Up', 'Move constraint up'),
            ('DOWN', 'Down', 'Move constraint down'),
        ]
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if not obj:
            return False
        return len(get_childof_constraints(obj)) > 1

    def execute(self, context):
        obj = context.object
        settings = context.scene.attach_settings
        
        childof_constraints = get_childof_constraints(obj)
        current_index = settings.active_layer_index
        
        if self.direction == 'UP' and current_index > 0:
            new_index = current_index - 1
        elif self.direction == 'DOWN' and current_index < len(childof_constraints) - 1:
            new_index = current_index + 1
        else:
            return {'CANCELLED'}
        
        # Pindah constraint dalam daftar Blender
        current_con = childof_constraints[current_index]
        target_con = childof_constraints[new_index]
        
        # Blender tidak memiliki move constraint built-in, jadi kita simulasi dengan mengubah urutan
        # Ini agak tricky, tapi bisa dilakukan dengan remove dan add kembali
        
        # Untuk saat ini, hanya update index
        settings.active_layer_index = new_index
        
        self.report({'INFO'}, f"Moved constraint {self.direction.lower()}")
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Operators Utama
# -----------------------------------------------------------------------------

class ATTACH_OT_pick_bone(bpy.types.Operator):
    bl_idname = "attach.pick_bone"
    bl_label = "Pick Bone"

    def invoke(self, context, event):
        return context.window_manager.invoke_search_popup(self)

    def execute(self, context):
        return {'FINISHED'}


class ATTACH_OT_new_attach(Operator):
    bl_idname = "attach.new"
    bl_label = ""
    bl_description = "Create Child Of to target the selected armature bone; keyframe influence = 1"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        obj = context.object
        prefs = context.scene.attach_settings
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}

        if not prefs.armature or prefs.armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Armature not set or not an armature.")
            return {'CANCELLED'}
        if not prefs.bone:
            self.report({'ERROR'}, "No bone selected.")
            return {'CANCELLED'}
        
        base_name = prefs.bone if prefs.auto_name_from_bone and prefs.bone else prefs.new_layer_name or "ChildOf"
        con_name = ensure_unique_constraint_name(obj, base_name)
        con = obj.constraints.new('CHILD_OF')
        con.name = con_name
        
        
        # Set target and options
        con.target = prefs.armature
        con.subtarget = prefs.bone
        con.use_location_x = True
        con.use_location_y = True
        con.use_location_z = True
        con.use_rotation_x = True
        con.use_rotation_y = True
        con.use_rotation_z = True
        con.use_scale_x = True
        con.use_scale_y = True
        con.use_scale_z = True

        # Maintain offset + set inverse so object doesn't snap
        try:
            set_constraint_active(context, obj, con)
            if prefs.maintain_offset:
                bpy.ops.constraint.childof_set_inverse(constraint=con.name, owner='OBJECT')
            else:
                bpy.ops.constraint.childof_clear_inverse(constraint=con.name, owner='OBJECT')
        except Exception as e:
            self.report({'WARNING'}, f"Set/Clear Inverse op failed: {e}")

        # Keyframe setup
        original_frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_current = original_frame - 1

        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler") 
        obj.keyframe_insert(data_path="scale")
        keyframe_influence(con, 0.0)

        bpy.context.scene.frame_current = original_frame
        
        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="scale")
        
        keyframe_influence(con, 1.0)
        
        # Update active index ke constraint baru
        childof_constraints = get_childof_constraints(obj)
        prefs.active_layer_index = len(childof_constraints) - 1
        
        self.report({'INFO'}, f"Attached via layer '{con.name}' â†’ {prefs.armature.name}:{prefs.bone}")
        return {'FINISHED'}


class ATTACH_OT_create_or_update(Operator):
    bl_idname = "attach.childof_attach"
    bl_label = "Attach"
    bl_description = "Create or update the active Child Of layer to target the selected armature bone; keyframe influence = 1"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}

        prefs = context.scene.attach_settings

        if not prefs.armature or prefs.armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Armature not set or not an armature.")
            return {'CANCELLED'}
        if not prefs.bone:
            self.report({'ERROR'}, "No bone selected.")
            return {'CANCELLED'}            

        # Dapatkan constraint yang aktif atau buat baru
        con = prefs.get_active_constraint(obj)
        if not con:
            # Buat constraint baru jika tidak ada yang aktif
            base_name = prefs.bone if prefs.auto_name_from_bone and prefs.bone else prefs.new_layer_name or "ChildOf"
            con_name = ensure_unique_constraint_name(obj, base_name)
            con = obj.constraints.new('CHILD_OF')
            con.name = con_name
            

        # Set target and options
        con.target = prefs.armature
        con.subtarget = prefs.bone
        con.use_location_x = True
        con.use_location_y = True
        con.use_location_z = True
        con.use_rotation_x = True
        con.use_rotation_y = True
        con.use_rotation_z = True
        con.use_scale_x = True
        con.use_scale_y = True
        con.use_scale_z = True

        # Maintain offset + set inverse so object doesn't snap
        try:
            set_constraint_active(context, obj, con)
            if prefs.maintain_offset:
                bpy.ops.constraint.childof_set_inverse(constraint=con.name, owner='OBJECT')
            else:
                bpy.ops.constraint.childof_clear_inverse(constraint=con.name, owner='OBJECT')
        except Exception as e:
            self.report({'WARNING'}, f"Set/Clear Inverse op failed: {e}")

        # Keyframe setup
        original_frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_current = original_frame - 1

        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler") 
        obj.keyframe_insert(data_path="scale")
        keyframe_influence(con, 0.0)

        bpy.context.scene.frame_current = original_frame

        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="scale")
        
        keyframe_influence(con, 1.0)
        
        # Update active index
        childof_constraints = get_childof_constraints(obj)
        prefs.active_layer_index = len(childof_constraints) - 1
        
        self.report({'INFO'}, f"Attached via layer '{con.name}' â†’ {prefs.armature.name}:{prefs.bone}")
        return {'FINISHED'}


class ATTACH_OT_detach(Operator):
    bl_idname = "attach.childof_detach"
    bl_label = "Detach"
    bl_description = "Keyframe the active Child Of layer influence = 0"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.object
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}
        prefs = context.scene.attach_settings

        con = prefs.get_active_constraint(obj)
        if not con:
            self.report({'ERROR'}, "No constraint selected to detach.")
            return {'CANCELLED'}
        
        # Keyframe setup
        original_frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_current = original_frame - 1

        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler") 
        obj.keyframe_insert(data_path="scale")
        keyframe_influence(con, 1.0)

        bpy.context.scene.frame_current = original_frame
        
        bpy.ops.object.visual_transform_apply()
        bpy.ops.anim.keyframe_insert()
        
        keyframe_influence(con, 0.0)
        self.report({'INFO'}, f"Detached layer '{con.name}' (influence 0)")
        return {'FINISHED'}


class ATTACH_OT_keyAttach(Operator):
    bl_idname = "attach.childof_key_attach"
    bl_label = ""
    bl_description = "Add Keyframe, influence: 1.0"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}
        
        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="scale")
        
        prefs = context.scene.attach_settings
        con = prefs.get_active_constraint(obj)
        if not con:
            self.report({'ERROR'}, "No constraint selected.")
            return {'CANCELLED'}
        
        keyframe_influence(con, 1.0)
        self.report({'INFO'}, "Key Created")
        return {'FINISHED'}
    

class ATTACH_OT_keyDetach(Operator):
    bl_idname = "attach.childof_key_detach"  # Fixed typo
    bl_label = ""
    bl_description = "Add Keyframe, influence: 0.0"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object.")
            return {'CANCELLED'}
        
        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="scale")
        
        prefs = context.scene.attach_settings
        con = prefs.get_active_constraint(obj)
        if not con:
            self.report({'ERROR'}, "No constraint selected.")
            return {'CANCELLED'}
        
        keyframe_influence(con, 0.0)
        self.report({'INFO'}, "Key Created")
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Updater
# -----------------------------------------------------------------------------

class ATTACH_OT_update_addon(bpy.types.Operator):
    """Update SimplyTake Addon from Google Drive"""
    bl_idname = "attach.update_addon"
    bl_label = "Update SimplyTake Addon"
    bl_options = {'REGISTER', 'INTERNAL'}

    repo_url: bpy.props.StringProperty(
        name="Repo URL",
        default="https://drive.google.com/uc?export=download&id=1DtODvdFvO_HEjxjHgdkBMrFa5BinThz-",  
    )

    def execute(self, context):
        import shutil

        try:
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "addon_update.zip")
            urllib.request.urlretrieve(self.repo_url, zip_path)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)

            # Cari folder atau file .py di dalam zip
            extracted_root = None
            for item in os.listdir(temp_dir):
                full_path = os.path.join(temp_dir, item)
                if os.path.isdir(full_path):
                    extracted_root = full_path
                    break
                elif item.lower().endswith(".py"):
                    addon_name = "SimplyTake"
                    folder_path = os.path.join(temp_dir, addon_name)
                    os.makedirs(folder_path, exist_ok=True)
                    shutil.move(full_path, os.path.join(folder_path, item))
                    extracted_root = folder_path
                    break

            if not extracted_root:
                self.report({'ERROR'}, "Zip tidak berisi folder atau file .py")
                return {'CANCELLED'}

            addon_name = "SimplyTake"
            addon_path = os.path.join(
                bpy.utils.user_resource('SCRIPTS'), "addons", addon_name
            )

            # Buat backup lama dulu biar aman
            backup_path = addon_path + "_backup"
            if os.path.exists(addon_path):
                if os.path.exists(backup_path):
                    shutil.rmtree(backup_path)
                shutil.move(addon_path, backup_path)

            # Copy addon baru
            shutil.copytree(extracted_root, addon_path)

            # ⚠️ Jangan reload otomatis (bisa bikin crash)
            self.report({'INFO'}, f"Addon {addon_name} berhasil diupdate. Restart Blender untuk apply.")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Gagal update: {e}")
            return {'CANCELLED'}


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

class ATTACH_PT_panel(Panel):
    bl_label = ""
    bl_idname = "ATTACH_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ZeusLab'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        if context.object is None:
            return False
            
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_attach_panel
        return True
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(text='Simple Take')

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.attach_settings
        obj = context.object

        # Object info
        row = layout.row()
        row.enabled = False
        row.alignment = 'LEFT'
        row.label(text=f"Active Object: {obj.name}")
        
        boxin = layout.box()
        # Armature dan bone selection
        boxin.prop(prefs, "armature", text="Target")
        
        row = boxin.row(align=True)
        if prefs.armature and prefs.armature.type == 'ARMATURE':
            row.prop_search(prefs, "bone", prefs.armature.data, "bones")
        else:
            row.prop(prefs, "bone", text="Bone")
            row.enabled = False
        
        # Options
        row = boxin.row()
        row.prop(prefs, "maintain_offset")
        row.prop(prefs, "new_constraint")
        
        # UIList untuk Child Of constraints
        layout.label(text="Constraints Layers:")
        
        # Dapatkan semua Child Of constraints untuk UIList
        childof_constraints = get_childof_constraints(obj)
        
        # UIList dengan tombol add/remove
        row = layout.row()
        row.template_list(
            "ATTACH_UL_constraint_list",  # UIList class name
            "",  # list id
            obj,  # data containing the collection
            "constraints",  # property name of the collection
            prefs,  # data containing the active index
            "active_layer_index",  # property name of the active index
            rows=4,  # number of rows to display
        )
        
        # Tombol add/remove di samping UIList
        col = row.column(align=True)
#        col.operator("attach.constraint_list_add", text="", icon='ADD')
        col.operator("attach.constraint_list_remove", text="", icon='TRASH')
        col.separator()
        col.operator("attach.childof_key_attach", text="", icon='KEYFRAME_HLT')
        col.operator("attach.childof_key_detach", text="", icon='KEYFRAME')

        
        # Main action buttons
        row = layout.row(align=True)
        row.scale_y = 1.5
        split = row.split(factor=0.5, align=True)
        
        col1 = split.column(align=True)
        col2 = split.column(align=True)
        # Cek status attachment dari constraint yang aktif
        is_attached = False
        active_con = prefs.get_active_constraint(obj)
        if active_con and active_con.influence >= 1.0:
            is_attached = True
        
        # Logikane tombol "Take"        
        if prefs.new_constraint:
            if is_attached:
                col1.active = False
                col1.operator(ATTACH_OT_create_or_update.bl_idname, text='Linked', icon='LINKED',)
            else:       
                col1.operator(ATTACH_OT_create_or_update.bl_idname, text='Take', icon='LINKED')   
        else:
            if is_attached:
                col1.active = False
                col1.operator(ATTACH_OT_new_attach.bl_idname, text='Linked', icon='LINKED',)
            else:
                col1.operator(ATTACH_OT_new_attach.bl_idname, text='Take', icon='LINKED')
        
        #Logikane tombol Put
        if is_attached:
            col2.operator(ATTACH_OT_detach.bl_idname, text='Put', icon='UNLINKED',)
        else:
            col2.active = False
            col2.operator(ATTACH_OT_detach.bl_idname, text='Unlinked', icon='UNLINKED',)        

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    ATTACH_PG_Settings,
    ATTACH_UL_constraint_list,
    ATTACH_OT_constraint_list_add,
    ATTACH_OT_constraint_list_remove,
    ATTACH_OT_constraint_list_move,
    ATTACH_OT_pick_bone,
    ATTACH_OT_new_attach,
    ATTACH_OT_create_or_update,
    ATTACH_OT_detach,
    ATTACH_OT_keyAttach,
    ATTACH_OT_keyDetach,
    ATTACH_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.attach_settings = PointerProperty(type=ATTACH_PG_Settings)


def unregister():
    del bpy.types.Scene.attach_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)