import bpy
from ..preferences import get_addon_preferences

# ==============================================================================
# PROPERTIES
# ==============================================================================

def register_properties():
    """Register scene properties for the addon"""
    bpy.types.Scene.bake_frame_start = bpy.props.IntProperty(
        name="Start",
        default=1,
        min=0,
        description="Starting frame for action baking",
        options={'ANIMATABLE'}
    )
    
    bpy.types.Scene.bake_frame_end = bpy.props.IntProperty(
        name="End",
        default=250,
        min=1,
        description="Ending frame for action baking",
        options={'ANIMATABLE'}
    )
    
    bpy.types.Scene.skeleton_style_option = bpy.props.EnumProperty(
        name="Skeleton Option",
        description="Pilih style skeleton untuk baking",
        items=[
            ('STYLE_18', "Skeleton 18 ect.", "Gunakan koleksi DEF dan MCH untuk skeleton style 18"),
            ('STYLE_19', "Skeleton 19", "Gunakan koleksi Layer 2 untuk skeleton style 19")
        ],
        default='STYLE_18'
    )

def unregister_properties():
    """Unregister scene properties"""
    del bpy.types.Scene.bake_frame_start
    del bpy.types.Scene.bake_frame_end
    del bpy.types.Scene.skeleton_style_option

# ==============================================================================
# OPERATORS - PREPARING
# ==============================================================================

class OBJECT_OT_duplicate_collection(bpy.types.Operator):
    bl_idname = "object.duplicate_collection"
    bl_label = "Duplicate Collection"
    bl_description = "Menduplikasi koleksi beserta isinya dengan nama 'Baked Animation'\n**Pilih Collection Tertentu**"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Perbaikan: Gunakan context.collection yang masih kompatibel di Blender 5.0
        collection = context.collection
        if not collection:
            self.report({'ERROR'}, "Tidak ada koleksi aktif! Pilih koleksi di Outliner.")
            return {'CANCELLED'}

        # Duplikasi object di koleksi
        bpy.ops.object.select_all(action='DESELECT')
        for obj in collection.objects:
            obj.select_set(True)
            # Pastikan ada object aktif
            if context.view_layer.objects.active is None:
                context.view_layer.objects.active = obj
        
        if not context.selected_objects:
            self.report({'ERROR'}, "Tidak ada object dalam koleksi untuk diduplikasi!")
            return {'CANCELLED'}
        
        bpy.ops.object.duplicate(linked=False)
        
        # Buat koleksi baru dan pindahkan object
        new_collection = bpy.data.collections.new("Baked Animation")
        context.scene.collection.children.link(new_collection)
        
        # Dapatkan objek yang baru diduplikasi (objek terakhir yang dipilih)
        duplicated_objects = context.selected_objects.copy()
        
        for obj in duplicated_objects:
            for old_col in obj.users_collection:
                old_col.objects.unlink(obj)
            new_collection.objects.link(obj)
        
        # Nonaktifkan koleksi asli di view layer
        def find_layer_collection(layer_collection, name):
            if layer_collection.collection.name == name:
                return layer_collection
            for child in layer_collection.children:
                result = find_layer_collection(child, name)
                if result:
                    return result
            return None
        
        layer_collection = find_layer_collection(context.view_layer.layer_collection, collection.name)
        if layer_collection:
            layer_collection.exclude = True
        
        self.report({'INFO'}, "Koleksi berhasil diduplikasi sebagai 'Baked Animation'.")
        return {'FINISHED'}

# Operator Visibility Bone Collection
class OBJECT_OT_set_bone_collection_visibility(bpy.types.Operator):
    bl_idname = "object.set_bone_collection_visibility"
    bl_label = "Set Bone Collection Visibility"
    bl_description = "Mengaktifkan semua bone collection di Blender 5.0\n**Pilih Armature Target**"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.active_object
        
        # Validasi context
        if not armature:
            self.report({'ERROR'}, "Tidak ada object aktif!")
            return {'CANCELLED'}
        
        if armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Object aktif bukan armature!")
            return {'CANCELLED'}
        
        # API Blender 5.0: Sistem bone collection sudah stabil
        # properti is_visible masih berfungsi seperti di Blender 4.x
        for collection in armature.data.collections:
            collection.is_visible = True
        
        self.report({'INFO'}, "Semua bone collection telah diaktifkan.")
        return {'FINISHED'}

# ==============================================================================
# OPERATORS - ACTION BAKING
# ==============================================================================

class OBJECT_OT_bake_action(bpy.types.Operator):
    """Bake action for bones based on skeleton style"""
    bl_idname = "bonver.bake_action"
    bl_label = "Bake Action Skeleton"
    bl_description = "Bake action based on skeleton style\n**Select an Armature first**"
    bl_options = {'REGISTER', 'UNDO'}

    frame_start: bpy.props.IntProperty(
        name="Start Frame",
        default=1,
        min=0,
        description="Starting frame for baking"
    )

    frame_end: bpy.props.IntProperty(
        name="End Frame",
        default=250,
        min=1,
        description="Ending frame for baking"
    )

    def invoke(self, context, event):
        """Initialize properties from scene when invoked"""
        scene = context.scene
        self.frame_start = scene.bake_frame_start
        self.frame_end = scene.bake_frame_end
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        """Custom dialog layout"""
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        col.prop(self, "frame_start")
        col.prop(self, "frame_end")
        
        layout.separator()
        
        # Tampilkan opsi yang dipilih dengan deskripsi jelas
        style_option = context.scene.skeleton_style_option
        if style_option == 'STYLE_18':
            layout.label(text="Skeleton Style 18: DEF & MCH Bone Collections", icon='ARMATURE_DATA')
        elif style_option == 'STYLE_19':
            layout.label(text="Skeleton Style 19: Layer 2 Bone Collections", icon='ARMATURE_DATA')

    def execute(self, context):
        armature = context.active_object
        style_option = context.scene.skeleton_style_option  # Ambil opsi skeleton style
        
        # 1. Pastikan User telah select Armature
        if not armature or armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an armature first!")
            return {'CANCELLED'}
        
        # Simpan mode asli
        original_mode = armature.mode
        
        # Dapatkan daftar nama bones berdasarkan skeleton style
        bone_names_to_select = set()
        collections_found = []
        
        if style_option == 'STYLE_18':
            # Style 18: Cari collections yang mulai dengan "DEF" atau "MCH"
            self.report({'INFO'}, "Using Skeleton Style 18: DEF & MCH collections")
            
            def_collections = []
            mch_collections = []
            
            for collection in armature.data.collections:
                collection_name_lower = collection.name.lower()
                if collection_name_lower.startswith('def'):
                    def_collections.append(collection)
                elif collection_name_lower.startswith('mch'):
                    mch_collections.append(collection)
            
            if not def_collections and not mch_collections:
                self.report({'ERROR'}, "No 'DEF' or 'MCH' collections found in armature!")
                available_collections = [col.name for col in armature.data.collections]
                self.report({'INFO'}, f"Available collections: {', '.join(available_collections)}")
                return {'CANCELLED'}
            
            # Tambahkan bones dari DEF collections
            for collection in def_collections:
                collections_found.append(collection.name)
                collection.is_visible = True
                for bone_ref in collection.bones:
                    bone_names_to_select.add(bone_ref.name)
            
            # Tambahkan bones dari MCH collections  
            for collection in mch_collections:
                collections_found.append(collection.name)
                collection.is_visible = True
                for bone_ref in collection.bones:
                    bone_names_to_select.add(bone_ref.name)
            
            self.report({'INFO'}, f"Found {len(def_collections)} DEF and {len(mch_collections)} MCH collections")
            self.report({'INFO'}, f"Total collections processed: {len(collections_found)}")
                
        elif style_option == 'STYLE_19':
            # Style 19: Cari collection "Layer 2"
            self.report({'INFO'}, "Using Skeleton Style 19: Layer 2 collection")
            
            target_collection = None
            # Cari dengan case-insensitive untuk "Layer 2"
            for collection in armature.data.collections:
                if collection.name.lower() == "layer 2":
                    target_collection = collection
                    if collection.name != "Layer 2":
                        self.report({'INFO'}, f"Found collection with case-insensitive match: '{collection.name}'")
                    break
            
            if not target_collection:
                # Cari alternatif: "Layer2" atau "layer2"
                for collection in armature.data.collections:
                    if collection.name.lower() in ["layer2", "layer 2", "layer-2"]:
                        target_collection = collection
                        self.report({'INFO'}, f"Found alternative match: '{collection.name}'")
                        break
            
            if target_collection:
                collections_found.append(target_collection.name)
                target_collection.is_visible = True
                for bone_ref in target_collection.bones:
                    bone_names_to_select.add(bone_ref.name)
            else:
                self.report({'ERROR'}, "Bone collection 'Layer 2' not found in armature!")
                available_collections = [col.name for col in armature.data.collections]
                self.report({'ERROR'}, f"Available collections: {', '.join(available_collections)}")
                return {'CANCELLED'}
        
        # Validasi bones yang akan dipilih
        if not bone_names_to_select:
            self.report({'ERROR'}, f"No bones found in the selected collection(s): {', '.join(collections_found)}")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Found {len(bone_names_to_select)} bones in collections: {', '.join(collections_found)}")
        self.report({'INFO'}, f"Sample bones: {', '.join(list(bone_names_to_select)[:5])}...")
        
        # BLENDER 5.0 METHOD: Gunakan Edit Mode untuk seleksi yang reliable
        selected_count = 0
        
        try:
            # Ke Edit Mode
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Deselect all
            bpy.ops.armature.select_all(action='DESELECT')
            
            # Seleksi bones berdasarkan nama
            for edit_bone in armature.data.edit_bones:
                if edit_bone.name in bone_names_to_select:
                    edit_bone.select = True
                    edit_bone.select_head = True
                    edit_bone.select_tail = True
                    selected_count += 1
            
            self.report({'INFO'}, f"Edit Mode: Selected {selected_count} bones from {len(collections_found)} collection(s)")
            
            # Validasi di Edit Mode
            if selected_count == 0:
                # Debug: Print semua edit bone names
                all_edit_bones = [eb.name for eb in armature.data.edit_bones]
                self.report({'WARNING'}, f"No matching bones found. Edit bones: {', '.join(all_edit_bones[:10])}...")
                bpy.ops.object.mode_set(mode='OBJECT')
                return {'CANCELLED'}
            
            # Kembali ke Object mode (seleksi akan persist)
            bpy.ops.object.mode_set(mode='OBJECT')
            
        except Exception as e:
            self.report({'ERROR'}, f"Selection in Edit Mode failed: {str(e)}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return {'CANCELLED'}
        
        # Verifikasi seleksi dengan melihat selected_pose_bones
        try:
            bpy.ops.object.mode_set(mode='POSE')
            
            # Hitung bone yang terseleksi di Pose Mode
            selected_in_pose = len(context.selected_pose_bones) if hasattr(context, 'selected_pose_bones') else 0
            
            self.report({'INFO'}, f"Pose Mode: {selected_in_pose} bones selected via context.selected_pose_bones")
            
            if selected_in_pose == 0:
                # Fallback: coba seleksi manual di Pose Mode
                self.report({'WARNING'}, "No bones selected in Pose Mode. Trying direct pose bone selection...")
                
                for pose_bone in armature.pose.bones:
                    if pose_bone.name in bone_names_to_select:
                        try:
                            pose_bone.bone.select = True
                        except AttributeError:
                            try:
                                pose_bone.select = True
                            except AttributeError:
                                pass
                        selected_in_pose += 1
                
                if selected_in_pose == 0:
                    self.report({'ERROR'}, "Failed to select any bones in Pose Mode")
                    bpy.ops.object.mode_set(mode='OBJECT')
                    return {'CANCELLED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Pose Mode verification failed: {str(e)}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return {'CANCELLED'}
        
        # Bake action
        try:
            bpy.ops.nla.bake(
                frame_start=self.frame_start,
                frame_end=self.frame_end,
                step=1,
                only_selected=True,
                visual_keying=True,
                clear_constraints=True,
                clear_parents=False,
                use_current_action=True,
                bake_types={'POSE'}
            )
            
            # Update scene properties
            context.scene.bake_frame_start = self.frame_start
            context.scene.bake_frame_end = self.frame_end
            
            # Opsional: Hapus bones yang tidak dibake (sesuaikan sesuai kebutuhan)
            bpy.ops.pose.select_all(action='INVERT')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.delete()
            bpy.ops.object.mode_set(mode='OBJECT')
            
            style_desc = "Style 18 (DEF & MCH)" if style_option == 'STYLE_18' else "Style 19 (Layer 2)"
            self.report({'INFO'}, f"✅ Successfully baked action from frame {self.frame_start} to {self.frame_end} for {selected_count} bones using {style_desc}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Baking failed: {str(e)}")
            
            # Kembalikan ke mode asli
            try:
                if original_mode == 'EDIT':
                    bpy.ops.object.mode_set(mode='EDIT')
                elif original_mode == 'POSE':
                    bpy.ops.object.mode_set(mode='POSE')
                else:
                    bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
                
            return {'CANCELLED'}

# ==============================================================================
# OPERATORS - COMBINED OPERATIONS
# ==============================================================================

class OBJECT_OT_complete_workflow(bpy.types.Operator):
    """Bake action and clean up bones in one operation"""
    bl_idname = "bonver.complete_workflow"
    bl_label = "Run All"
    bl_description = "Running All Directly"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # First bake action
        bake_result = bpy.ops.bonver.bake_action_19(
            frame_start=context.scene.bake_frame_start,
            frame_end=context.scene.bake_frame_end
        )
        
        if 'CANCELLED' in bake_result:
            self.report({'ERROR'}, "Baking action failed, cleanup aborted")
            return {'CANCELLED'}
        
        # Then clean up bones
        cleanup_result = bpy.ops.bonver.cleanup_bones()
        
        if 'CANCELLED' in cleanup_result:
            self.report({'WARNING'}, "Baking succeeded but cleanup failed")
            return {'FINISHED'}
        
        self.report({'INFO'}, "Successfully completed bake and cleanup operations")
        return {'FINISHED'}

class OBJECT_OT_prepare_bake(bpy.types.Operator):
    """Complete workflow: duplicate collection, enable bones, bake & cleanup"""
    bl_idname = "bonver.prepare_bake"
    bl_label = "Prepare Bake"
    bl_description = "Full workflow: duplicate collection, enable bones, bake action, and clean up"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Simpan referensi ke object aktif sebelum operasi
        original_active = context.active_object
        original_collection = context.collection
        
        # ===== OPERASI 1: DUPLICATE COLLECTION =====
        self.report({'INFO'}, "🔄 Starting: Duplicate Collection")
        
        # Gunakan bl_idname yang benar: "object.duplicate_collection"
        duplicate_result = bpy.ops.object.duplicate_collection()
        
        if 'CANCELLED' in duplicate_result:
            self.report({'ERROR'}, "❌ Duplicate Collection failed. Workflow aborted.")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "✅ Duplicate Collection completed successfully")
        
        # ===== OPERASI 2: CARI ARMATURE DI KOLEKSI BARU =====
        new_collection = bpy.data.collections.get("Baked Animation")
        if not new_collection:
            self.report({'ERROR'}, "❌ 'Baked Animation' collection not found after duplication!")
            return {'CANCELLED'}
        
        # Temukan armature di koleksi baru
        new_armature = None
        for obj in new_collection.objects:
            if obj.type == 'ARMATURE':
                new_armature = obj
                break
        
        if not new_armature:
            self.report({'ERROR'}, f"❌ No armature found in 'Baked Animation' collection!\nObjects found: {[obj.name for obj in new_collection.objects]}")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"🎯 Found armature: '{new_armature.name}' in duplicated collection")
        
        # ===== OPERASI 3: SET ARMATURE BARU SEBAGAI AKTIF =====
        context.view_layer.objects.active = new_armature
        bpy.ops.object.select_all(action='DESELECT')
        new_armature.select_set(True)
        
        # ===== OPERASI 4: ENABLE BONE COLLECTION VISIBILITY =====
        self.report({'INFO'}, "🔄 Starting: Enable Bone Collections")
        
        # Gunakan bl_idname yang benar: "object.set_bone_collection_visibility"
        visibility_result = bpy.ops.object.set_bone_collection_visibility()
        
        if 'CANCELLED' in visibility_result:
            self.report({'ERROR'}, "❌ Enable Bone Collections failed!")
            
            # Optional: rollback - aktifkan kembali koleksi asli
            if original_collection:
                def find_layer_collection(layer_collection, name):
                    if layer_collection.collection.name == name:
                        return layer_collection
                    for child in layer_collection.children:
                        result = find_layer_collection(child, name)
                        if result:
                            return result
                    return None
                
                layer_collection = find_layer_collection(context.view_layer.layer_collection, original_collection.name)
                if layer_collection:
                    layer_collection.exclude = False
            
            return {'CANCELLED'}
        
        
        self.report({'INFO'}, "✅ Enable Bone Collections completed successfully")
        self.report({'INFO'}, "✨ Workflow completed: Collection duplicated and bone collections enabled!")
        
        return {'FINISHED'}

# ==============================================================================
# UI PANELS
# ==============================================================================

class BONVER_PT_main_panel(bpy.types.Panel):
    """Main panel for BonVer addon"""
    bl_label = ""
    bl_idname = "BONVER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZeusLab"
    bl_options = {'DEFAULT_CLOSED'}
    bl_description = "Convert custom mixamo RIG to Bones"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_bonver_panel
        return True

    def draw_header(self, context):
        layout = self.layout
        layout.label(text='Mixamo Rig to Bones')

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.operator("bonver.prepare_bake", text="Prepare Bake")
#        col.operator("object.duplicate_collection", text="Duplicate Collection", icon='DUPLICATE')
#        col.operator("object.set_bone_collection_visibility", text="Enable All Bone Collections", icon='HIDE_OFF')
        
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scene, "bake_frame_start")
        row.prop(scene, "bake_frame_end")
        
        col.scale_y=1.0
        col.prop(scene, "skeleton_style_option", text="")
        row = layout.row()
        row.scale_y=1.5
        row.operator("bonver.bake_action", text="Bake Action")
        
        # Complete Workflow (RAWAN ERROR NJINGG!! AOWKOAK)
#        box2 = layout.box()
#        box2.label(text="Complete Workflow", icon='SEQUENCE')
#        box2.operator("bonver.complete_workflow", text="Run Full Workflow", icon='PLAY')

# ==============================================================================
# REGISTRATION
# ==============================================================================

classes = (
    OBJECT_OT_duplicate_collection,
    OBJECT_OT_set_bone_collection_visibility,
    OBJECT_OT_bake_action,
#    OBJECT_OT_complete_workflow,
    OBJECT_OT_prepare_bake,
    BONVER_PT_main_panel,
)

def register():
    """Register all classes and properties"""
    # Register properties first
    register_properties()
    
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    print("BonVer addon registered successfully")

def unregister():
    """Unregister all classes and properties"""
    # Unregister classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Unregister properties
    unregister_properties()
    
    print("BonVer addon unregistered successfully")
