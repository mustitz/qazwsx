from random import randint

from environment import environment
from utils import distance, limited_gauss

def calc_mouse_path(sx, sy, fx, fy, *, stddev=5):
    width = environment.resolution.width
    first_goal = width // 10
    max_step = width // 10

    x, y = sx, sy
    path = [(x,y)]

    tx = limited_gauss(fx, first_goal)
    ty = limited_gauss(fy, first_goal)

    i = 0
    while True:
        i += 1
        if i > 100:
            break

        td = distance(x, y, tx, ty)
        if td < first_goal:
            break

        step = min(0.5 * td, max_step)
        step = limited_gauss(step, 0.25 * step)

        p = step / td
        nx = max(0, tx * p + x * (1-p) + limited_gauss(0, stddev))
        ny = max(0, ty * p + y * (1-p) + limited_gauss(0, stddev))

        x, y = nx, ny
        path.append((x,y))

    i = 0
    while True:
        i += 1
        if i > 100:
            tx, ty = fx, fy
            break

        tx = limited_gauss(fx, stddev)
        ty = limited_gauss(fy, stddev)
        d = distance(fx, fy, tx, ty)
        if d <= stddev:
            break

    max_step = 0.3 * max_step

    i = 0
    while True:
        i += 1
        if i > 100:
            break

        td = distance(x, y, tx, ty)
        if td < stddev:
            break

        step = min(0.5 * td, max_step)
        step = limited_gauss(step, 0.3 * step)

        p = step / td
        nx = max(0, tx * p + x * (1-p) + limited_gauss(0, stddev))
        ny = max(0, ty * p + y * (1-p) + limited_gauss(0, stddev))

        x, y = nx, ny
        path.append((x,y))

    while len(path) > 13:
        ri = randint(0, len(path) - 3)
        path.pop(ri)

    path.append((tx,ty))

    tx = tx + limited_gauss(0, 0.5 * stddev)
    ty = ty + limited_gauss(0, 0.5 * stddev)
    path.append((tx,ty))

    return [(int(x), int(y)) for x, y in path]
