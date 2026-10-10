from . import bonver_operator
from . import bonesnap
from . import simpletake

def register():
    bonesnap.register()
    bonver_operator.register()
    simpletake.register()

def unregister():
    bonesnap.unregister()
    bonver_operator.unregister()
    simpletake.unregister()