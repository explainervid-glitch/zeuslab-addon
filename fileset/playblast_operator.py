import bpy
import os
import shutil
from bpy.props import StringProperty
from bpy.types import Operator

# class PLAYBLAST_OT_apply_settings(bpy.types.Operator):
#     bl_idname = "renderplaybast.setting"
#     bl_label = "Final Render Setting"
#     bl_description = "Render Playblast untuk dua kamera (Split Screen)"
#     bl_options = {'REGISTER', 'UNDO'}

#     def execute(self, context):
#         # Setup render
#         scene = context.scene
#         scene.render.resolution_x = 768
#         scene.render.resolution_y = 864
#         scene.render.resolution_percentage = 100
        
#         # Setup ffmpeg untuk Blender 5.0
#         scene.render.ffmpeg.format = 'MPEG4'
#         scene.render.ffmpeg.codec = 'H264'
        
#         bpy.ops.wm.save_mainfile()
        
#         # Output folder
#         blend_dir = bpy.path.abspath("//")
#         output_dir = os.path.join(blend_dir, "Viewport Render (Temporary)")
#         os.makedirs(output_dir, exist_ok=True)
        
#         # Daftar kamera
#         camera_list = ["Camera.Front", "Camera.Side"]
#         render_paths = []
        
#         # Dapatkan area 3D View yang valid
#         view3d_area = None
#         view3d_region = None
#         for window in context.window_manager.windows:
#             screen = window.screen
#             for area in screen.areas:
#                 if area.type == 'VIEW_3D':
#                     view3d_area = area
#                     for region in area.regions:
#                         if region.type == 'WINDOW':
#                             view3d_region = region
#                             break
#                     if view3d_region:
#                         break
#             if view3d_area and view3d_region:
#                 break
        
#         if not view3d_area or not view3d_region:
#             self.report({'ERROR'}, "Tidak dapat menemukan View3D area yang valid!")
#             return {'CANCELLED'}
        
#         space = view3d_area.spaces.active
#         original_shading_type = space.shading.type
#         original_show_overlays = space.overlay.show_overlays
#         original_view_perspective = space.region_3d.view_perspective
        
#         try:
#             # Setup viewport untuk rendering
#             space.shading.type = 'SOLID'
#             space.overlay.show_overlays = False
            
#             for i, cam_name in enumerate(camera_list):
#                 cam = bpy.data.objects.get(cam_name)
#                 if not cam:
#                     self.report({'WARNING'}, f"Kamera '{cam_name}' tidak ditemukan.")
#                     continue
                
#                 # Set kamera aktif
#                 scene.camera = cam
                
#                 # Path untuk video ini
#                 cam_output_path = os.path.join(output_dir, f"cam{i+1}_")
#                 render_paths.append(cam_output_path)
                
#                 # Setup context override untuk viewport rendering
#                 with context.temp_override(window=window, area=view3d_area, region=view3d_region):
#                     # Paksa perubahan view ke kamera
#                     space.region_3d.view_perspective = 'CAMERA'
#                     space.region_3d.view_matrix = cam.matrix_world.inverted()
                    
#                     # Update view layer
#                     context.view_layer.update()
                    
#                     # Render
#                     scene.render.filepath = cam_output_path
#                     bpy.ops.render.opengl(animation=True, view_context=True)
            
#             # Kembalikan setting viewport
#             space.shading.type = original_shading_type
#             space.overlay.show_overlays = original_show_overlays
#             space.region_3d.view_perspective = original_view_perspective
            
#         finally:
#             # Pastikan viewport dikembalikan ke state asli
#             space.shading.type = original_shading_type
#             space.overlay.show_overlays = original_show_overlays
#             space.region_3d.view_perspective = original_view_perspective
        
#         # Setelah render kedua kamera selesai, buat split screen
#         complete_render_paths = []
#         for path in render_paths:
#             last_frame = context.scene.frame_end
#             video_file = f"{path}0001-{str(last_frame).zfill(4)}.mp4"
#             complete_render_paths.append(video_file)
        
#         self.report({'INFO'}, f"Render paths: {complete_render_paths}")
        
#         # Hanya lanjutkan jika kedua video berhasil dirender
#         if len(complete_render_paths) >= 2:
#             self.create_split_screen(context, complete_render_paths, output_dir, blend_dir)
#         else:
#             self.report({'ERROR'}, "Tidak cukup video yang berhasil dirender untuk split screen!")
        
#         self.report({'INFO'}, "Rendering Playblast dan Split Screen selesai.")
#         return {'FINISHED'}

#     def create_split_screen(self, context, render_paths, output_dir, blend_dir):
#         self.report({'INFO'}, "Memulai proses split screen (Operator-Based)...")
        
#         # Simpan scene aktif saat ini
#         original_scene = context.scene
        
#         try:
#             # 1. Buat scene baru untuk VSE
#             bpy.ops.scene.new(type='NEW')
#             vse_scene = context.scene
#             vse_scene.name = "SplitScreen"
#             self.report({'INFO'}, "Scene SplitScreen baru dibuat")
            
#             # 2. Setup render settings
#             vse_scene.render.resolution_x = 1536  # Lebar total untuk side-by-side
#             vse_scene.render.resolution_y = 864
#             vse_scene.render.fps = original_scene.render.fps
            
#             # Setup ffmpeg untuk Blender 5.0
#             vse_scene.render.ffmpeg.format = 'MPEG4'
#             vse_scene.render.ffmpeg.codec = 'H264'
            
#             # 3. Setup frame range
#             vse_scene.frame_start = original_scene.frame_start
#             vse_scene.frame_end = original_scene.frame_end
            
#             # 4. Pastikan sequence editor aktif
#             if not vse_scene.sequence_editor:
#                 vse_scene.sequence_editor_create()
            
#             # 5. Frame range sudah diset di atas (line 144-145), siap untuk menambahkan strip
            
#             # 6. Tambahkan video pertama (kiri) - PURE OPERATOR APPROACH
#             try:
#                 self.report({'INFO'}, f"Menambahkan video 1: {render_paths[0]}")
                
#                 # Tambahkan movie strip
#                 bpy.ops.sequencer.movie_strip_add(
#                     filepath=render_paths[0],
#                     frame_start=vse_scene.frame_start,
#                     channel=1,
#                     replace_selected=True,
#                     overlap=False
#                 )
                
#                 # Dapatkan strip yang baru ditambahkan melalui selection
#                 seq1 = context.selected_sequences[0] if context.selected_sequences else None
                
#                 if seq1:
#                     seq1.name = "Camera Front"
#                     half_width = vse_scene.render.resolution_x // 2
#                     seq1.transform.offset_x = -half_width // 2
#                     self.report({'INFO'}, f"Video 1 berhasil ditambahkan: {seq1.name}")
#                 else:
#                     self.report({'ERROR'}, "Tidak dapat menemukan strip video 1 setelah penambahan")
            
#             except Exception as e:
#                 self.report({'ERROR'}, f"Error menambahkan video 1: {str(e)}")
#                 return
            
#             # 7. Tambahkan video kedua (kanan) - PURE OPERATOR APPROACH
#             try:
#                 self.report({'INFO'}, f"Menambahkan video 2: {render_paths[1]}")
                
#                 bpy.ops.sequencer.movie_strip_add(
#                     filepath=render_paths[1],
#                     frame_start=vse_scene.frame_start,
#                     channel=2,
#                     replace_selected=True,
#                     overlap=False
#                 )
                
#                 # Dapatkan strip yang baru ditambahkan
#                 seq2 = context.selected_sequences[0] if context.selected_sequences else None
                
#                 if seq2:
#                     seq2.name = "Camera Side"
#                     half_width = vse_scene.render.resolution_x // 2
#                     seq2.transform.offset_x = half_width // 2
#                     self.report({'INFO'}, f"Video 2 berhasil ditambahkan: {seq2.name}")
#                 else:
#                     self.report({'ERROR'}, "Tidak dapat menemukan strip video 2 setelah penambahan")
            
#             except Exception as e:
#                 self.report({'ERROR'}, f"Error menambahkan video 2: {str(e)}")
#                 return
            
#             # 8. Render output final - PURE OPERATOR APPROACH
#             try:
#                 # Setup output path
#                 blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
#                 if not blend_file_name:
#                     blend_file_name = "split_screen_final"
#                     self.report({'WARNING'}, "File belum disimpan, menggunakan nama default untuk output")
                
#                 final_output = os.path.join(blend_dir, f"{blend_file_name}.mp4")
#                 vse_scene.render.filepath = final_output
                
#                 self.report({'INFO'}, f"Merender split screen ke: {final_output}")
#                 bpy.ops.render.render(animation=True)
                
#                 self.report({'INFO'}, "Render split screen selesai")
            
#             except Exception as e:
#                 self.report({'ERROR'}, f"Error saat render: {str(e)}")
        
#         finally:
#             # 9. Kembalikan ke scene asli
#             context.window.scene = original_scene
#             self.report({'INFO'}, f"Kembali ke scene: {original_scene.name}")
            
#             # 10. Hapus scene VSE yang tidak terpakai
#             if "SplitScreen" in bpy.data.scenes:
#                 self.report({'INFO'}, "Menghapus scene VSE yang tidak terpakai")
#                 scenes_to_remove = [scene for scene in bpy.data.scenes if scene.name == "SplitScreen"]
#                 for scene in scenes_to_remove:
#                     bpy.data.scenes.remove(scene)
            
#             # 11. Hapus folder sementara
#             try:
#                 if os.path.exists(output_dir):
#                     self.report({'INFO'}, f"Menghapus folder sementara: {output_dir}")
#                     shutil.rmtree(output_dir, ignore_errors=True)
#                     self.report({'INFO'}, "Folder sementara berhasil dihapus")
#             except Exception as e:
#                 self.report({'WARNING'}, f"Gagal menghapus folder sementara: {str(e)}")

import bpy
import os
import shutil
import subprocess


class PLAYBLAST_OT_apply_settings(bpy.types.Operator):
    bl_idname = "renderplaybast.setting"
    bl_label = "Final Render Setting"
    bl_description = "Render Playblast untuk dua kamera (Split Screen)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Setup render
        scene = context.scene
        scene.render.resolution_x = 768
        scene.render.resolution_y = 864
        scene.render.resolution_percentage = 100
        
        # Setup ffmpeg untuk Blender 5.0
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        
        bpy.ops.wm.save_mainfile()
        
        # Output folder
        blend_dir = bpy.path.abspath("//")
        output_dir = os.path.join(blend_dir, "Viewport Render (Hapus Nnti)")
        os.makedirs(output_dir, exist_ok=True)
        
        # Daftar kamera
        camera_list = ["Camera.Front", "Camera.Side"]
        render_paths = []
        
        # Dapatkan area 3D View yang valid
        view3d_area = None
        view3d_region = None
        for window in context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    view3d_area = area
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            view3d_region = region
                            break
                    if view3d_region:
                        break
            if view3d_area and view3d_region:
                break
        
        if not view3d_area or not view3d_region:
            self.report({'ERROR'}, "Tidak dapat menemukan View3D area yang valid!")
            return {'CANCELLED'}
        
        space = view3d_area.spaces.active
        original_shading_type = space.shading.type
        original_show_overlays = space.overlay.show_overlays
        original_view_perspective = space.region_3d.view_perspective
        
        try:
            # Setup viewport untuk rendering
            space.shading.type = 'SOLID'
            space.overlay.show_overlays = False
            
            for i, cam_name in enumerate(camera_list):
                cam = bpy.data.objects.get(cam_name)
                if not cam:
                    self.report({'WARNING'}, f"Kamera '{cam_name}' tidak ditemukan.")
                    continue
                
                # Set kamera aktif
                scene.camera = cam
                
                # Path untuk video ini
                cam_output_path = os.path.join(output_dir, f"cam{i+1}_")
                render_paths.append(cam_output_path)
                
                # Setup context override untuk viewport rendering
                with context.temp_override(window=window, area=view3d_area, region=view3d_region):
                    # Paksa perubahan view ke kamera
                    space.region_3d.view_perspective = 'CAMERA'
                    space.region_3d.view_matrix = cam.matrix_world.inverted()
                    
                    # Update view layer
                    context.view_layer.update()
                    
                    # Render
                    scene.render.filepath = cam_output_path
                    bpy.ops.render.opengl(animation=True, view_context=True)
            
            # Kembalikan setting viewport
            space.shading.type = original_shading_type
            space.overlay.show_overlays = original_show_overlays
            space.region_3d.view_perspective = original_view_perspective
            
        finally:
            # Pastikan viewport dikembalikan ke state asli
            space.shading.type = original_shading_type
            space.overlay.show_overlays = original_show_overlays
            space.region_3d.view_perspective = original_view_perspective
        
        # Setelah render kedua kamera selesai, buat split screen
        complete_render_paths = []
        for path in render_paths:
            last_frame = context.scene.frame_end
            video_file = f"{path}0001-{str(last_frame).zfill(4)}.mp4"
            complete_render_paths.append(video_file)
        
        self.report({'INFO'}, f"Render paths: {complete_render_paths}")
        
        # Hanya lanjutkan jika kedua video berhasil dirender
        if len(complete_render_paths) >= 2:
            self.create_split_screen_ffmpeg(context, complete_render_paths, output_dir, blend_dir)
        else:
            self.report({'ERROR'}, "Tidak cukup video yang berhasil dirender untuk split screen!")
        
        self.report({'INFO'}, "Rendering Playblast dan Split Screen selesai.")
        return {'FINISHED'}

    def create_split_screen_ffmpeg(self, context, render_paths, output_dir, blend_dir):
        """Buat split screen menggunakan FFmpeg langsung - lebih simple & reliable"""
        self.report({'INFO'}, "Memulai proses split screen dengan FFmpeg...")
        
        try:
            # 1. Setup output path
            blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            if not blend_file_name:
                blend_file_name = "split_screen_final"
            
            final_output = os.path.join(blend_dir, f"{blend_file_name}.mp4")
            
            # 2. Cari FFmpeg dari Blender
            ffmpeg_path = None
            
            # Coba dapatkan ffmpeg dari Blender installation
            blender_path = bpy.app.binary_path
            blender_dir = os.path.dirname(blender_path)
            
            # Kemungkinan lokasi ffmpeg di Blender
            possible_paths = [
                os.path.join(blender_dir, "ffmpeg.exe"),  # Windows
                os.path.join(blender_dir, "ffmpeg"),       # Linux/Mac
                os.path.join(blender_dir, "..", "ffmpeg", "bin", "ffmpeg.exe"),  # Portable
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    break
            
            # Jika tidak ketemu, coba system ffmpeg
            if not ffmpeg_path:
                try:
                    result = subprocess.run(['ffmpeg', '-version'], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=5)
                    if result.returncode == 0:
                        ffmpeg_path = 'ffmpeg'
                except:
                    pass
            
            if not ffmpeg_path:
                self.report({'ERROR'}, "FFmpeg tidak ditemukan! Install FFmpeg atau gunakan VSE manual.")
                return
            
            self.report({'INFO'}, f"Menggunakan FFmpeg: {ffmpeg_path}")
            
            # 3. Buat filter complex untuk side-by-side
            # [0:v] = video kiri (front), [1:v] = video kanan (side)
            filter_complex = (
                f"[0:v]scale=768:864[left];"
                f"[1:v]scale=768:864[right];"
                f"[left][right]hstack=inputs=2[out]"
            )
            
            # 4. Command FFmpeg
            cmd = [
                ffmpeg_path,
                '-i', render_paths[0],  # Input 1: Camera Front
                '-i', render_paths[1],  # Input 2: Camera Side
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-y',  # Overwrite output
                final_output
            ]
            
            self.report({'INFO'}, f"Menjalankan FFmpeg...")
            self.report({'INFO'}, f"Output: {final_output}")
            
            # 5. Jalankan FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 menit timeout
            )
            
            if result.returncode == 0:
                self.report({'INFO'}, f"✓ Split screen berhasil dibuat: {final_output}")
            else:
                self.report({'ERROR'}, f"FFmpeg error: {result.stderr}")
                self.report({'ERROR'}, f"Command: {' '.join(cmd)}")
                
        except subprocess.TimeoutExpired:
            self.report({'ERROR'}, "FFmpeg timeout! Video terlalu panjang.")
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            self.report({'ERROR'}, traceback.format_exc())
        finally:
            # 6. Hapus folder sementara
            try:
                if os.path.exists(output_dir):
                    self.report({'INFO'}, f"Menghapus folder sementara...")
                    shutil.rmtree(output_dir, ignore_errors=True)
                    self.report({'INFO'}, "✓ Cleanup selesai")
            except Exception as e:
                self.report({'WARNING'}, f"Gagal hapus folder: {str(e)}")
                
class PLAYBLAST_OT_set_profile(bpy.types.Operator):
    bl_idname = "profile.setting"
    bl_label = ""
    bl_description = "Apply setting resolusi sebelum export playblast"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.render.resolution_x = 768
        scene.render.resolution_y = 864
        scene.render.resolution_percentage = 100
        
        # Setup ffmpeg untuk Blender 5.0
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        
        self.report({'INFO'}, "Playblast Settings Applied")
        return {'FINISHED'}

class PLAYBLAST_OT_append_camera_collection18(bpy.types.Operator):
    bl_idname = "append.camera_collection_18"
    bl_label = "18"
    bl_description = "Append collection CAM untuk playblast"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Dapatkan path addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file blend yang berisi collection CAM
        template_file = os.path.join(addon_path, "template", "camera_template.blend")
        
        # Cek apakah file template ada
        if not os.path.exists(template_file):
            self.report({'ERROR'}, f"File template tidak ditemukan: {template_file}")
            return {'CANCELLED'}
        
        # Cek apakah collection CAM sudah ada di file
        collection_name = "CAM (Hide Ketika Animasi)"
        if collection_name in bpy.data.collections:
            self.report({'INFO'}, f"Collection {collection_name} sudah ada dalam file")
            return {'FINISHED'}
        
        # Lakukan proses append collection
        try:
            # Append collection dari file template
            with bpy.data.libraries.load(template_file, link=False) as (data_from, data_to):
                if collection_name in data_from.collections:
                    data_to.collections = [collection_name]
            
            # Link collection ke scene jika berhasil diappend
            if collection_name in bpy.data.collections:
                new_collection = bpy.data.collections[collection_name]
                
                # Pastikan collection belum ada di Scene Collection
                if collection_name not in [c.name for c in context.scene.collection.children]:
                    context.scene.collection.children.link(new_collection)
                    self.report({'INFO'}, f"Collection {collection_name} berhasil di-append ke Scene Collection")
                else:
                    self.report({'INFO'}, f"Collection {collection_name} sudah ada di Scene Collection")
            else:
                self.report({'WARNING'}, f"Collection {collection_name} tidak ditemukan setelah append")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error saat append collection: {str(e)}")
            return {'CANCELLED'}

class PLAYBLAST_OT_append_camera_collection19(bpy.types.Operator):
    bl_idname = "append.camera_collection_19"
    bl_label = "19"
    bl_description = "Append collection CAM untuk playblast"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Dapatkan path addon
        addon_path = os.path.dirname(os.path.realpath(__file__))
        
        # Path ke file blend yang berisi collection CAM
        template_file = os.path.join(addon_path, "template", "camera_template19.blend")
        
        # Cek apakah file template ada
        if not os.path.exists(template_file):
            self.report({'ERROR'}, f"File template tidak ditemukan: {template_file}")
            return {'CANCELLED'}
        
        # Cek apakah collection CAM sudah ada di file
        collection_name = "CAM (Hide Ketika Animasi)"
        if collection_name in bpy.data.collections:
            self.report({'INFO'}, f"Collection {collection_name} sudah ada dalam file")
            return {'FINISHED'}
        
        # Lakukan proses append collection
        try:
            # Append collection dari file template
            with bpy.data.libraries.load(template_file, link=False) as (data_from, data_to):
                if collection_name in data_from.collections:
                    data_to.collections = [collection_name]
            
            # Link collection ke scene jika berhasil diappend
            if collection_name in bpy.data.collections:
                new_collection = bpy.data.collections[collection_name]
                
                # Pastikan collection belum ada di Scene Collection
                if collection_name not in [c.name for c in context.scene.collection.children]:
                    context.scene.collection.children.link(new_collection)
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
    PLAYBLAST_OT_apply_settings,
    PLAYBLAST_OT_set_profile,
    PLAYBLAST_OT_append_camera_collection18,
    PLAYBLAST_OT_append_camera_collection19,
]

# Register function
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

# Unregister function
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()