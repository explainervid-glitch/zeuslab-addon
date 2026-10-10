import bpy
from bpy.types import AddonPreferences
from bpy.props import EnumProperty, BoolProperty

# Import draw functions dari file lain
from . import manage
from .updater import updater_panel

class ZeusLabAddonPreferences(AddonPreferences):
    """Main Preferences yang menggabungkan semua section"""
    bl_idname = "ZeusLab"
    
    # Tab selector
    prefs_tabs: EnumProperty(
        name="Preferences Tabs",
        items=[
            ('MANAGE', "Manage Panels", "Kelola visibility panels", 'WINDOW', 0),
            ('UPDATE', "Update", "Auto update checker", 'FILE_REFRESH', 1),
        ],
        default='MANAGE'
    )
    
    # Panel visibility properties dari manage.py
    show_bonesnap_panel: BoolProperty(
        name="Snap Bones",
        description="Tampilkan/sembunyikan panel Snap Bones",
        default=True
    )
    show_bonver_panel: BoolProperty(
        name="Mixamo Rig to Bones",
        description="Tampilkan/sembunyikan panel Mixamo Rig to Bones",
        default=False
    )
    show_attach_panel: BoolProperty(
        name="Simple Take",
        description="Tampilkan/sembunyikan panel Simple Take",
        default=True
    )
    show_pack_panel: BoolProperty(
        name="Zeus Pack Assistant",
        description="Tampilkan/sembunyikan panel Zeus Pack Assistant",
        default=False
    )
    show_style_render_panel: BoolProperty(
        name="3D Explainer Style",
        description="Tampilkan/sembunyikan panel 3D Explainer Style Render",
        default=False
    )
    show_animz_panel: BoolProperty(
        name="Animz™",
        description="Tampilkan/sembunyikan panel Animz™",
        default=True
    )
    
    show_coming_soon_1: BoolProperty(
        name="Coming Soon 1",
        description="Tampilkan/sembunyikan panel Coming Soon 1",
        default=False
    )
    show_coming_soon_2: BoolProperty(
        name="Coming Soon 2",
        description="Tampilkan/sembunyikan panel Coming Soon 2",
        default=False
    )
    show_coming_soon_3: BoolProperty(
        name="Coming Soon 3",
        description="Tampilkan/sembunyikan panel Coming Soon 3",
        default=False
    )
    show_coming_soon_4: BoolProperty(
        name="Coming Soon 4",
        description="Tampilkan/sembunyikan panel Coming Soon 4",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Tab selector
        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)
        
        layout.separator()
        
        # Render section berdasarkan tab aktif
        if self.prefs_tabs == 'MANAGE':
            manage.draw_manage_section(self, layout)
        elif self.prefs_tabs == 'UPDATE':
            updater_panel.draw_update_section(self, layout, context)

# ==============================================================================
# HELPER FUNCTION (preferences.py)
# ==============================================================================

def get_addon_preferences():
    """Mendapatkan addon preferences dari mana saja"""
    import bpy
    addon_name = "ZeusLab"
    preferences = bpy.context.preferences.addons.get(addon_name)
    if preferences:
        return preferences.preferences
    return None

def register():
    # Register class
    bpy.utils.register_class(ZeusLabAddonPreferences)

def unregister():
    bpy.utils.unregister_class(ZeusLabAddonPreferences)