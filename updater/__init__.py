import bpy
import os
from . import updater_panel
from . import operators

modules = [
            operators
            ]

def register():
    # Register Scene properties untuk update status
    bpy.types.Scene.zeuslab_update_available = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.zeuslab_latest_version = bpy.props.StringProperty(default="")
    bpy.types.Scene.zeuslab_download_url = bpy.props.StringProperty(default="")
    bpy.types.Scene.zeuslab_changelog = bpy.props.StringProperty(default="")
    
    for mod in modules:
        mod.register()

def unregister():
    for mod in reversed(modules):
        mod.unregister()
    
    # Hapus Scene properties
    del bpy.types.Scene.zeuslab_update_available
    del bpy.types.Scene.zeuslab_latest_version
    del bpy.types.Scene.zeuslab_download_url
    del bpy.types.Scene.zeuslab_changelog