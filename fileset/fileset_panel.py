import bpy
from ..preferences import get_addon_preferences

class Pack_exporter(bpy.types.Panel):
    """Export pack animasi character"""
    bl_label = ""
    bl_idname = "Pack_UI_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZeusLab"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences()
        if prefs:
            return prefs.show_pack_panel
        return True

    def draw_header(self, context):
        layout = self.layout
        layout.label(text='Zeus Pack Assistant')

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Zeus Pack Exporter", icon='PACKAGE')
        row = box.row(align=True)
        row.alignment = 'CENTER'
        row.scale_x = 5.0
        # row.operator("append.pack_coll18", text="18")
        row.operator("append.pack_coll18b", text="18")
        row.operator("append.pack_coll19", text="19")
        row.operator("pack.profile", icon='COPY_ID')
        col = box.column()
        col.scale_y = 1.5
        col.operator("render.animpack", icon='RENDER_ANIMATION', text="RENDER!")

class fileset_UI_panel(bpy.types.Panel):
    """Export playblast untuk pack animasi character"""
    bl_label = "For Intern"
    bl_idname = "Fileset_UI_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZeusLab"
    bl_parent_id = "Pack_UI_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.separator()

        box = layout.box()
        box.label(text="Playblast Exporter (Intern)", icon='VIEW3D')
        row = box.row(align=True)
        row.alignment = 'CENTER'
        split = row.split(factor=0.5, align=True)
        
        left = split.row(align=True)
        left.scale_x = 3.0
        left.operator("append.camera_collection_18")
        left.operator("append.camera_collection_19")
        

        right = split.row()
        right.operator("profile.setting", icon='COPY_ID')
        # right.operator("fps.convert_to_30", text="30")
        # right.operator("fps.convert_to_60", text="60")

        col = box.column(align=True)
        col.scale_y = 1.5
        col.operator("renderplaybast.setting", text="Export Playblast", icon='RENDER_ANIMATION')


def register():
    bpy.utils.register_class(Pack_exporter)
    bpy.utils.register_class(fileset_UI_panel)

def unregister():
    bpy.utils.unregister_class(Pack_exporter)
    bpy.utils.unregister_class(fileset_UI_panel)