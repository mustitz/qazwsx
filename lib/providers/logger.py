from enum import IntFlag
from pathlib import Path

from environment import environment
from imgrect import get_frame
from timer import age, iso_datetime
from utils import GlobalFailure

DIGITS = 5

class LogLevel(IntFlag):
    TRACE  = 1 << 0
    DEBUG  = 1 << 1
    INFO   = 1 << 2
    NOTICE = 1 << 3
    WARN   = 1 << 4
    ERR    = 1 << 5
    USER   = 1 << 10

    ALL = TRACE | DEBUG | INFO | NOTICE | WARN | ERR | USER
    FLUSH = NOTICE | WARN | ERR | USER
    STDOUT = NOTICE | WARN | ERR | USER
    NONE = 0

class Logger:
    def __init__(self, **kwargs):
        self.f = None
        self.counter = 0
        self.indent = 0
        self.stdout_mask = kwargs.pop('stdout_mask', LogLevel.STDOUT)
        self.stdout_flush_mask = kwargs.pop('stdout_flush_mask', LogLevel.STDOUT)
        self.file_mask = kwargs.pop('file_mask', LogLevel.ALL)
        self.file_flush_mask = kwargs.pop('file_flush_mask', LogLevel.FLUSH)

        if kwargs:
            sunknown = ', '.join(kwargs)
            raise ValueError(f"Unknown kwargs: {sunknown}")

    def __del__(self):
        if self.f is not None:
            self.f.close()
            self.f = None

    def _get_f(self):
        if self.f is not None:
            return self.f

        fn = Path('detailed.log')
        self.f = open(fn, 'w', encoding='utf-8') # pylint: disable=consider-using-with
        return self.f

    def _check(self, level, mask):
        return bool(level & mask)

    def _log(self, level, text):
        indentation = ' ' * (2 * self.indent)
        text = indentation + text
        self._log_stdout(level, text)
        self._log_file(level, text)

    @staticmethod
    def _get_log_line(text):
        time_stamp = age()
        if time_stamp is None:
            return text

        return f"{time_stamp:8.2f} sec - {text}"

    def _log_stdout(self, level, text):
        if not self._check(level, self.stdout_mask):
            return

        flush = self._check(level, self.stdout_flush_mask)
        text = self._get_log_line(text)
        print(text, flush=flush)

    def _log_file(self, level, text):
        if not self._check(level, self.file_mask):
            return

        f = self._get_f()
        if f is None:
            return

        flush = self._check(level, self.file_flush_mask)
        text = self._get_log_line(text)
        print(text, file=f, flush=flush)

    def trace(self, text):
        self._log(LogLevel.TRACE, text)

    def debug(self, text):
        self._log(LogLevel.DEBUG, text)

    def info(self, text):
        self._log(LogLevel.INFO, text)

    def notice(self, text):
        self._log(LogLevel.NOTICE, text)

    def warn(self, text):
        self._log(LogLevel.WARN, text)

    def error(self, text):
        self._log(LogLevel.ERR, text)

    def panic(self, text):
        self._log(LogLevel.ERR, text)
        raise GlobalFailure(text)

    def user(self, text):
        self._log(LogLevel.USER, text)

    def shift(self, delta):
        self.indent += delta

    def screenshot(self, fn, img, rect):
        if img is None:
            img = get_frame(rect=rect)
        else:
            if rect is not None:
                img = img.subrect(rect)

        fn = f"{self.counter:0{DIGITS}d}-{fn}"
        supported = ('.png', '.jpg', '.jpeg')
        if not any(fn.endswith(ext) for ext in supported):
            fn = fn + '.png'
        self.counter += 1
        img.save(fn)

def _init():
    logger = Logger()
    environment.components.logger = logger
    datetime = iso_datetime()
    logger.notice(f"Started at {datetime}")

_init()
