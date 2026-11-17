bl_info = {
    "name": "ZeusLab",
    "author": "Putra Tegar",
    "version": (1, 10, 1),
    "blender": (5, 0, 1),
    "description": "Addon for helping Zeus's workflow for animation",
    "location": "3D Side Panel > ZeusLab",
    "category": "3D View",
    "use_pin": True,
    "doc_url": "https://zeusanim.notion.site/ZeusLab-Manual-306b85d5ae5a808fb3e9eecd8d05f511?source=copy_link"
}

# Import modul dari subfolder
import bpy
import os
from . import bonver
from . import fileset
# from . import panel
from . import updater
from . import preferences
from . import manage
from . import zeploy_counts

# Feature use for zeploy, the studio's deployment tool (see zeploy_counts.py).
zeploy_counts.count_features(__name__, bl_info["version"])


modules = [bonver,
           fileset,
           updater,
           preferences,
           manage,
           ]

def register():
    bpy.types.Scene.tools_empty_name = bpy.props.StringProperty(
        name="",
        default="Empty",
        description="Nama untuk Empty yang akan dibuat"
    )
    for mod in modules:
        mod.register()


def unregister():
    del bpy.types.Scene.tools_empty_name
    for mod in reversed(modules):
        mod.unregister()

if __name__ == "__main__":
    register()