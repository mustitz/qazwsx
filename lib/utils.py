import re
from collections import namedtuple
from math import atan2, pi as π, sqrt
from random import gauss, shuffle


RND_STR_LEN = 8



class BadArgument(Exception):
    pass

class BreakExecution(Exception):
    pass

class GlobalFailure(Exception):
    pass

class InternalError(Exception):
    pass

def badarg(msg):
    raise BadArgument(msg)

def fail(msg):
    raise InternalError(msg)

RectTuple = namedtuple('RectTuple', ['x1', 'y1', 'x2', 'y2'])
LineTuple = namedtuple('LineTuple', ['x1', 'y1', 'x2', 'y2'])
Dialog = namedtuple('Dialog', ['caption', 'text'])

class Rect(RectTuple):
    def move(self, dx, dy):
        return Rect(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)

    @property
    def cx(self):
        return int(0.5 * (self.x1 + self.x2))

    @property
    def cy(self):
        return int(0.5 * (self.y1 + self.y2))

    @property
    def width(self):
        return abs(self.x2 - self.x1)

    @property
    def height(self):
        return abs(self.y2 - self.y1)

    @property
    def area(self):
        return self.width * self.height

    def has_point(self, x, y):
        return (self.x1 <= x <= self.x2) and (self.y1 <= y <= self.y2)

    def has_line(self, line):
        return self.has_point(line.x1, line.y1) and self.has_point(line.x2, line.y2)

    w = width
    h = height

    def scale(self, factor=0.9, *, delta=0):
        cx, cy = self.cx, self.cy
        w = self.w * factor + delta
        h = self.h * factor + delta
        x1, y1 = int(cx - 0.5 * w), int(cy - 0.5 * h)
        x2, y2 = int(x1 + w), int(y1 + w)
        if x1 >= x2:
            x1, x2 = cx, cx + 1
        if y1 >= y2:
            y1, y2 = cy, cy + 1
        return Rect(x1, y1, x2, y2)


class Line(LineTuple):
    def move(self, dx, dy):
        return Line(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)

    @property
    def dx(self):
        return abs(self.x2 - self.x1)

    @property
    def dy(self):
        return abs(self.y2 - self.y1)

    @property
    def cx(self):
        return int(0.5 * (self.x1 + self.x2))

    @property
    def cy(self):
        return int(0.5 * (self.y1 + self.y2))

    @property
    def length(self):
        dx, dy = self.dx, self.dy
        return sqrt(dx * dx + dy * dy)

    @property
    def phi(self):
        return atan2(self.dy, self.dx)

    def is_vertical(self, degree=1):
        Δφ = π * degree / 180.0
        return self.phi >= 0.5 * π - Δφ

    def is_horizontal(self, degree=1):
        Δφ = π * degree / 180.0
        return self.phi <= Δφ

def limited_gauss(mean, stddev):
    while True:
        value = gauss(mean, stddev)
        if abs(value - mean) < stddev:
            return value

def distance(x1, y1, x2, y2):
    return sqrt((x1- x2) ** 2 + (y1 - y2) ** 2)

def class_name(obj):
    return obj.__class__.__name__

def rnd_str(length=None):
    if length is None:
        length = RND_STR_LEN
    base = "0123456789qazwsxedcrfvtgbyhnujmikolp"
    as_list = list(base)
    shuffle(as_list)
    return ''.join(as_list[:length])

def split(s, sep, maxsplit):
    if not sep:
        sep = None
    parts = s.split(sep, maxsplit=maxsplit)
    while len(parts) != maxsplit + 1:
        parts.append('')
    return [ s.strip() for s in parts ]

def median(data):
    data = sorted(data)
    if not data:
        return None
    return data[len(data)//2]

def has_attrs(obj, *args):
    return all(hasattr(obj, attr) for attr in args)

def args_to_rect(*args):
    if len(args) == 4:
        return Rect(args[0], args[1], args[2], args[3])
    if len(args) == 1:
        arg = args[0]
        if isinstance(arg, Rect):
            return arg
        if has_attrs(arg, 'lx', 'rx', 'ty', 'by'):
            return Rect(arg.lx, arg.ty, arg.rx, arg.by)
    raise BadArgument("rect is a tuple or rect")

def nice(s):
    if isinstance(s, re.Pattern):
        s = s.pattern
        result = re.sub(r'[^a-zA-Z\s]', '', s)
        return ' '.join(result.split())

    if hasattr(s, 'shape'):
        cname = s.__class__.__name__
        shape = 'x'.join(map(str, s.shape))
        return f"{cname} {shape}"

    result = str(s).replace('\n', ' ').strip()
    if len(result) > 100:
        result = result[:97] + '...'
    return result
