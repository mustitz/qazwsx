from collections import namedtuple
from math import sqrt, pi, atan2

import cv2
import numpy as np

import art
import log
from detectors import register
from testing import imdebug, istest
from utils import Rect

Point = namedtuple('Point', ['x','y'])
Cross = namedtuple('Cross', ['probability', 'rect'])
Sequence = namedtuple('Sequence', ['start', 'length'])

def coef(p1, p2):
    return p2.y - p1.y, p1.x - p2.x, (p2.x - p1.x) * p1.y + (p1.y - p2.y) * p1.x

def middle(x, y, p1, p2, p3, p4): #pylint: disable=too-many-arguments
    a1, b1, c1 = coef(p1, p2)
    a2, b2, c2 = coef(p3, p4)
    s1 = a1 * x + b1 * y + c1
    s2 = a2 * x + b2 * y + c2
    return (s1 >= 0.0) ^ (s2 >= 0.0)

def detect_cross(objname, orig_img):
    w, h = orig_img.width, orig_img.height
    log.info(f"Detect: objname={objname}; img.resolution={w}x{h};")
    imdebug('start', orig_img)

    img = orig_img.buf
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    adaptive_thresh = cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2)

    cleaned1 = adaptive_thresh
    cleaned2 = 255 - cleaned1
    imdebug('cleaned1', cleaned1)
    imdebug('cleaned2', cleaned2)

    candidates = []

    p11, p12, p21, p22 = None, None, None, None
    p31, p32, p41, p42 = None, None, None, None

    for mark, cleaned in (('org', cleaned1), ('inv', cleaned2)):
        num_labels, labels = cv2.connectedComponents(cleaned)
        for label in range(0, num_labels):
            mask = (labels == label).astype(np.uint8) * 255
            x, y, w, h = cv2.boundingRect(mask)

            if w < 5 or h < 5:
                continue

            imdebug(f'region-{mark}-{label}', mask)

            trimmed = cleaned[y:y+h, x:x+w]
            imdebug(f'trimmed-{mark}-{label}', trimmed)

            white_pixels = cv2.countNonZero(trimmed)
            k = white_pixels / trimmed.size

            kx = sqrt(w**2 + h**2) / h / 2
            ky = sqrt(w**2 + h**2) / w / 2

            a = 4 * kx * ky
            b = (-2) * (kx * h + ky * w)
            c = k * w * h
            discriminant = b * b - 4 * a * c
            if discriminant < 0.0:
                continue

            d1 = 0.5 * (-b + sqrt(discriminant)) / a
            d2 = 0.5 * (-b - sqrt(discriminant)) / a
            alts = [d for d in (d1, d2) if d > 0.0]
            alts.sort()
            if not alts:
                continue

            d = alts.pop(0)
            dx = d * sqrt(w*w+h*h) / h / 2
            dy = d * sqrt(w*w+h*h) / w / 2

            p11 = Point(0, h - dy)
            p12 = Point(w - dx, 0)
            p21 = Point(dx, h)
            p22 = Point(w, dy)

            p31 = Point(0, dy)
            p32 = Point(w - dx, h)
            p41 = Point(dx, 0)
            p42 = Point(w, h - dy)

            def is_cross(x, y):
                return middle(x, y, p11, p12, p21, p22) or middle(x, y, p31, p32, p41, p42)

            ideal = np.zeros((h, w), np.uint8)
            for xx in range(w):
                for yy in range(h):
                    cx = xx + 0.5
                    cy = yy + 0.5
                    if is_cross(cx, cy):
                        ideal[yy,xx] = 255

            imdebug(f'ideal-{mark}-{label}', ideal)

            white_mask = ideal == 255
            black_mask = ideal == 0

            qw = np.sum(white_mask)
            qb = np.sum(black_mask)

            if qw == 0 or qb == 0:
                log.debug(f"Invalid ideal: {w}x{h}; d={d};")
                continue

            qwm = np.sum(white_mask & (trimmed == 255))
            qbm = np.sum(black_mask & (trimmed == 0))

            wq, bq = qwm / qw, qbm / qb
            if wq > 0.7 and bq > 0.7:
                candidates.append(Cross(0.5 * (wq + bq), Rect(x, y, x+w, y+h)))

    if not candidates:
        return None

    candidates.sort()

    result = candidates[-1]
    log.debug(f"Find cross returns: {result}")
    imdebug('result', orig_img, art.rect(result.rect))
    return result

def find_sequences(line, minlen=50):
    result = []
    n = line.shape[0]

    i = 0
    while i < n:
        if line[i] == 255:
            start = i
            while i < n and line[i] == 255:
                i += 1
            length = i - start

            if length > minlen:
                result.append(Sequence(start, length))
        else:
            i += 1

    return result

def detect_xpanel(objname, orig_img, x, y):
    w, h = orig_img.width, orig_img.height
    log.info(f"Detect: objname={objname}; img.resolution={w}x{h}; point={(x,y)}")
    imdebug('start', orig_img)

    gray_img = orig_img.make_gray()
    imdebug('gray', gray_img)

    blurred = cv2.GaussianBlur(gray_img.buf, (9, 9), 0)
    imdebug('blurred', blurred)

    edges = cv2.Canny(blurred, 50, 150)
    imdebug('edges', edges)

    lsd = cv2.createLineSegmentDetector(0)
    lines, width, prec, nfa = lsd.detect(gray_img.buf)

    vlines, hlines = [], []
    tmp = orig_img.clone()
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        d = sqrt(dx*dx+dy*dy)
        if d < 25:
            continue
        phi = atan2(dy, dx)
        degree = pi / 180.0
        if phi < degree:
            hlines.append(line)
        if phi > 0.5 * pi - degree:
            vlines.append(line)

    VLine = namedtuple('VLine', ['cy', 'x', 'y1', 'y2', 'len'])
    HLine = namedtuple('HLine', ['cx', 'y', 'x1', 'x2', 'len'])

    def make_vline(line):
        x1, y1, x2, y2 = line[0]
        x = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        return VLine(int(cy), int(x), int(y1), int(y2), int(abs(y2-y1)))

    def make_hline(line):
        x1, y1, x2, y2 = line[0]
        cx = 0.5 * (x1 + x2)
        y = 0.5 * (y1 + y2)
        return HLine(int(cx), int(y), int(x1), int(x2), int(abs(x2-x1)))

    vlines = [ make_vline(line) for line in vlines ]
    hlines = [ make_hline(line) for line in hlines ]

    vlines.sort(key=lambda vline: vline.cy)
    hlines.sort(key=lambda hline: hline.cx)

    log.notice("Vertical:")
    for line in vlines:
        log.notice(f"  {line}")
        cv2.line(tmp.buf, (line.x, line.y1), (line.x, line.y2), (0, 0, 255), 2)

    log.notice("Horizontal:")
    for line in hlines:
        log.notice(f"  {line}")
        cv2.line(tmp.buf, (line.x1, line.y), (line.x2, line.y), (255, 0, 0), 2)

    imdebug('lsd', tmp)

    vgroups, hgroups = [], []

    Δx, Δy = 0.05 * 1920, 0.05 * 1080

    def group(lst, ismerge, **kwargs):
        lst.sort(**kwargs)
        prev = None
        result = []

        for item in lst:
            new_group = prev is None or not ismerge(prev, item)
            prev = item

            if new_group:
                current = []
                result.append(current)

            current.append(item)

        return result

    def is_same_len(prev, line):
        k = prev.len / line.len
        return k <= 1.2

    def is_big_gap(prev, vline):
        dy = abs(vline.cy - prev.cy)
        return dy > Δy

    vgroups = group(vlines, is_same_len, key=lambda vline: vline.len, reverse=True)

    log.notice("After len grouping:")
    for group in vgroups:
        for vline in group:
            log.notice(f"  {vline}")
            log.notice("--")

    vgroups = [group for group in vgroups if len(group) > 1]

    tmp = orig_img.clone()
    for group in vgroups:
        x1 = min(line.x for line in group)
        x2 = max(line.x for line in group)
        y1 = min(line.y1 for line in group)
        y2 = max(line.y2 for line in group)
        cv2.rectangle(tmp.buf, (x1, y1), (x2, y2), (0, 0, 255), 2)
    imdebug('vlines', tmp)

    """
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if istest():
        tmp = orig_img.clone()
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(tmp.buf, (x, y), (x + w, y + h), (0, 255, 0), 2)
        imdebug('contours', tmp)
    """

    """
    #lines = cv2.HoughLinesP(edges, 1, np.pi/180, 200,
    #    minLineLength=100, maxLineGap=10)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 80,
        minLineLength=30, maxLineGap=10)
    tmp = orig_img.clone()
    for line in lines:
        x1, y1, x2, y2 = line[0]
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        log.notice(f"dx={dx}; dy={dy};")
        if dx < 5 or dy < 5:
            cv2.line(tmp.buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
    imdebug('hlp', tmp)
    """

    """
    all_xsequences = []
    for xx in range(1920):
        sequences = find_sequences(edges[:,xx], minlen=50)
        sequences = [ (xx, seq) for seq in sequences ]
        if sequences:
            all_xsequences += sequences
            log.notice(f"{xx} -> {sequences}")

    all_ysequences = []
    for yy in range(1080):
        sequences = find_sequences(edges[yy,:], minlen=30)
        sequences = [ (yy, seq) for seq in sequences ]
        if sequences:
            all_ysequences += sequences
            log.notice(f"{yy} -> {sequences}")

    if istest():
        tmp = orig_img.clone()
        for xx, seq in all_xsequences:
            cv2.line(tmp.buf, (xx, seq.start), (xx, seq.start + seq.length), (255, 0, 0), 2)
        for yy, seq in all_ysequences:
            cv2.line(tmp.buf, (seq.start, yy), (seq.start + seq.length, yy), (255, 0, 0), 2)
        imdebug('vlines', tmp)
    """

def _init():
    register('cross', detect_cross)
    register('xpanel', detect_xpanel)

_init()
