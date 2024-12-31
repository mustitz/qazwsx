from functools import partial

import cv2

PEN_COLOR = (255, 0, 0)
PEN_THICK = 2

def paint(img, *args):
    for arg in args:
        arg(ime=img)

def paint_rect(r, *, color, thick, img):
    x1, y1, x2, y2 = r
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thick)

def rect(r, color=PEN_COLOR, thick=PEN_THICK):
    return partial(paint_rect, r, color=color, thick=thick)
