import cv2
import numpy as np

from environment import environment
from imgrect import ImgRect
from timer import age

CAPTION_COLOR = (64,255,255)
CAPTION_FONT = 'FONT_HERSHEY_SIMPLEX'

class Effector:
    def __init__(self):
        self.caption = None

    def _show_caption(self, img):
        h = img.rect.y2
        h0 = environment.resolution.height
        x = (h - h0) // 2
        y = h0 + (h - h0) // 2 + (h - h0) // 4

        if self.caption is None:
            caption = environment.script_fn
        else:
            caption = self.caption

        timestamp = age()
        msg = f"{timestamp:8.2f} sec - {caption}"
        font = getattr(cv2, CAPTION_FONT)

        cv2.putText(img.buf, msg, (x, y), font, 1.0, CAPTION_COLOR, 2)

    def visualize(self, buf):
        img = ImgRect(buf).clone()
        self._show_caption(img)
        return img.buf

def _init():
    effector = Effector()
    environment.components.effector = effector

_init()
