from collections import namedtuple
from statistics import mean

import cv2

import log
from detectors import register
from testing import istest, imdebug
from timer import age
from utils import Line, Rect, fail, nice

def detect_lines(img, minlength=10):
    gray_img = img.make_gray()
    imdebug('gray', gray_img)

    lsd = cv2.createLineSegmentDetector(0)
    lines, *tail = lsd.detect(gray_img.buf)

    qlines = len(lines)
    swidth, sprec, snfa = [ nice(item) for item in tail ]
    log.info(f"las.detect returns {qlines} lines: width={swidth}; prec={sprec}; nfa={snfa};")

    result = []
    for line_data in lines:
        coords = [ int(coord) for coord in line_data[0] ]
        line = Line(*coords)
        if line.length >= minlength:
            result.append(Line(*coords))

    if istest():
        buf = img.clone().buf
        for line in result:
            x1, y1, x2, y2 = line
            cv2.line(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
        imdebug(f'lines-minlength-{minlength}', buf)

    return result

def detect_hv_lines(img, minlength=10):
    lines = detect_lines(img, minlength=minlength)
    hlines = [ line for line in lines if line.is_horizontal() ]
    vlines = [ line for line in lines if line.is_vertical() ]

    if istest():
        buf = img.clone().buf
        for line in vlines:
            x1, y1, x2, y2 = line
            cv2.line(buf, (x1, y1), (x2, y2), (0, 255, 0), 2)
        imdebug(f'vlines-minlength-{minlength}', buf)

        buf = img.clone().buf
        for line in hlines:
            x1, y1, x2, y2 = line
            cv2.line(buf, (x1, y1), (x2, y2), (0, 0, 255), 2)
        imdebug(f'hlines-minlength-{minlength}', buf)

    return hlines, vlines

class Group(list):
    @property
    def length(self):
        return len(self)

    def minx(self, lines):
        return min(
            min(lines[i].x1 for i in self),
            min(lines[i].x2 for i in self),
            )

    def maxx(self, lines):
        return max(
            max(lines[i].x1 for i in self),
            max(lines[i].x2 for i in self),
            )

    def miny(self, lines):
        return min(
            min(lines[i].y1 for i in self),
            min(lines[i].y2 for i in self),
            )

    def maxy(self, lines):
        return max(
            max(lines[i].y1 for i in self),
            max(lines[i].y2 for i in self),
            )

    def rect(self, lines):
        x1, y1 = self.minx(lines), self.miny(lines)
        x2, y2 = self.maxx(lines), self.maxy(lines)
        return Rect(x1, y1, x2, y2)

    def split(self, index):
        return (Group(self[:index]), Group(self[index:]))


def group_lines(lines, axis, *, maxlinediff, mingap):
    qlines = len(lines)
    lines.sort(key=lambda line: line.length)
    indexes = list(range(qlines))

    if axis == 'x':
        def center(line):
            return 0.5 * (line.x1 + line.x2)
        def position(line):
            return 0.5 * (line.y1 + line.y2)

    elif axis == 'y':
        def center(line):
            return 0.5 * (line.y1 + line.y2)
        def position(line):
            return 0.5 * (line.x1 + line.x2)

    else:
        fail("Wrong axis")

    for i in range(0, qlines-1):
        for j in range(i+1, qlines):
            iline = lines[i]
            jline = lines[j]
            Δ = abs(iline.length - jline.length)
            m = int(0.5 * (iline.length + jline.length))
            if Δ / m > maxlinediff:
                continue

            ci, cj = center(iline), center(jline)
            offset = abs(cj - ci)
            if offset / m > maxlinediff:
                continue

            log.info(f"Join {i}, {j}: {iline}, {jline}")
            joint_index = min(indexes[i], indexes[j])
            indexes[i] = joint_index
            indexes[j] = joint_index

    groups = [ Group() for _ in indexes ]
    for i, joint_index in enumerate(indexes):
        groups[joint_index].append(i)

    groups = [ g for g in groups if len(g) > 1 ]

    result = []

    for g in groups:
        g.sort(key=lambda i: position(lines[i]))

        while True:
            if len(g) <= 3:
                result.append(g)
                break

            last_pos, first_group = None, None
            log.notice(f"Groups! {g}")
            qgaps = 0
            for j, i in enumerate(g):
                line = lines[i]
                pos = position(line)
                isgap = last_pos is None or (pos - last_pos > mingap)
                if isgap:
                    qgaps += 1
                if qgaps == 3:
                    first_group = j
                last_pos = pos
                log.info(f"  view {i}: {line} {pos} {isgap}")
                if qgaps >= 4:
                    log.info("  many gaps, splitting")
                    break

            if qgaps < 3:
                result.append(g)
                break

            separated, g = g.split(first_group)
            result.append(separated)

    return result

ILine = namedtuple('ILine', ['index', 'typ', 'line'])

MIN_DX = 5
MIN_DY = 5

class PanelLine:
    def __init__(self, x1, y1, x2, y2, *,
            panel=None,
            index=None,
            ): #pylint: disable=too-many-arguments
        self.panel = panel
        self.index = index

        dx = abs(x2 - x1)
        dy = abs(y1 - y1)
        is_horizontal = dx >= dy
        if is_horizontal:
            self.typ = 'H'
            if x1 > x2:
                x1, y1, x2, y2 = x2, y2, x1, y1
        else:
            self.typ = 'V'
            if y1 > y2:
                x1, y1, x2, y2 = x2, y2, x1, y1

        self.coords = Line(x1, y1, x2, y2)

    def is_vertical(self, *args, **kwargs):
        return self.coords.is_vertical(*args, **kwargs)

    def is_horizontal(self, *args, **kwargs):
        return self.coords.is_horizontal(*args, **kwargs)

    def dump(self):
        scoord = None
        x1, y1, x2, y2 = self.coords

        if self.typ == 'H':
            sdy = ''
            dy = y2 - y1
            if dy != 0:
                sign = '+' if dy > 0 else '-'
                dy = abs(dy)
                sdy = f' ({sign}{dy})'

            scoord = f"H {x1} - {x2}: {y1}{sdy}"

        if self.typ == 'V':
            sdx = ''
            dx = x2 - x1
            if dx != 0:
                sign = '+' if dx > 0 else '-'
                dx = abs(dx)
                sdx = f' ({sign}{dx})'

            scoord = f"V {y1} - {y2}: {x1}{sdx}"

        if scoord is None:
            fail(f"Invalid self.typ: {self.typ}")

        return scoord


class LinePair:
    def __init__(self, pl1, pl2):
        self.pl1 = pl1
        self.pl2 = pl2
        self.scores = []
        self.key = None

    @property
    def average_len(self):
        line1, line2 = self.pl1.coords, self.pl2.coords
        return int(0.5 * (line1.length + line2.length))

    def dump(self):
        sscores = ', '.join(f'{score:.2f}' for score in self.scores)
        return f'{self.score:.1f} : {sscores} - {self.key} {self.pl1.index}/{self.pl2.index}'

    @property
    def score(self):
        return mean(self.scores)


class Panel:
    def __init__(self, detector, rect):
        self.detector = detector
        self.rect = rect
        self.children = []
        self.hlines = []
        self.vlines = []
        self.hpairs = []
        self.vpairs = []

    def load_lines(self, hlines, vlines):
        self.hlines = list(hlines)
        self.vlines = list(vlines)

    def new_child(self, x1, y1, x2, y2, *, used=None): #pylint: disable=too-many-arguments
        detector = self.detector
        used = used or []

        minlength = detector.minlength
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        if abs(x2 - x1) < minlength:
            return 0
        if abs(y2 - y1) < minlength:
            return 0

        child_rect = Rect(x1, y1, x2, y2)
        if child_rect == self.rect:
            return 0

        def is_inner_line(pl):
            if not child_rect.has_line(pl.coords):
                return False
            if pl.index in used:
                return False
            return True

        child = Panel(detector, child_rect)
        child.hlines = [ pl for pl in self.hlines if is_inner_line(pl) ]
        child.vlines = [ pl for pl in self.vlines if is_inner_line(pl) ]
        qh, qv = len(child.hlines), len(child.vlines)
        log.notice(f"New child: {(x1, y1)} - {(x2, y2)}, {qh} hlines, {qv} vlines.")

        if istest():
            img = detector.orig_img

            buf = img.subrect(child_rect).clone().buf
            imdebug('panel', buf)

            for pl in child.hlines:
                x1, y1, x2, y2 = pl.coords.move(-child_rect.x1, -child_rect.y1)
                cv2.line(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)

            for pl in child.vlines:
                x1, y1, x2, y2 = pl.coords.move(-child_rect.x1, -child_rect.y1)
                cv2.line(buf, (x1, y1), (x2, y2), (0, 0, 255), 2)

            imdebug('panel-lines', buf)

            buf = img.clone().buf
            x1, y1, x2, y2 = child_rect
            cv2.rectangle(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
            imdebug('panel-rect', buf)

        self.children.append(child)
        detector.stack.add(child)
        return 1

    def try_hsplit(self):
        minwidth = int(self.detector.mincommonlen * self.rect.width)
        minlength = self.detector.minlength

        def ishr(pl):
            line = pl.coords
            if line.length < minwidth:
                return False
            delta = self.rect.width - line.length
            if delta > minlength:
                return False
            return True

        candidates = [ pl for pl in self.hlines if ishr(pl) ]
        if not candidates:
            log.notice("No candidates for horizontal splits")
            return 0

        candidates.sort(key=lambda pl: pl.coords.cy)

        log.notice("Horizontal splits candidates:")
        log.shift(+1)
        try:
            for pl in candidates:
                log.notice(pl.dump())
        finally:
            log.shift(-1)

        qchildren = 0
        used = set(pl.index for pl in candidates)
        y = self.rect.y1
        for pl in candidates:
            x1, x2 = self.rect.x1, self.rect.x2
            y1, y2 = y, pl.coords.cy
            y = y2

            if abs(y2 - y1) < self.detector.minlength:
                continue

            qchildren += self.new_child(x1, y1, x2, y2, used=used)

        qchildren += self.new_child(x1,  y, x2, self.rect.y2, used=used)

        log.notice(f"Found {qchildren} children")
        return qchildren

    def generate_pairs(self, lines):
        result = []
        qlines = len(lines)

        for i in range(0, qlines-1):
            pl1 = lines[i]
            line1 = pl1.coords
            for j in range(i+1, qlines):
                pl2 = lines[j]
                line2 = pl2.coords

                if self.detector.is_interesting_pair(line1, line2):
                    result.append(LinePair(pl1, pl2))

        return result

    @staticmethod
    def update_pair_score(pairs, reverse, max_score=10.0):
        pairs.sort(key=lambda pair: pair.key, reverse=reverse)
        qpairs = len(pairs)
        if qpairs == 0:
            return
        if qpairs == 0:
            pairs[0].score = max_score
            return

        score = max_score
        step = max_score / qpairs
        last_key = pairs[0].key
        skipped = 0
        for pair in pairs:
            if pair.key != last_key:
                score -= step * skipped
                skipped = 1
            else:
                skipped += 1
            pair.scores.append(score)
            last_key = pair.key

    def estimate_pair_length(self, pairs):
        for pair in pairs:
            pair.key = pair.average_len
        self.update_pair_score(pairs, reverse=True)

    def estimate_pair_hshift(self, pairs):
        for pair in pairs:
            pair.key = 0.5 * (pair.pl1.coords.x1 + pair.pl1.coords.x2)
        self.update_pair_score(pairs, reverse=True)

    def robust_best_hpair(self):
        detector = self.detector
        lines = self.hlines
        candidates = []
        qlines = len(lines)
        for i in range(0, qlines-1):
            line1 = lines[i].line
            for j in range(i+1, qlines):
                line2 = lines[j].line
                k = detector.estimate_hline_pair(line1, line2)
                l = int(max(line1.length, line2.length))
                if k > 0.01:
                    candidates.append((i, j, int(100*k), l))

        candidates.sort(key=lambda t: (t[2], t[3]), reverse=True)

        log.notice("H-Line pairs:")
        log.shift(+1)
        try:
            for i, j, k, l in candidates:
                sindex = f"{i}/{j}"
                line1 = lines[i]
                line2 = lines[j]
                log.notice(f"{sindex:8s} {k:3d}% {line1} {line2} len={l}")

                buf = detector.orig_img.clone().buf
                x1, y1, x2, y2 = line1.line
                cv2.line(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
                x1, y1, x2, y2 = line2.line
                cv2.line(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
                imdebug(f'{i}-{j}', buf)

        finally:
            log.shift(-1)

        return candidates

    def find_children(self):
        log.notice(f"Find children in rect: {self.rect}")

        if self.try_hsplit() > 0:
            return

        # SKIPED try_vsplit

        qh, qv = len(self.hlines), len(self.vlines)
        log.notice(f"Panel {self.rect}: {qh} hlines {qv} vlines")

        self.hpairs = self.generate_pairs(self.hlines)
        self.vpairs = self.generate_pairs(self.vlines)
        log.notice(f"len(hpairs) = {len(self.hpairs)}")
        log.notice(f"len(vpairs) = {len(self.vpairs)}")

        self.estimate_pair_length(self.hpairs)
        self.estimate_pair_hshift(self.hpairs)

        log.notice("H-pairs:")
        log.shift(+1)
        try:
            for pair in self.hpairs:
                log.notice(pair.dump())
        finally:
            log.shift(-1)

        #self.robust_best_hpair()
        #log.notice("Not implemented yet find_children")


class PanelDetector:#pylint: disable=too-many-instance-attributes
    def __init__(self, objname, orig_img, *,
            minlength=24,
            mincommonlen=0.9,
            ): #pylint: disable=too-many-arguments

        self.objname = objname
        self.orig_img = orig_img
        self.minlength = minlength
        self.mincommonlen = mincommonlen

        self.root = Panel(self, orig_img.rect)
        self.stack = { self.root }
        self.hlines = []
        self.vlines = []

    def clone_img_buf(self):
        return self.orig_img.clone().buf

    def log_lines(self, title, name, panel_lines, color):
        log.info(title)
        log.shift(+1)
        try:
            buf = self.clone_img_buf()
            for pl in panel_lines:
                x1, y1, x2, y2 = pl.coords
                cv2.line(buf, (x1, y1), (x2, y2), color, 2)
                log.info(pl.dump())
            imdebug(f'{name}-minlength-{self.minlength}', buf)
        finally:
            log.shift(-1)

    def detect_hv_lines(self):
        lines = detect_lines(self.orig_img, minlength=self.minlength)
        hlines = [ line for line in lines if line.is_horizontal() ]
        vlines = [ line for line in lines if line.is_vertical() ]

        self.hlines = []
        for i, hline in enumerate(hlines):
            pl = PanelLine(*hline, panel=self.root, index=i)
            self.hlines.append(pl)

        self.vlines = []
        for i, vline in enumerate(vlines):
            pl = PanelLine(*vline, panel=self.root, index=i)
            self.vlines.append(pl)

        if istest():
            self.log_lines("H-Lines:", 'hlines', self.hlines, (0, 0, 255))
            self.log_lines("V-Lines:", 'vlines', self.vlines, (0, 255, 0))

    def is_interesting_pair(self, line1, line2):
        minlen = min(line1.length, line2.length)
        maxlen = max(line1.length, line2.length)
        k = minlen / maxlen
        if k < self.mincommonlen:
            return False

        k = 1.0 - abs(line1.cx - line2.cx) / maxlen
        if k < self.mincommonlen:
            return False

        return True

    def estimate_hline_pair(self, line1, line2):
        minlen = min(line1.length, line2.length)
        maxlen = max(line1.length, line2.length)
        k1 = minlen / maxlen
        if k1 < self.mincommonlen:
            return 0
        k2 = 1.0 - abs(line1.cx - line2.cx) / maxlen
        if k2 < self.mincommonlen:
            return 0
        return 0.5 * (k1 + k2)

    def estimate_vline_pair(self, line1, line2):
        minlen = min(line1.length, line2.length)
        maxlen = max(line1.length, line2.length)
        k1 = minlen / maxlen
        if k1 < self.mincommonlen:
            return 0
        k2 = 1.0 - abs(line1.cy - line2.cy) / maxlen
        if k2 < self.mincommonlen:
            return 0
        return 0.5 * (k1 + k2)

    def robust_best_hpair(self):
        lines = self.hlines
        candidates = []
        qlines = len(lines)
        for i in range(0, qlines-1):
            line1 = lines[i]
            for j in range(i+1, qlines):
                line2 = lines[j]
                k = self.estimate_hline_pair(line1, line2)
                l = int(max(line1.length, line2.length))
                if k > 0.01:
                    candidates.append((i, j, int(100*k), l))

        candidates.sort(key=lambda t: (t[2], t[3]), reverse=True)

        log.notice("H-Line pairs:")
        log.shift(+1)
        try:
            for i, j, k, l in candidates:
                sindex = f"{i}/{j}"
                line1 = lines[i]
                line2 = lines[j]
                log.notice(f"{sindex:8s} {k:3d}% {line1} {line2} len={l}")
        finally:
            log.shift(-1)

        return candidates

    def robust_best_vpair(self):
        lines = self.vlines
        candidates = []
        qlines = len(lines)
        for i in range(0, qlines-1):
            line1 = lines[i]
            for j in range(i+1, qlines):
                line2 = lines[j]
                k = self.estimate_vline_pair(line1, line2)
                l = int(max(line1.length, line2.length))
                if k > 0.01:
                    candidates.append((i, j, int(100*k), l))

        candidates.sort(key=lambda t: (t[2], t[3]), reverse=True)

        log.notice("V-Line pairs:")
        log.shift(+1)
        try:
            for i, j, k, l in candidates:
                sindex = f"{i}/{j}"
                line1 = lines[i]
                line2 = lines[j]
                log.notice(f"{sindex:8s} {k:3d}% {line1} {line2} len={l}")
        finally:
            log.shift(-1)

        return candidates

    def run(self):
        w, h = self.orig_img.width, self.orig_img.height
        log.info(f"Detect: objname={self.objname}; img.resolution={w}x{h};")
        imdebug('start', self.orig_img)

        start_at = age()
        self.detect_hv_lines()
        qhlines, qvlines = len(self.hlines), len(self.vlines)
        duration = age() - start_at
        log.info(f"Found {qhlines} horizontal and {qvlines} vertial lines in {duration:.02f} sec")

        self.root.load_lines(self.hlines, self.vlines)
        self.stack = { self.root }

        while len(self.stack) > 0:
            panel = self.stack.pop()
            panel.find_children()

        # hpairs = self.robust_best_hpair()
        # vpairs = self.robust_best_vpair()
        # log.notice(f"{len(hpairs)} hpairs and {len(vpairs)} vpairs")

def detect_panels(objname, orig_img, **kwargs):
    detector = PanelDetector(objname, orig_img, **kwargs)
    return detector.run()

def detect_panels2(objname, orig_img, *, maxlinediff=0.1, minheight=24, mingap=5):
    w, h = orig_img.width, orig_img.height
    log.info(f"Detect: objname={objname}; img.resolution={w}x{h};")
    imdebug('start', orig_img)

    start_at = age()
    hlines, vlines = detect_hv_lines(orig_img)
    qhlines, qvlines = len(hlines), len(vlines)
    duration = age() - start_at
    log.info(f"Found {qhlines} horizontal and {qvlines} vertial lines in {duration:.02f} sec")

    started_at = age()
    hgroups = group_lines(hlines, 'x', maxlinediff=maxlinediff, mingap=mingap)
    vgroups = group_lines(vlines, 'y', maxlinediff=maxlinediff, mingap=mingap)
    duration = age() - started_at
    log.notice(f"Grouping HV lines in {duration:.02f} sec")

    if istest():
        for group in hgroups:
            buf = orig_img.clone().buf
            indexes = '-'.join(map(str, group))
            rect = group.rect(hlines)
            if rect.height < minheight:
                continue

            x1, y1, x2, y2 = rect
            cv2.rectangle(buf, (x1, y1), (x2, y2), (255, 0, 0), 2)
            imdebug(f'hgroup-{indexes}', buf)

        for group in vgroups:
            buf = orig_img.clone().buf
            indexes = '-'.join(map(str, group))
            rect = group.rect(vlines)
            if rect.height < minheight:
                continue

            x1, y1, x2, y2 = rect
            cv2.rectangle(buf, (x1, y1), (x2, y2), (0, 255, 0), 2)
            imdebug(f'vgroup-{indexes}', buf)

    log.notice(f"H-Groups: {len(hgroups)}")
    log.notice(f"V-Groups: {len(vgroups)}")

    qpanels, panel_rects = 0, []
    for i, hgroup in enumerate(hgroups):
        for j, vgroup in enumerate(vgroups):
            if vgroup is None:
                continue

            ri = hgroup.rect(hlines)
            rj = vgroup.rect(vlines)

            x1 = max(ri.x1, rj.x1)
            y1 = max(ri.y1, rj.y1)
            x2 = min(ri.x2, rj.x2)
            y2 = min(ri.y2, rj.y2)
            if x1 >= x2:
                continue
            if y1 >= y2:
                continue

            inner = Rect(x1, y1, x2, y2)

            x1 = min(ri.x1, rj.x1)
            y1 = min(ri.y1, rj.y1)
            x2 = max(ri.x2, rj.x2)
            y2 = max(ri.y2, rj.y2)
            outer = Rect(x1, y1, x2, y2)

            k = inner.area / outer.area
            if k < 0.3:
                continue

            qpanels += 1
            log.notice(f"Find panel #{qpanels}: {outer} k = {k:.03f}")
            hgroups[i] = None
            vgroups[j] = None
            panel_rects.append(outer)

    if istest():
        buf = orig_img.clone().buf
        for rect in panel_rects:
            x1, y1, x2, y2 = rect
            cv2.rectangle(buf, (x1, y1), (x2, y2), (0, 0, 255), 2)
        imdebug(f'panels-{qpanels}', buf)


def _init():
    register('panels', detect_panels)

_init()
