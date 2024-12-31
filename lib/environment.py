from time import time

from easydict import EasyDict

components = EasyDict()
components.logger = None
components.video = None
components.ocr = None
components.effector = None
components.detectors = None

resolution = EasyDict()
resolution.width = 1920
resolution.height = 1080
resolution.bpp = 32

environment = EasyDict()
environment.script_fn = None
environment.machine_name = None
environment.snapshot_name = None
environment.started_at = time()
environment.start_pause = 10
environment.time_scale = 1.0
environment.fps = 10
environment.vm = None
environment.ready = False
environment.basta = False
environment.test = None
environment.frame_data = None
environment.components = components
environment.resolution = resolution
environment.user_data = EasyDict()
