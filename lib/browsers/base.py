import log
from environment import environment
from utils import fail

class BaseBrowser:
    def __init__(self, name):
        self.name = name
        self.vm = environment.vm
        self.is_opened = False
        self.tname = type(self).__name__

    def do_open(self):
        fail(f"{self.tname}.do_open: Not implemented.")

    def do_close(self):
        fail(f"{self.tname}.do_close: Not implemented.")

    def do_goto(self, url):
        fail(f"{self.tname}.do_goto {url}: Not implemented.")

    def open(self):
        if self.is_opened:
            return

        log.info(f"Open browser {self.name}")
        self.do_open()
        self.is_opened = True

    def close(self):
        if not self.is_opened:
            return

        log.info(f"Close browser {self.name}")
        self.do_close()
        self.is_opened = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def goto_url(self, url):
        log.info(f"Goto URL {url} in {self.name}")
        self.do_goto(url)
