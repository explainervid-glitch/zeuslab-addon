import bpy
import os
import subprocess
import string
from ..preferences import get_addon_preferences

def configure_cycles_device(scene):
    """Mengatur Device Cycles (OptiX/CUDA) dengan aman untuk Blender 5.0."""
    try:
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'GPU'
        
        prefs = bpy.context.preferences.addons['cycles'].preferences
        
        try:
            prefs.compute_device_type = 'OPTIX'
        except TypeError:
            prefs.compute_device_type = 'CUDA'
            
        prefs.get_devices()
        
        # Aktifkan hanya GPU, nonaktifkan CPU
        for device in prefs.devices:
            if device.type == 'CPU':
                device.use = False  # ← Matikan CPU
            else:
                device.use = True   # ← Aktifkan GPU (OPTIX/CUDA)
            
    except Exception as e:
        print(f"Warning: Gagal konfigurasi GPU Cycles. Menggunakan default. Error: {e}")

def set_output_format(scene, format_type='FFMPEG'):
    """Mengatur format output dengan Fallback jika FFMPEG tidak tersedia."""
    try:
        if format_type == 'FFMPEG':
            scene.render.image_settings.file_format = 'FFMPEG'
            scene.render.ffmpeg.format = 'MPEG4'
            scene.render.ffmpeg.codec = 'H264'
        else:
            scene.render.image_settings.file_format = format_type
    except TypeError:
        # Fallback jika FFMPEG dihapus/tidak ada di build ini
        print(f"Warning: Format '{format_type}' tidak ditemukan di API versi ini. Fallback ke 'PNG'.")
        scene.render.image_settings.file_format = 'PNG'

class Style18_Setting(bpy.types.Operator):
    bl_idname = "set.18"
    bl_label = ""
    bl_description = "Mengatur Render Setting Style 18"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Setup Render & Device
        configure_cycles_device(scene)
        
        scene.render.fps = 30
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.01
        scene.cycles.samples = 256
        scene.render.use_persistent_data = True

        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100

        # SAFE FORMAT SETTING
        set_output_format(scene, 'FFMPEG')
        
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Filmic'
        scene.view_settings.look = 'High Contrast'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 18 Render Setting Applied!")
        return {'FINISHED'}
    
class Style19_Setting(bpy.types.Operator):
    bl_idname = "set.19"
    bl_label = ""
    bl_description = "Mengatur Render Setting Style 19"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Performa
        configure_cycles_device(scene)
        
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.01
        scene.cycles.samples = 256
        scene.render.use_persistent_data = True

        # Denoise
        scene.cycles.use_denoising = True
        # scene.cycles.denoising_store_passes = True  (REMOVED)
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        scene.cycles.use_light_tree = True

        # Motion Blur
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = 0.50
        scene.render.motion_blur_position = 'CENTER'

        # Resolusi
        scene.render.fps = 30
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        # Color Management 
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'AgX'
        try:
            scene.view_settings.look = 'Medium High Contrast'
        except TypeError:
            scene.view_settings.look = 'None'
            
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 19 Render Setting Applied!")
        return {'FINISHED'}
    
class Style20_Setting(bpy.types.Operator):
    bl_idname = "set.20"
    bl_label = ""
    bl_description = "Render Setting Style 20 Isometric"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Performa
        configure_cycles_device(scene)

        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.0100
        scene.cycles.samples = 256
        scene.render.use_persistent_data = True

        # Denoise
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        
        scene.cycles.use_light_tree = False
        # scene.cycles.light_threshold = 0.01 (REMOVED: Property dihapus di Blender 5.0)

        # Motion Blur
        scene.render.use_motion_blur = False
        scene.render.motion_blur_shutter = 0.50
        scene.render.motion_blur_position = 'CENTER'

        # Resolusi
        scene.render.fps = 30
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        # Color Management 
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Filmic'
        scene.view_settings.look = 'Medium Contrast'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 20 Render Setting Applied!")
        return {'FINISHED'}
    
class Style21_Setting(bpy.types.Operator):
    bl_idname = "set.21"
    bl_label = ""
    bl_description = "Render Setting Style 21 Isometric"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Performa
        configure_cycles_device(scene)

        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.0100
        scene.cycles.samples = 256
        scene.render.use_persistent_data = True

        # Denoise
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        
        scene.cycles.use_light_tree = True
        # scene.cycles.light_threshold = 0.01 (REMOVED)

        # Motion Blur
        scene.render.use_motion_blur = False
        scene.render.motion_blur_shutter = 0.50
        scene.render.motion_blur_position = 'CENTER'

        # Resolusi
        scene.render.fps = 30
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        # Color Management 
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'Filmic'
        scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 21 Render Setting Applied!")
        return {'FINISHED'}
    
class Style22_Setting(bpy.types.Operator):
    bl_idname = "set.22"
    bl_label = ""
    bl_description = "Render Setting Style 22 No Face"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Performa
        configure_cycles_device(scene)

        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.0100
        scene.cycles.samples = 256
        scene.render.use_persistent_data = True

        # Denoise
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        
        scene.cycles.use_light_tree = True
        # scene.cycles.light_threshold = 0.01 (REMOVED)

        # Motion Blur
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = 0.50
        scene.render.motion_blur_position = 'CENTER'

        # Resolusi
        scene.render.fps = 30
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        # Color Management 
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'AgX'
        try:
            scene.view_settings.look = 'Medium High Contrast'
        except TypeError:
            scene.view_settings.look = 'None'
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 22 Render Setting Applied!")
        return {'FINISHED'}

class Style23_Setting(bpy.types.Operator):
    bl_idname = "set.23"
    bl_label = ""
    bl_description = "Render Setting Style 23 Realist"

    def execute(self, context):
        scene = bpy.context.scene
        
        # Performa
        configure_cycles_device(scene)

        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.0100
        scene.cycles.samples = 512
        scene.render.use_persistent_data = True

        # Denoise
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        scene.cycles.denoising_prefilter = 'ACCURATE'
        
        scene.cycles.use_light_tree = True
        # scene.cycles.light_threshold = 0.01 (REMOVED)

        # Motion Blur
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = 0.50
        scene.render.motion_blur_position = 'CENTER'

        # Resolusi
        scene.render.fps = 30
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        
        # Color Management 
        scene.display_settings.display_device = 'sRGB'
        scene.view_settings.view_transform = 'AgX'
        try:
            scene.view_settings.look = 'Medium High Contrast'
        except TypeError:
            scene.view_settings.look = 'None'
            
        scene.view_settings.exposure = 0.0
        scene.view_settings.gamma = 1.0
        scene.sequencer_colorspace_settings.name = 'sRGB'

        self.report({'INFO'}, "Style 23 Render Setting Applied!")
        return {'FINISHED'}

class style_setting_panel(bpy.types.Panel):
    """Setting Render Every Style"""
    bl_label = "3D Explainer Style"
    bl_idname = "Style_render_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZeusLab"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_style_render_panel
        return True

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text='3D Style Setting', icon='RENDER_STILL')
        grid = box.grid_flow(columns=3, row_major=True, even_columns=False, even_rows=False, align=True)
        grid.enabled = True
        grid.active = True
        grid.use_property_split = False
        grid.use_property_decorate = False
        grid.alignment = 'Expand'.upper()
        grid.scale_x = 1.0
        grid.scale_y = 1.5

        grid.operator('set.18', text='18', icon_value=0, emboss=True, depress=False)
        grid.operator('set.19', text='19', icon_value=0, emboss=True, depress=False)
        grid.operator('set.20', text='20', icon_value=0, emboss=True, depress=False)
        grid.operator('set.21', text='21', icon_value=0, emboss=True, depress=False)
        grid.operator('set.22', text='22', icon_value=0, emboss=True, depress=False)
        grid.operator('set.23', text='23', icon_value=0, emboss=True, depress=False)
        grid.operator('set.24', text='24', icon_value=0, emboss=True, depress=False)

classes = [
    Style18_Setting, Style19_Setting, Style20_Setting,
    Style21_Setting, Style22_Setting, Style23_Setting,
    style_setting_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)