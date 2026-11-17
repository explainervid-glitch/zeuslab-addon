"""Which ZeusLab features get used, for zeploy (the studio's deployment tool).

zeploy_usage.py is zeploy's helper, copied unchanged: it appends one line per
use to %LOCALAPPDATA%\\zeploy\\usage\\ZeusLab.jsonl, only on PCs where zeploy is
installed, and zeploy's agent collects the file. No names, paths or scene data.

Each operator below counts once per run that is not cancelled, under the
feature name next to it; a run that raises counts as an error. An operator a
ZeusLab operator runs itself (Prepare Bake runs Duplicate Collection and
Bake) is not counted again.
Operators not listed (list buttons, helpers, the updater) are not counted.
"""

import functools
import time

import bpy

from . import zeploy_usage

FEATURES = {
    # BoneSnap
    "pose.add_empty_to_bone": "bonesnap add empty",
    "pose.snap_influence": "bonesnap snap",
    "pose.unsnap_influence": "bonesnap unsnap",
    "pose.update_empty": "bonesnap update empty",
    "pose.tweak_pose": "bonesnap tweak pose",
    "pose.bake_action": "bonesnap bake",
    # Bonver
    "object.duplicate_collection": "bonver duplicate collection",
    "object.set_bone_collection_visibility": "bonver show bones",
    "bonver.bake_action": "bonver bake",
    "bonver.prepare_bake": "bonver prepare bake",
    # SimplyTake
    "attach.constraint_list_add": "simpletake add",
    "attach.constraint_list_remove": "simpletake remove",
    "attach.new": "simpletake attach",
    "attach.childof_attach": "simpletake attach",
    "attach.childof_detach": "simpletake detach",
    "attach.childof_key_attach": "simpletake key attach",
    "attach.childof_key_detach": "simpletake key detach",
    # Animz
    "animz.append_node": "animz append node",
    "animz.upgrade_node_group": "animz upgrade node",
    "animz.animate_popup": "animz pop in",
    "animz.animate_out_popup": "animz pop out",
    "animz.update_in_animation": "animz update in",
    "animz.update_out_animation": "animz update out",
    "animz.delete_animation": "animz delete animation",
    "animz.add_wiggle": "animz add wiggle",
    "animz.copy_wiggle": "animz copy wiggle",
    "animz.remove_wiggle": "animz remove wiggle",
    # FPS converter
    "fps.convert_to_30": "fps convert 30",
    "fps.convert_to_60": "fps convert 60",
    # Pack
    "pack.profile": "pack set profile",
    "render.animpack": "pack render",
    "append.pack_coll18": "pack append style",
    "append.pack_coll18b": "pack append style",
    "append.pack_coll19": "pack append style",
    # Playblast
    "renderplaybast.setting": "playblast render",
    "profile.setting": "playblast set profile",
    "append.camera_collection_18": "playblast append camera",
    "append.camera_collection_19": "playblast append camera",
}

usage = None
_depth = 0  # ZeusLab operators running, the outermost first


def _counted(name, execute):
    @functools.wraps(execute)
    def wrapper(self, context):  # Blender wants exactly (self, context)
        global _depth
        _depth += 1
        start = time.perf_counter()
        try:
            result = execute(self, context)
        except Exception:
            if _depth == 1:
                usage.error(name)
            raise
        finally:
            _depth -= 1
        if _depth == 0 and not (isinstance(result, set) and "CANCELLED" in result):
            usage.action(name, (time.perf_counter() - start) * 1000)
        return result

    wrapper._zeploy_counted = True
    return wrapper


def count_features(package, version):
    """Wrap the listed operators' execute. Call once at import, before register():
    Blender must never see a method replaced on a registered class."""
    global usage
    usage = zeploy_usage.Usage("ZeusLab", ".".join(map(str, version)))
    pending = list(bpy.types.Operator.__subclasses__())
    while pending:
        cls = pending.pop()
        pending.extend(cls.__subclasses__())
        name = FEATURES.get(getattr(cls, "bl_idname", ""))
        execute = cls.__dict__.get("execute")
        if not cls.__module__.startswith(package) or name is None or execute is None:
            continue
        if not getattr(execute, "_zeploy_counted", False):
            cls.execute = _counted(name, execute)
