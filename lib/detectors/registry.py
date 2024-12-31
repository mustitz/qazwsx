import log
from environment import environment
from utils import fail

class Detectors:
    def __init__(self):
        self.known = {}

    def run(self, objname, *args, **kwargs):
        candidates = self.known.get(objname, [])
        for _, entry in candidates:
            result = entry(objname, *args, **kwargs)
            if result is not None:
                return result
        return None

    def register(self, objname, method, priority):
        lst = self.known.get(objname)
        if lst is None:
            lst = []
            self.known[objname] = lst

        lst.append((priority, method))
        lst.sort(reverse=True)

def register(objname, method, priority=10):
    detectors = environment.components.detectors
    if detectors is None:
        fail(f"Cannot register detector: {objname}")

    detectors.register(objname, method, priority)
    log.notice(f"Registered detector for {objname}/{priority}: {method.__name__}")

def _init():
    detectors = Detectors()
    environment.components.detectors = detectors

_init()
