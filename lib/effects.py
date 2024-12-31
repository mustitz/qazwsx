import sys

import log
from environment import environment

class This(sys.__class__): #pylint: disable=no-member
    @property
    def caption(self):
        effector = environment.components.effector
        return effector.caption if effector is not None else None

    @caption.setter
    def caption(self, value):
        effector = environment.components.effector
        if effector is not None:
            effector.caption = value

def mouse_click(x, y):
    log.warn(f"TODO: mot implemented effects mouse_click x={x}; y={y};")

sys.modules[__name__].__class__ = This
