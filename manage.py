import bpy
from bpy.props import BoolProperty

# Properties untuk panel visibility
panel_visibility_props = {
    "show_bonesnap_panel": BoolProperty(
        name="Snap Bones",
        description="Tampilkan/sembunyikan panel Snap Bones",
        default=True
    ),
    "show_bonver_panel": BoolProperty(
        name="Mixamo Rig to Bones",
        description="Tampilkan/sembunyikan panel Mixamo Rig to Bones",
        default=True
    ),
    "show_attach_panel": BoolProperty(
        name="Simple Take",
        description="Tampilkan/sembunyikan panel Simple Take",
        default=True
    ),
    "show_pack_panel": BoolProperty(
        name="Zeus Pack Assistant",
        description="Tampilkan/sembunyikan panel Zeus Pack Assistant",
        default=True
    ),
    "show_style_render_panel": BoolProperty(
        name="3D Expl. Style Settings",
        description="Tampilkan/sembunyikan panel 3D Explainer Style",
        default=True
    ),
    "show_animz_panel": BoolProperty(
        name="AnimZ™",
        description="Tampilkan/sembunyikan panel AnimZ",
        default=True
    ),
    "show_coming_soon_1": BoolProperty(
        name="Coming Soon 1",
        description="Tampilkan/sembunyikan panel Coming Soon 1",
        default=False
    ),
    "show_coming_soon_2": BoolProperty(
        name="Coming Soon 2",
        description="Tampilkan/sembunyikan panel Coming Soon 2",
        default=False
    ),
    "show_coming_soon_3": BoolProperty(
        name="Coming Soon 3",
        description="Tampilkan/sembunyikan panel Coming Soon 3",
        default=False
    ),
    "show_coming_soon_4": BoolProperty(
        name="Coming Soon 4",
        description="Tampilkan/sembunyikan panel Coming Soon 4",
        default=False
    ),
}

def draw_manage_section(self, layout):
    """Draw function untuk section Manage Panels"""
    box = layout.box()
    box.label(text="Manage Addon Panels", icon='WINDOW')
    
    col = box.column(align=True)
    col.label(text="Visibility di N-Panel:", icon='HIDE_OFF')
    
    grid = col.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
    grid.prop(self, "show_bonesnap_panel", toggle=True)
    grid.prop(self, "show_bonver_panel", toggle=True)
    grid.prop(self, "show_attach_panel", toggle=True)
    grid.prop(self, "show_pack_panel", toggle=True)
    grid.prop(self, "show_style_render_panel", toggle=True)
    grid.prop(self, "show_animz_panel", toggle=True)
    grid.prop(self, "show_coming_soon_1", toggle=True)
    grid.prop(self, "show_coming_soon_2", toggle=True)
    grid.prop(self, "show_coming_soon_3", toggle=True)
    grid.prop(self, "show_coming_soon_4", toggle=True)
    
    info_box = layout.box()
    info_box.label(text="ℹ️ Perubahan langsung terlihat di N-Panel", icon='INFO')

def register():
    pass

def unregister():
    pass