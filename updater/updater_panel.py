import bpy
from bpy.props import BoolProperty, StringProperty
from .. import bl_info

# Properties untuk update checker
update_props = {
    "zeuslab_update_available": BoolProperty(
        name="Update Available",
        default=False
    ),
    "zeuslab_latest_version": StringProperty(
        name="Latest Version",
        default=""
    ),
    "zeuslab_download_url": StringProperty(
        name="Download URL",
        default=""
    ),
    "zeuslab_changelog": StringProperty(
        name="Changelog",
        default=""
    ),
}

def draw_update_section(self, layout, context):
    """Draw function untuk section Update"""
    scene = context.scene
    
    box = layout.box()
    box.label(text="Auto Update", icon='FILE_REFRESH')
    
    # Tampilkan versi saat ini
    version_str = ".".join(str(v) for v in bl_info['version'])
    row = box.row()
    row.label(text=f"Versi saat ini: v{version_str}")
    
    # Tombol periksa update
    row = box.row()
    row.scale_y = 1.3
    row.operator("zeuslab.check_for_updates", icon='URL', text="Cek Update")
    
    # Status update
    status_box = box.box()
    if hasattr(scene, "zeuslab_update_available") and scene.zeuslab_update_available:
        col = status_box.column(align=True)
        col.label(text=f"✓ Update tersedia: v{scene.zeuslab_latest_version}", icon='PACKAGE')
        
        # Tampilkan changelog jika ada
        if hasattr(scene, "zeuslab_changelog") and scene.zeuslab_changelog:
            col.separator()
            col.label(text="Changelog:", icon='TEXT')
            
            changelog_box = status_box.box()
            for line in scene.zeuslab_changelog.split('\n'):
                if line.strip():
                    changelog_box.label(text=f"  • {line.strip()}")
        
        # Tombol install update
        col.separator()
        row = col.row()
        row.scale_y = 1.5
        row.operator("zeuslab.install_update", icon='IMPORT', text="Install Update")
    else:
        status_box.label(text="✓ Addon sudah versi terbaru", icon='CHECKMARK')

# import bpy
# import os
# from bpy.types import AddonPreferences
# from .. import bl_info

# class ZeusLabUpdatePreferences(AddonPreferences):
#     """Preferences untuk ZeusLab Addon dengan fitur auto-update"""
#     # bl_idname harus sama dengan nama folder addon atau __package__
#     bl_idname = __package__.split('.')[0]
    
#     def draw(self, context):
#         layout = self.layout
#         scene = context.scene
        
#         # Section Update
#         box = layout.box()
#         box.label(text="Auto Update", icon='FILE_REFRESH')
        
#         # Tampilkan versi saat ini
#         version_str = ".".join(str(v) for v in bl_info['version'])
#         row = box.row()
#         row.label(text=f"Versi saat ini: v{version_str}")
        
#         # Tombol periksa update
#         row = box.row()
#         row.scale_y = 1.3
#         row.operator("zeuslab.check_for_updates", icon='URL', text="Cek Update")
        
#         # Status update
#         status_box = box.box()
#         if hasattr(scene, "zeuslab_update_available") and scene.zeuslab_update_available:
#             # Update tersedia
#             col = status_box.column(align=True)
#             col.label(text=f"✓ Update tersedia: v{scene.zeuslab_latest_version}", icon='PACKAGE')
            
#             # Tampilkan changelog jika ada
#             if hasattr(scene, "zeuslab_changelog") and scene.zeuslab_changelog:
#                 col.separator()
#                 col.label(text="Changelog:", icon='TEXT')
                
#                 changelog_box = status_box.box()
#                 for line in scene.zeuslab_changelog.split('\n'):
#                     if line.strip():
#                         changelog_box.label(text=f"  • {line.strip()}")
            
#             # Tombol install update
#             col.separator()
#             row = col.row()
#             row.scale_y = 1.5
#             row.operator("zeuslab.install_update", icon='IMPORT', text="Install Update Sekarang")
#         else:
#             # Tidak ada update atau belum dicek
#             status_box.label(text="✓ Addon sudah versi terbaru", icon='CHECKMARK')
        
#         # Separator untuk section lain (jika ada)
#         layout.separator()
        
#         # Anda bisa menambahkan preferensi lain di sini
#         # Contoh:
#         # other_box = layout.box()
#         # other_box.label(text="Pengaturan Lainnya", icon='PREFERENCES')
#         # other_box.prop(self, "some_property")

            
# def register():
#     bpy.utils.register_class(ZeusLabUpdatePreferences)
    
#     # Tambahkan property untuk update ke Scene
#     bpy.types.Scene.zeuslab_update_available = bpy.props.BoolProperty(default=False)
#     bpy.types.Scene.zeuslab_latest_version = bpy.props.StringProperty(default="")
#     bpy.types.Scene.zeuslab_download_url = bpy.props.StringProperty(default="")
#     bpy.types.Scene.zeuslab_changelog = bpy.props.StringProperty(default="")

# def unregister():
#     bpy.utils.unregister_class(ZeusLabUpdatePreferences)
    
#     # Hapus property
#     del bpy.types.Scene.zeuslab_update_available
#     del bpy.types.Scene.zeuslab_latest_version
#     del bpy.types.Scene.zeuslab_download_url
#     del bpy.types.Scene.zeuslab_changelog