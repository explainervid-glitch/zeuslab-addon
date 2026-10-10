import bpy
import os
import bpy.utils.previews
from .. import bl_info

def draw_footer(layout):
    row = layout.row()
    row.scale_y = 0.1
    row.label(text=f"v{'.'.join(str(i) for i in bl_info['version'])}", icon='BLANK1')

class Main_ZeusLab_UI(bpy.types.Panel):
    """Creates a Panel in the Scene properties window"""
    bl_label = ""
    bl_idname = "ZeusLab_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZeusLab"

    def draw_header(self, context):
        layout = self.layout
        layout.operator("wm.url_open", text='ZeusLab™', icon='WORLD', emboss=False, depress=False).url = "https://zeusanim.notion.site/ZeusDev-Tools-Manual-231b85d5ae5a80399e3ce78c4630604a?source=copy_link"

    def draw(self, context):
        layout = self.layout
        row = layout.row(heading='', align=True)
        row.alert = False
        row.enabled = True
        row.active = False
        row.use_property_split = False
        row.use_property_decorate = False

def register():
    bpy.utils.register_class(Main_ZeusLab_UI)



def unregister():
    bpy.utils.unregister_class(Main_ZeusLab_UI)