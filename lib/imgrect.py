import cv2
import numpy as np

import log
from environment import environment
from utils import Rect, badarg, fail

class ImgRect:
    def __init__(self, buf, *, parent=None, rect=None):
        dim = len(buf.shape)
        if dim not in (2, 3):
            badarg(f"Invalid buf: wrong shape {buf.shape}")

        self._ocr = None
        self.buf = buf if dim == 2 else buf[:,:,:3]
        self.parent = parent

        if rect is None:
            self.rect = self.get_buf_rect()
        else:
            self.rect = rect

    def get_buf_rect(self):
        w, h, _ = self.buf_shape
        return Rect(0, 0, w, h)

    @property
    def data(self):
        x1, y1, x2, y2 = self.rect
        shape = self.buf.shape
        if len(shape) == 2:
            return self.buf[y1:y2,x1:x2]
        if len(shape) == 3:
            return self.buf[y1:y2,x1:x2,:3]
        return fail(f"Invalid shape: {shape}")

    @property
    def has_ocr(self):
        return self._ocr is not None

    def get_ocr(self):
        parent = self.parent
        if parent is not None:
            if parent.has_ocr:
                return parent.ocr.in_rect(self.rect)

        ocr_component = environment.components.ocr
        if ocr_component is None:
            return None

        return ocr_component.recognize(self, self.rect)

    @property
    def ocr(self):
        bad_ocr = 'FAILED'
        if self._ocr is not None:
            return self._ocr

        if self._ocr == bad_ocr:
            return None

        self._ocr = self.get_ocr()
        if self._ocr is None:
            log.error("Failed to get an OCR in imgrect")
            self._ocr = bad_ocr
            return None

        return self._ocr

    @property
    def buf_shape(self):
        shape = self.buf.shape
        if len(shape) == 2:
            h, w = shape
            return w, h, None
        if len(shape) == 3:
            h, w, d = shape
            return w, h, d
        return fail(f"Invalid shape: {shape}")

    @property
    def width(self):
        return self.rect.x2 - self.rect.x1

    @property
    def height(self):
        return self.rect.y2 - self.rect.y1

    def save(self, fn):
        cv2.imwrite(str(fn), self.data)

    @staticmethod
    def load(fn):
        return ImgRect(cv2.imread(str(fn)))

    def subrect(self, rect):
        parent = self if self.parent is None else self.parent
        return ImgRect(self.buf, parent=parent, rect=rect)

    def clone(self):
        x1, y1, x2, y2 = self.rect
        if len(self.buf.shape) == 2:
            region = np.copy(self.buf[y1:y2,x1:x2])
        else:
            region = np.copy(self.buf[y1:y2,x1:x2,:])

        return ImgRect(np.copy(region))

    def make_gray(self):
        if len(self.buf.shape) == 2:
            return self.clone()
        buf = self.buf[:,:,:3]
        return ImgRect(cv2.cvtColor(buf, cv2.COLOR_BGR2GRAY))

    def detect(self, objname, *args, **kwargs):
        detectors = environment.components.detectors
        if detectors is None:
            return None

        return detectors.run(objname, self, *args, **kwargs)

def get_frame(rect=None):
    return ImgRect(environment.frame_data, rect=rect)
