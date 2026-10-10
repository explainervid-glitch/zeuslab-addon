import bpy
from bpy.types import Operator
from ..updater.updater import updater

class ZeusLabCheckForUpdates(Operator):
    bl_idname = "zeuslab.check_for_updates"
    bl_label = "Check for Updates"
    bl_description = "Periksa apakah ada update terbaru untuk addon ZeusLab"
    
    def execute(self, context):
        # Periksa update
        has_update, version, download_url, changelog = updater.check_for_updates()
        
        if has_update:
            # Simpan informasi update ke Scene properties
            context.scene.zeuslab_update_available = True
            context.scene.zeuslab_latest_version = ".".join(str(v) for v in version)
            context.scene.zeuslab_download_url = download_url
            context.scene.zeuslab_changelog = changelog
            
            self.report({'INFO'}, f"Update tersedia: v{context.scene.zeuslab_latest_version}")
        else:
            context.scene.zeuslab_update_available = False
            self.report({'INFO'}, "Addon sudah versi terbaru.")
            
        return {'FINISHED'}
        
class ZeusLabInstallUpdate(Operator):
    bl_idname = "zeuslab.install_update"
    bl_label = "Install Update"
    bl_description = "Download dan install update terbaru untuk addon ZeusLab"
    
    def execute(self, context):
        # Download dan install update
        download_url = context.scene.zeuslab_download_url
        success, message = updater.download_and_install_update(download_url)
        
        if success:
            context.scene.zeuslab_update_available = False
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
            
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ZeusLabCheckForUpdates)
    bpy.utils.register_class(ZeusLabInstallUpdate)

def unregister():
    bpy.utils.unregister_class(ZeusLabInstallUpdate)
    bpy.utils.unregister_class(ZeusLabCheckForUpdates)