from browsers.base import BaseBrowser
from browsers.edge import EdgeBrowser
from browsers.brave import BraveBrowser

def open_browser(name):
    if name == 'Edge':
        return EdgeBrowser(name)
    if name == 'Brave':
        return BraveBrowser(name)
    return BaseBrowser(name)
