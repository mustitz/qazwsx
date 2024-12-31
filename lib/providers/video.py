from pathlib import Path
from threading import Thread
from time import time, sleep

import cv2
import numpy as np

from virtualbox.library import BitmapFormat

import log
from environment import environment

FOOTER_HEIGHT = 64
MSG_COLOR = (64,255,255)
MSG_FONT = 'FONT_HERSHEY_SIMPLEX'

BITMAP_FMT = BitmapFormat.bgr0
VIDEO_FPS = 25
VIDEO_FILE = 'run.mkv'

screenshots = []

class VideoLoop:
    def __init__(self):
        self.writer = None
        self.buf = None
        self.thread = None
        self.fn = Path(VIDEO_FILE).absolute()

    def _iteration(self):
        if not environment.ready:
            return None

        if environment.basta:
            return None

        vm = environment.vm
        if vm is None:
            return None

        display = vm.display
        if display is None:
            return None

        width = environment.resolution.width
        height = environment.resolution.height

        w, h, _, _, _, _ = display.get_screen_resolution(0)
        if w != width:
            self.buf[:,:,:] = 0

        if h != height:
            self.buf[:,:,:] = 0

        frame = display.take_screen_shot_to_array(0, w, h, BITMAP_FMT)
        frame = np.frombuffer(frame, dtype=np.uint8)
        frame = np.reshape(frame, (h, w, 4))
        environment.frame_data = frame

        self.buf[0:h,:,:] = frame[:,:,0:3]
        self.buf[h:,:,:] = 0

        effector = environment.components.effector
        if effector is None:
            return self.buf

        return effector.visualize(self.buf)

    def _loop(self):
        while not environment.basta:
            next_frame_time = time() + 1.0 / environment.fps

            try:
                buf = self._iteration()
            except Exception as e: #pylint: disable=broad-exception-caught
                ename = e.__class__.__name__
                log.error(f"Exception {ename}: {e}")
                self.buf[:,:,:] = 0
                buf = self.buf

            if buf is not None:
                self.writer.write(buf)

            delta = next_frame_time - time()
            if delta > 0.0:
                sleep(delta)

    def start(self):
        width = environment.resolution.width
        height = environment.resolution.height + FOOTER_HEIGHT

        shape = (width, height)
        shape3 = (height, width, 3)

        self.buf = np.zeros(shape3, dtype=np.uint8)

        fn = str(self.fn)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(fn, fourcc, VIDEO_FPS, shape)

        self.thread = Thread(target=self._loop)
        self.thread.start()

    def deinit(self):
        if self.thread is not None:
            self.thread.join()

        if self.writer is not None:
            self.writer.release()
            self.writer = None

        log.notice(f"Video saved: {self.fn}")

def _init():
    loop = VideoLoop()
    environment.components.video = loop
    loop.start()

_init()
