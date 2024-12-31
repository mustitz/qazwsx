from environment import environment

def _logger():
    return environment.components.logger

def trace(text):
    _logger().trace(text)

def debug(text):
    _logger().debug(text)

def info(text):
    _logger().info(text)

def notice(text):
    _logger().notice(text)

def warn(text):
    _logger().warn(text)

def error(text):
    _logger().error(text)

def panic(text):
    _logger().panic(text)

def user(text):
    _logger().user(text)

def shift(delta):
    _logger().shift(delta)

def screenshot(fn, img=None, *, rect=None):
    logger = environment.components.logger
    if logger is None:
        return

    logger.screenshot(fn, img, rect)
