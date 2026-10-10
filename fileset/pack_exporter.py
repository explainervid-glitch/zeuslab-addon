import bpy
import os

class Pack_Set_Profile(bpy.types.Operator):
    bl_idname = "pack.profile"
    bl_label = "" #Set Resolution
    bl_description = "Set Profile untuk Pack"

    def execute(self, context):
        scene = bpy.context.scene
#        scene.render.fps = 60
        scene.render.engine = 'CYCLES'
        bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'OPTIX'
        scene.cycles.device = 'GPU'
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.5
        scene.cycles.samples = 100
        scene.render.use_persistent_data = True

        scene.render.resolution_x = 320
        scene.render.resolution_y = 430
        scene.render.resolution_percentage = 100
        scene.render.image_settings.media_type = 'VIDEO'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'

        # Buat collection "COPY THIS FOLDER"
        col1_name = "COPY THIS FOLDER"
        if col1_name not in bpy.data.collections:
            col1 = bpy.data.collections.new(col1_name)
            bpy.context.scene.collection.children.link(col1)
            col1.color_tag = 'COLOR_04'  # Hijau
        else:
            col1 = bpy.data.collections[col1_name]

        # Buat collection "DONT COPY THIS FOLDER"
        col2_name = "DONT COPY THIS FOLDER"
        if col2_name not in bpy.data.collections:
            col2 = bpy.data.collections.new(col2_name)
            bpy.context.scene.collection.children.link(col2)
        self.report({'INFO'}, "Pack Render Applied")
        return {'FINISHED'}
    
class Render_animPack(bpy.types.Operator):
    bl_idname = "render.animpack"
    bl_label = ""
    bl_description = "Render Pack"

    def execute(self, context):
        scene = context.scene

        # Dapatkan nama file blend saat ini tanpa path dan ekstensi
        blend_file_path = bpy.data.filepath
        if blend_file_path:
            blend_file_name = os.path.splitext(os.path.basename(blend_file_path))[0]
            blend_dir = os.path.dirname(blend_file_path)
        else:
            blend_file_name = "split_screen_final"
            blend_dir = bpy.path.abspath("//")
            self.report({'WARNING'}, "File belum disimpan, menggunakan nama default untuk output")

        # Atur path dan filename output
        final_output = os.path.join(blend_dir, f"{blend_file_name}.mp4")

        # Atur properti render output
        scene.render.filepath = final_output
        scene.render.use_file_extension = True

        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

        self.report({'INFO'}, "Ready To Render")
        return {'FINISHED'}
    
class Append_Pack_Coll18(bpy.types.Operator):
    bl_idname = "append.pack_coll18"
    bl_label = "18"
    bl_description = "Append Pack Style 18"
    
    def execute(self, context):
        # Dapatkan path addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file blend yang berisi collection CAM
        template_file = os.path.join(addon_path, "template", "pack_style18.blend")
        
        # Cek apakah file template ada
        if not os.path.exists(template_file):
            self.report({'ERROR'}, f"File template tidak ditemukan: {template_file}")
            return {'CANCELLED'}
        
        # Cek apakah collection CAM sudah ada di file
        collection_name = "Cam & Light"
        if collection_name in bpy.data.collections:
            self.report({'INFO'}, f"Collection {collection_name} sudah ada dalam file")
            return {'FINISHED'}
        
        # Lakukan proses append collection
        try:
            # Tentukan inner path dan name
            inner_path = "Collection"
            
            # Append collection dari file template
            bpy.ops.wm.append(
                filepath=os.path.join(template_file, inner_path, collection_name),
                directory=os.path.join(template_file, inner_path),
                filename=collection_name
            )
            
            # Link collection ke scene jika belum ada (langsung pada Scene Collection, sejajar)
            if collection_name in bpy.data.collections:
                # Pastikan collection belum ada di Scene Collection
                if collection_name not in [c.name for c in bpy.context.scene.collection.children]:
                    # Link collection ke scene collection (root)
                    bpy.context.scene.collection.children.link(bpy.data.collections[collection_name])
                    self.report({'INFO'}, f"Collection {collection_name} berhasil di-append ke Scene Collection")
                else:
                    self.report({'INFO'}, f"Collection {collection_name} sudah ada di Scene Collection")
            else:
                self.report({'WARNING'}, f"Collection {collection_name} tidak ditemukan setelah append")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error saat append collection: {str(e)}")
            return {'CANCELLED'}
        
class Append_Pack_Coll18B(bpy.types.Operator):
    bl_idname = "append.pack_coll18b"
    bl_label = "18B"
    bl_description = "Append Pack Style 18, 20, 21 & 22"
    
    def execute(self, context):
        # Dapatkan path addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file blend yang berisi collection CAM
        template_file = os.path.join(addon_path, "template", "pack_style.blend")
        
        # Cek apakah file template ada
        if not os.path.exists(template_file):
            self.report({'ERROR'}, f"File template tidak ditemukan: {template_file}")
            return {'CANCELLED'}
        
        # Cek apakah collection CAM sudah ada di file
        collection_name = "Cam & Light"
        if collection_name in bpy.data.collections:
            self.report({'INFO'}, f"Collection {collection_name} sudah ada dalam file")
            return {'FINISHED'}
        
        # Lakukan proses append collection
        try:
            # Tentukan inner path dan name
            inner_path = "Collection"
            
            # Append collection dari file template
            bpy.ops.wm.append(
                filepath=os.path.join(template_file, inner_path, collection_name),
                directory=os.path.join(template_file, inner_path),
                filename=collection_name
            )
            
            # Link collection ke scene jika belum ada (langsung pada Scene Collection, sejajar)
            if collection_name in bpy.data.collections:
                # Pastikan collection belum ada di Scene Collection
                if collection_name not in [c.name for c in bpy.context.scene.collection.children]:
                    # Link collection ke scene collection (root)
                    bpy.context.scene.collection.children.link(bpy.data.collections[collection_name])
                    self.report({'INFO'}, f"Collection {collection_name} berhasil di-append ke Scene Collection")
                else:
                    self.report({'INFO'}, f"Collection {collection_name} sudah ada di Scene Collection")
            else:
                self.report({'WARNING'}, f"Collection {collection_name} tidak ditemukan setelah append")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error saat append collection: {str(e)}")
            return {'CANCELLED'}

class Append_Pack_Coll19(bpy.types.Operator):
    bl_idname = "append.pack_coll19"
    bl_label = "19"
    bl_description = "Append Pack Style 19"
    
    def execute(self, context):
        # Dapatkan path addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file blend yang berisi collection CAM
        template_file = os.path.join(addon_path, "template", "pack_style19.blend")
        
        # Cek apakah file template ada
        if not os.path.exists(template_file):
            self.report({'ERROR'}, f"File template tidak ditemukan: {template_file}")
            return {'CANCELLED'}
        
        # Cek apakah collection CAM sudah ada di file
        collection_name = "Cam & Light"
        if collection_name in bpy.data.collections:
            self.report({'INFO'}, f"Collection {collection_name} sudah ada dalam file")
            return {'FINISHED'}
        
        # Lakukan proses append collection
        try:
            # Tentukan inner path dan name
            inner_path = "Collection"
            
            # Append collection dari file template
            bpy.ops.wm.append(
                filepath=os.path.join(template_file, inner_path, collection_name),
                directory=os.path.join(template_file, inner_path),
                filename=collection_name
            )
            
            # Link collection ke scene jika belum ada (langsung pada Scene Collection, sejajar)
            if collection_name in bpy.data.collections:
                # Pastikan collection belum ada di Scene Collection
                if collection_name not in [c.name for c in bpy.context.scene.collection.children]:
                    # Link collection ke scene collection (root)
                    bpy.context.scene.collection.children.link(bpy.data.collections[collection_name])
                    self.report({'INFO'}, f"Collection {collection_name} berhasil di-append ke Scene Collection")
                else:
                    self.report({'INFO'}, f"Collection {collection_name} sudah ada di Scene Collection")
            else:
                self.report({'WARNING'}, f"Collection {collection_name} tidak ditemukan setelah append")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error saat append collection: {str(e)}")
            return {'CANCELLED'}
    
classes = [
    Pack_Set_Profile,
    Render_animPack,
    Append_Pack_Coll18,
    Append_Pack_Coll18B,
    Append_Pack_Coll19,
]


# Register function
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


# Unregister function
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)    