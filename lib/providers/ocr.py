import re
from collections import namedtuple
from pathlib import Path

import numpy as np
from requests import get as http_request

import log
from environment import environment
from timer import age
from utils import badarg, Rect


OCR_SERVER_URL = 'http://localhost:1914/test'


TEXT_KEYS = {
    'x': lambda t: t.x,
    'y': lambda t: t.y,
    'left': lambda t: t.lx,
    'right': lambda t: t.rx,
    'top': lambda t: t.ty,
    'bottom': lambda t: t.by,
    'height': lambda t: t.by - t.ty,
    'width': lambda t: t.rx - t.lx,
}

def to_lambda(key):
    if isinstance(key, str):
        key = TEXT_KEYS.get(key)
        if key is None:
            badarg(f"Unknown sort mode key: {key}")
    if not callable(key):
        badarg("Sort key is not a callable")
    return key

OcrItemTuple = namedtuple('OcrItemTuple', ['rect', 'text', 'probability', 'bbox'])

class OcrItem(OcrItemTuple):
    @property
    def width(self):
        return self.rect.x2 - self.rect.x1

    @property
    def height(self):
        return self.rect.x2 - self.rect.x1

    @property
    def x(self):
        return sum(elem[0] for elem in self.bbox) // 4

    @property
    def y(self):
        return sum(elem[1] for elem in self.bbox) // 4


class OcrClient():
    def __init__(self):
        self.qrequests = 0

    def make_fn(self):
        dn = Path('ocr').absolute()
        dn.mkdir(parents=True, exist_ok=True)

        fname = f"{self.qrequests:04d}.npy"
        fn = dn / fname
        self.qrequests += 1
        return fn

    def recognize(self, img, rect, *, lang=None, timeout=60):
        fn = self.make_fn()
        img = img.subrect(rect)
        np.save(fn, img.data)
        w, h = img.width, img.height
        log.info(f"ocr.recognize: shape={w}x{h}; rect={rect}; num={self.qrequests};")

        url = OCR_SERVER_URL
        params = { 'fn': str(fn) }
        if lang:
            params['lang'] = lang

        try:
            start = age()
            response = http_request(url, params, timeout=timeout)
            duration = age() - start
            log.info(f"OCR request for image {w}x{h} finished in {duration:.2f} sec for {params}")
        except Exception as e: #pylint: disable=broad-exception-caught
            ename = e.__class__.__name__
            log.error(f"Exception {ename} during OCR HTTP request: {e}")
            return None

        if response.status_code != 200:
            log.error(f"HTTP request failed: {url} with {params}")
            return None

        try:
            answer = response.json()
        except ValueError:
            log.error("OCR response is not in JSON format")
            return None

        if answer.get('status') != 'OK':
            log.error(f"OCR server log.error: {answer}")
            return None

        raw = []
        try:
            for item in answer.get('texts', []):
                raw.append(eval(item)) #pylint: disable=eval-used
        except Exception: #pylint: disable=broad-exception-caught
            log.error(f"Invalid answer: {answer}")

        return ImgOcr(img, raw, rect.x1, rect.y1)


class ImgOcr:
    def __init__(self, img, raw, dx=0, dy=0):
        self.img = img
        self.raw = raw
        self.items = [ make_ocr_item(t, dx, dy) for t in raw ]

    def __iter__(self):
        return iter(self.items)

    @property
    def count(self):
        return len(self.items)

    def create_empty(self):
        return ImgOcr(self.img, [])

    def filter(self, cond):
        result = self.create_empty()
        for t, item in zip(self.raw, self.items):
            if cond(item):
                result.raw.append(t)
                result.items.append(item)
        return result

    def sort(self, key, reverse=False):
        result = self.create_empty()
        if self.count == 0:
            return result

        item_key = to_lambda(key)
        pairs = zip(self.items, self.raw)
        pairs = sorted(pairs, key=lambda t: item_key(t[0]), reverse=reverse)
        result.items, result.raw = zip(*pairs)
        return result

    def best(self, key, reverse=False):
        result = self.sort(key, reverse)
        if result.count == 0:
            return None
        return result.items[0]

    def _match_regexp(self, pattern):
        return self.filter(lambda item: bool(pattern.match(item.text)))

    def _match_icase(self, text):
        text = text.lower()
        return self.filter(lambda item: item.text.lower() == text)

    def match(self, m):
        if isinstance(m, re.Pattern):
            return self._match_regexp(m)
        return self._match_icase(str(m))

    def in_rect(self, rect):
        if rect is None:
            return self.create_empty()

        x1, y1, x2, y2 = rect
        return self.filter(lambda item: (x1 <= item.x <= x2) and (y1 <= item.y <= y2))


def make_ocr_item(t, dx, dy):
    bbox, text, probability = t
    tl, tr, br, bl = bbox
    x1 = dx + int(min(tl[0], tr[0], br[0], bl[0]))
    x2 = dx + int(max(tl[0], tr[0], br[0], bl[0]))
    y1 = dy + int(min(tl[1], tr[1], br[1], bl[1]))
    y2 = dy + int(max(tl[1], tr[1], br[1], bl[1]))
    return OcrItem(Rect(x1, y1, x2, y2), text, probability, bbox)


def _init():
    ocr = OcrClient()
    environment.components.ocr = ocr

_init()
