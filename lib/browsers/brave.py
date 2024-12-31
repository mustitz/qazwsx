import log
from environment import environment
from scan_codes import L_WIN, L_CTRL, ENTER, F4
from timer import wait
from utils import Rect, Dialog

from browsers.base import BaseBrowser

class BraveBrowser(BaseBrowser):
    def do_open(self):
        log.info("Edge open from Win+R dialog")
        self.vm.press_keys(L_WIN, 'r')
        wait(10)
        self.vm.press_keys('brave.exe')
        self.vm.press_keys(ENTER)
        wait(5)

    def do_goto(self, url):
        self.vm.press_keys(url)
        self.vm.press_keys(ENTER)

    def do_close(self):
        self.vm.press_keys(L_CTRL, F4)
        wait(1)

    def check_popups(self, frame, *, autoclose=True):
        w = environment.resolution.width
        h = environment.resolution.height

        x1 = int(w - 0.2 * w)
        x2 = int(w - 1)
        y1 = int(h - 0.25 * h)
        y2 = int(h - 1)
        roi = Rect(x1, y1, x2, y2)

        ocr = frame.subrect(roi).ocr

        log.notice("OCR items:")
        for item in ocr:
            log.notice(f"  {item}")

        brave_label = ocr.match('brave').best('top')
        close_label = ocr.match('close').best('bottom')
        if brave_label is None:
            return None
        if close_label is None:
            return None

        log.notice(">>> Detected Brave popup <<<")
        log.screenshot('brave-popup', ocr.img)

        popup = Dialog('Brave', None)

        if autoclose:
            log.info("BraveBrowser.check_popups: close_label={close_label}")
            self.vm.click(close_label, style='robot')

        return popup
