from datetime import datetime
from functools import wraps
from random import gauss
from time import time, sleep

from environment import environment

class NotReadyException(Exception):
    pass

def age():
    started_at = environment.started_at
    if started_at is None:
        return None
    return time() - started_at

def iso_datetime():
    return datetime.now().isoformat()

def wait(delay, *, β=0.1):
    if delay <= 0.0:
        return

    if β is not None and β > 0.0:
        σ = 0.333333333 * 0.5 * β * delay
        random_delay = gauss(delay, σ) + 3.0 * σ
        delay = max(delay, random_delay)
        delay = min((1.0 + β) * delay, random_delay)

    sleep(environment.time_scale * delay)

def not_ready(msg):
    raise NotReadyException(msg)

def repeat(timeout, delay):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_call = age() + timeout
            self = args[0] if args else None
            has_qtries = hasattr(self, 'qtries')
            if has_qtries:
                self.qtries = 0
            while True:
                try:
                    if has_qtries:
                        self.qtries += 1
                    return func(*args, **kwargs)
                except NotReadyException as e:
                    if age() >= last_call:
                        raise e
                wait(delay, β=None)
        return wrapper
    return decorator
