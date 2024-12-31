from collections import namedtuple
from random import randint

from virtualbox import VirtualBox
from virtualbox import Session

from environment import environment
from snapshots import Snapshots
from timer import age, wait, iso_datetime
from utils import badarg, fail

import effects
import human
import log

OperationStat = namedtuple('OperationStat', ['code', 'duration'])

def waitop(p):
    if p is None:
        return OperationStat(0, 0.0)

    started_at = age()
    p.wait_for_completion()
    return OperationStat(p.result_code, age() - started_at)

def longwaitop(p, title):
    if p is None:
        return 0

    log.notice(f"Operation started: {title}")
    return waitop(p)


class VBoxVm:
    def __init__(self):
        self.vbox = None
        self.session = None
        self.machine = None
        self.console = None
        self.display = None
        self.mouse_pos = (0, 0)

    @property
    def keyboard(self):
        if self.console is None:
            return None
        return self.console.keyboard

    @property
    def mouse(self):
        if self.console is None:
            return None
        return self.console.mouse

    def find_snapshot(self, name):
        snapshots = Snapshots()
        snapshots.populate(self.machine)

        qsnapshots = len(snapshots)
        log.info(f"Snapshots: {qsnapshots}")
        for snapshot in snapshots:
            log.info(f"  {snapshot.id_p}: {snapshot.name}")

        return snapshots.find(name)

    def restore_snapshot(self, snapshot):
        p = self.session.machine.restore_snapshot(snapshot)
        stat = longwaitop(p, f'restore snapshot {snapshot.name} {snapshot.id_p}')
        if stat.code != 0:
            log.panic(f"  Failed: {stat.code}")

        log.notice(f"  OK in {stat.duration:.1f} sec")

    def take_snapshot(self, name):
        session = self.session
        if session is None:
            return

        machine = session.machine
        if machine is None:
            return

        snapshots = Snapshots()
        snapshots.populate(self.machine)
        name = snapshots.next_name(name)
        timestamp = iso_datetime()
        description = f"Last execution, saved at {timestamp}."
        p, guid = machine.take_snapshot(name, description, True)
        stat = longwaitop(p, "taking snapshot")
        if stat.code != 0:
            log.error(f"  Failed: {stat.code}")
            return

        sargs = '; '.join((
            f'name={name}',
            f'guid={guid}',
            f'duration={stat.duration:.1f} sec',
            ))

        log.notice(f"  Snapshot has been taken: {sargs};")

    def set_resolution(self, max_tries=50):
        width = environment.resolution.width
        height = environment.resolution.height
        bpp = environment.resolution.bpp

        qtries = 0
        while True:
            w, h, _, _, _, _ = self.display.get_screen_resolution(0)
            if w == width and h == height:
                if qtries == 0:
                    log.info(f"Needed resolution {width}x{height} already set")
                else:
                    log.info(f"New resolution  {width}x{height} was successfully set")
                break

            log.trace(f"The current resolution is {w}x{h}")

            log.trace(f"Try to change resolution to {width}x{height}")
            self.display.set_video_mode_hint(0,
                enabled=True, change_origin=False,
                origin_x=0, origin_y=0,
                width=width, height=height, bits_per_pixel=bpp,
                notify=True)

            wait(1, β=None)
            w, h, _, _, _, _ = self.display.get_screen_resolution(0)
            if w == width and h == height:
                log.info(f"New resolution {w}x{h} was successfully set")
                return

            qtries += 1
            if qtries > max_tries:
                log.panic("Failed to change resolution")

        log.notice(f"Resolution: {width}x{height}")

    def power_on(self):
        self.session.unlock_machine()
        p = self.machine.launch_vm_process(self.session, 'headless', [])
        stat = longwaitop(p, 'launch VM')
        if stat.code != 0:
            log.error(f"  Failed: {stat.code}")
            return

        log.notice(f"  OK in {stat.duration:.1f} sec")

    def power_down(self):
        console = self.console
        if console is None:
            return

        wait(1, β=None)
        p = console.power_down()
        stat = longwaitop(p, 'power off')

        if stat.code != 0:
            log.error(f"  Failed: {stat.code}")
            return

        log.notice(f"  OK in {stat.duration:.1f} sec")

    def press_keys(self, *args):
        scancodes_down = []
        text = None

        for arg in args:
            if isinstance(arg, list):
                if text is not None:
                    badarg('Invalid args: list after str')
                for item in arg:
                    if not isinstance(item, int):
                        badarg('Invalid args: wrong scancode list')
                    scancodes_down.append(item)
                continue

            if isinstance(arg, int):
                if text is not None:
                    badarg('Invalid args: int after str')
                scancodes_down.append(arg)
                continue

            if isinstance(arg, str):
                if text is not None:
                    badarg('Invalid args: too many str')
                text = arg
                continue

            badarg('Invalid args: unexpected type')

        if scancodes_down:
            scancodes_down = list(scancodes_down)
            scancodes_up = [0x80 | code for code in scancodes_down]
            log.trace(f"keyboard.put_scancodes {scancodes_down}")
            self.keyboard.put_scancodes(scancodes_down)
            wait(0.1)

        if text:
            log.trace(f"keyboard.put_keys {text}")
            self.keyboard.put_keys(text)
            wait(0.1)

        if scancodes_down:
            log.trace(f"keyboard.put_scancodes {scancodes_up}")
            self.keyboard.put_scancodes(scancodes_up)

    @staticmethod
    def get_mouse_click_mask(button):
        if button is None:
            return 0x01
        if button == 'left':
            return 0x01
        if button == 'skip':
            return 0
        return None

    def put_mouse_event(self, x, y, mask):
        log.trace(f"mouse.put_mouse_event_absolute {x} {y} 0 0 0x{mask:02x}")
        self.mouse.put_mouse_event_absolute(x, y, 0, 0, mask)
        self.mouse_pos = (x, y)

    def mouse_click_robot(self, x, y, button=None, *, downtime=0.1):
        mask = self.get_mouse_click_mask(button)
        if mask is None:
            log.error(f"Unknown mouse button {button}")
            return

        effects.mouse_click(x, y)

        if mask != 0:
            self.put_mouse_event(x, y, mask)
            wait(downtime)

        self.put_mouse_event(x, y, 0x00)

    #pylint: disable=too-many-arguments
    def mouse_click_human(self, x, y, button=None, *, speed=1.0, downtime=0.04, max_path=None):
        if button is None:
            button = 'left'

        mx, my = self.mouse_pos
        path = human.calc_mouse_path(mx, my, x, y)
        lx, ly = path.pop()
        px, py = path.pop()

        if max_path is not None:
            while len(path) > max_path:
                i = randint(1, len(path))
                path.pop(i)

        for xx, yy in path:
            self.put_mouse_event(xx, yy, 0x00)
            wait(0.005 * speed)

        mask = self.get_mouse_click_mask(button)
        if mask is None:
            log.error(f"Unknown mouse button {button}")
            return

        effects.mouse_click(lx, ly)

        if mask != 0:
            self.put_mouse_event(lx, ly, 0x01)
            wait(speed * downtime)

        self.put_mouse_event(px, py, 0x00)

    def mouse_click(self, x, y, button=None, *, style=None, **kwargs):
        if style == 'robot':
            return self.mouse_click_robot(x, y, button, **kwargs)

        if style is None or style == 'human':
            return self.mouse_click_human(x, y, button, **kwargs)

        return fail(f"Unsupported mouse_click_style: {style}")

    def go(self):
        machine_name = environment.machine_name
        snapshot_name = environment.snapshot_name

        self.vbox = VirtualBox()
        self.session = Session()
        self.machine = self.vbox.find_machine(machine_name)

        snapshot = self.find_snapshot(snapshot_name)
        if snapshot is None:
            log.panic(f"Cannot find snapshot: {snapshot_name}")

        self.machine.create_session(session=self.session)
        self.restore_snapshot(snapshot)
        self.power_on()

        self.console = self.session.console
        self.display = self.console.display
        self.set_resolution()

    def deinit(self, was_exception):
        snapshot_name = environment.snapshot_name
        if not was_exception:
            self.take_snapshot(snapshot_name)
        else:
            log.notice("Skip snapshot due to exception.")

        self.power_down()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            log.notice("Deinit VM")
            self.deinit(False)
        else:
            log.error(f"Deinit VM after failure: {exc_type} {exc_value} {traceback}")
            self.deinit(True)

def create():
    return VBoxVm()
