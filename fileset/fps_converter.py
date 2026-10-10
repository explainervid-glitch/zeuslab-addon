import bpy
from bpy.types import Operator

# ============================================================================
# COMPATIBILITY LAYER untuk Blender 4.2 LTS dan 5.0+
# ============================================================================

def get_fcurves_from_action(action, animation_data=None):
    """
    Mendapatkan fcurves dari action dengan cara yang kompatibel
    antara Blender 4.2 dan 5.0+
    
    Args:
        action: bpy.types.Action object
        animation_data: bpy.types.AnimData object (diperlukan untuk 5.0+)
    
    Returns:
        Collection of FCurves atau None
    """
    if action is None:
        return None
    
    # Cek apakah menggunakan Blender 5.0+ dengan channelbag system
    # Kita cek dengan melihat apakah action memiliki attribute 'layers'
    if hasattr(action, 'layers') and len(action.layers) > 0:
        # Blender 5.0+ - gunakan channelbag system
        try:
            from bpy_extras import anim_utils
            
            # Jika animation_data tersedia, gunakan slot yang sesuai
            if animation_data and hasattr(animation_data, 'action_slot'):
                channelbag = anim_utils.action_get_channelbag_for_slot(
                    action, 
                    animation_data.action_slot
                )
                if channelbag:
                    return channelbag.fcurves
            
            # Fallback: gunakan layer pertama, strip pertama
            if len(action.layers) > 0 and len(action.layers[0].strips) > 0:
                strip = action.layers[0].strips[0]
                # Ambil channelbag pertama yang ada
                for slot in action.slots:
                    channelbag = strip.channelbag(slot)
                    if channelbag:
                        return channelbag.fcurves
        except:
            pass
    
    # Blender 4.2 LTS atau fallback untuk 5.0+ (legacy API)
    # Legacy API masih tersedia di 5.0 untuk backward compatibility
    if hasattr(action, 'fcurves'):
        return action.fcurves
    
    return None


class FPS_OT_convert_to_30(Operator):
    """Convert animation from current FPS to 30 FPS while maintaining timing"""
    bl_idname = "fps.convert_to_30"
    bl_label = "Convert to 30 FPS"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        current_fps = context.scene.render.fps
        target_fps = 30
        
        if current_fps == target_fps:
            self.report({'INFO'}, f"Scene already at {target_fps} FPS")
            return {'FINISHED'}
        
        scale_factor = target_fps / current_fps
        
        # Konversi keyframe dengan rounding yang tepat
        self.convert_keyframes(context, scale_factor)
        
        # Konversi keyframe pada material nodes
        self.convert_material_keyframes(context, scale_factor)
        
        # Update frame rate
        context.scene.render.fps = target_fps
        
        # Update frame range
        new_end_frame = round(context.scene.frame_end * scale_factor)
        context.scene.frame_end = new_end_frame
        
        # Update current frame position
        new_current_frame = round(context.scene.frame_current * scale_factor)
        context.scene.frame_set(new_current_frame)
        
        self.report({'INFO'}, f"Converted from {current_fps} FPS to {target_fps} FPS")
        return {'FINISHED'}
    
    def convert_keyframes(self, context, scale_factor):
        """Konversi keyframes dengan rounding yang tepat"""
        for obj in context.scene.objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                
                # Gunakan compatibility function untuk mendapatkan fcurves
                fcurves = get_fcurves_from_action(action, obj.animation_data)
                if not fcurves:
                    continue
                
                for fcurve in fcurves:
                    # Kumpulkan semua keyframe data terlebih dahulu
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        # Round ke integer terdekat untuk menghindari posisi aneh
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    # Hapus semua keyframes lama
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    # Tambahkan keyframes baru dengan posisi yang sudah diround
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    # Update FCurve
                    fcurve.update()
    
    def convert_material_keyframes(self, context, scale_factor):
        """Konversi keyframes pada material nodes"""
        for material in bpy.data.materials:
            if material.animation_data and material.animation_data.action:
                action = material.animation_data.action
                
                # Gunakan compatibility function
                fcurves = get_fcurves_from_action(action, material.animation_data)
                if not fcurves:
                    continue
                
                for fcurve in fcurves:
                    # Kumpulkan keyframe data
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    # Hapus keyframes lama
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    # Tambahkan keyframes baru
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    fcurve.update()
        
        # Konversi keyframes pada world shader juga jika ada
        if context.scene.world and context.scene.world.animation_data:
            world = context.scene.world
            if world.animation_data.action:
                action = world.animation_data.action
                
                # Gunakan compatibility function
                fcurves = get_fcurves_from_action(action, world.animation_data)
                if not fcurves:
                    return
                
                for fcurve in fcurves:
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    fcurve.update()


class FPS_OT_convert_to_60(Operator):
    """Convert animation from current FPS to 60 FPS while maintaining timing"""
    bl_idname = "fps.convert_to_60"
    bl_label = "Convert to 60 FPS"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        current_fps = context.scene.render.fps
        target_fps = 60
        
        if current_fps == target_fps:
            self.report({'INFO'}, f"Scene already at {target_fps} FPS")
            return {'FINISHED'}
        
        scale_factor = target_fps / current_fps
        
        # Konversi keyframe dengan rounding yang tepat
        self.convert_keyframes(context, scale_factor)
        
        # Konversi keyframe pada material nodes
        self.convert_material_keyframes(context, scale_factor)
        
        # Update frame rate
        context.scene.render.fps = target_fps
        
        # Update frame range
        new_end_frame = round(context.scene.frame_end * scale_factor)
        context.scene.frame_end = new_end_frame
        
        # Update current frame position
        new_current_frame = round(context.scene.frame_current * scale_factor)
        context.scene.frame_set(new_current_frame)
        
        self.report({'INFO'}, f"Converted from {current_fps} FPS to {target_fps} FPS")
        return {'FINISHED'}
    
    def convert_keyframes(self, context, scale_factor):
        """Konversi keyframes dengan rounding yang tepat"""
        for obj in context.scene.objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                
                # Gunakan compatibility function untuk mendapatkan fcurves
                fcurves = get_fcurves_from_action(action, obj.animation_data)
                if not fcurves:
                    continue
                
                for fcurve in fcurves:
                    # Kumpulkan semua keyframe data terlebih dahulu
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        # Round ke integer terdekat untuk menghindari posisi aneh
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    # Hapus semua keyframes lama
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    # Tambahkan keyframes baru dengan posisi yang sudah diround
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    # Update FCurve
                    fcurve.update()
    
    def convert_material_keyframes(self, context, scale_factor):
        """Konversi keyframes pada material nodes"""
        for material in bpy.data.materials:
            if material.animation_data and material.animation_data.action:
                action = material.animation_data.action
                
                # Gunakan compatibility function
                fcurves = get_fcurves_from_action(action, material.animation_data)
                if not fcurves:
                    continue
                
                for fcurve in fcurves:
                    # Kumpulkan keyframe data
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    # Hapus keyframes lama
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    # Tambahkan keyframes baru
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    fcurve.update()
        
        # Konversi keyframes pada world shader juga jika ada
        if context.scene.world and context.scene.world.animation_data:
            world = context.scene.world
            if world.animation_data.action:
                action = world.animation_data.action
                
                # Gunakan compatibility function
                fcurves = get_fcurves_from_action(action, world.animation_data)
                if not fcurves:
                    return
                
                for fcurve in fcurves:
                    keyframe_data = []
                    for keyframe in fcurve.keyframe_points:
                        new_frame = round(keyframe.co.x * scale_factor)
                        keyframe_data.append({
                            'frame': new_frame,
                            'value': keyframe.co.y,
                            'handle_left_type': keyframe.handle_left_type,
                            'handle_right_type': keyframe.handle_right_type,
                            'interpolation': keyframe.interpolation
                        })
                    
                    while len(fcurve.keyframe_points) > 0:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
                    
                    for data in keyframe_data:
                        keyframe = fcurve.keyframe_points.insert(data['frame'], data['value'])
                        keyframe.handle_left_type = data['handle_left_type']
                        keyframe.handle_right_type = data['handle_right_type']
                        keyframe.interpolation = data['interpolation']
                    
                    fcurve.update()


# Fungsi untuk registrasi addon
def register():
    """Mendaftarkan semua class agar bisa digunakan Blender"""
    bpy.utils.register_class(FPS_OT_convert_to_30)
    bpy.utils.register_class(FPS_OT_convert_to_60)

def unregister():
    """Menghapus registrasi ketika addon dinonaktifkan"""
    bpy.utils.unregister_class(FPS_OT_convert_to_60)
    bpy.utils.unregister_class(FPS_OT_convert_to_30)