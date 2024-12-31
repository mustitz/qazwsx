import log
from scan_codes import L_WIN, L_CTRL, ENTER, F4

from browsers.base import BaseBrowser

from timer import wait

class EdgeBrowser(BaseBrowser):
    def do_open(self):
        log.info("Edge open from Win+R dialog")
        self.vm.press_keys(L_WIN, 'r')
        wait(10)
        self.vm.press_keys('msedge.exe')
        self.vm.press_keys(ENTER)
        wait(1)

    def do_goto(self, url):
        self.vm.press_keys(url)
        self.vm.press_keys(ENTER)

    def do_close(self):
        self.vm.press_keys(L_CTRL, F4)
        wait(1)

    def check_popups(self, frame, *, autoclose=True): #pylint: disable=unused-argument
        return log.warn("TODO: not implemented check_popups for EdgeBrowser")
