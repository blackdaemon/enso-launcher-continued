from collections import namedtuple
import enso.providers

Position = namedtuple('Position', 'x y')
Size = namedtuple('Size', 'width height')

_graphics = enso.providers.getInterface("graphics")

from enso.graphics.measurement import pointsToPixels, pixelsToPoints

__desktop_offset = None
__desktop_size = None
__workarea_offset = None
__workarea_size = None


def refreshDesktopOffset():
    global __desktop_offset
    left, top = _graphics.getDesktopOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints(top)
    __desktop_offset = Position(left, top)


def refreshDesktopSize():
    global __desktop_size
    width, height = _graphics.getDesktopSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    __desktop_size = Size(width, height)


def refreshDesktopInfo():
    refreshDesktopOffset()
    refreshDesktopSize()


def refreshWorkareaOffset():
    global __workarea_offset
    left, top = _graphics.getWorkareaOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints(top)
    __workarea_offset = Position(left, top)


def refreshWorkareaSize():
    global __workarea_size
    width, height = _graphics.getWorkareaSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    __workarea_size = Size(width, height)


def refreshWorkareaInfo():
    refreshWorkareaOffset()
    refreshWorkareaSize()


def getDesktopOffset(force_refresh=False):
    """ Return primary monitor desktop offset in points. 
    WARNING: This is very expensive operation on Linux
    We cache it here. Call refreshWorkareaSize() to refresh the cache.
    """
    global __desktop_offset
    if __desktop_offset is None or force_refresh:
        refreshDesktopOffset()
    return __desktop_offset


def getDesktopSize(force_refresh=False):
    """ Return primary monitor desktop size in points. 
    WARNING: This is very expensive operation on Linux
    We cache it here. Call refreshWorkareaSize() to refresh the cache.
    """
    global __desktop_size
    if __desktop_size is None or force_refresh:
        refreshDesktopSize()
    return __desktop_size


def getWorkareaOffset(force_refresh=False):
    """
    Return primary monitor workarea offset in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    WARNING: This is very expensive operation on Linux
    We cache it here. Call refreshWorkareaSize() to refresh the cache.
    """
    global __workarea_offset
    if __workarea_offset is None or force_refresh:
        refreshWorkareaOffset()
    return __workarea_offset


def getWorkareaSize(force_refresh=False):
    """
    Return primary monitor workarea size in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    WARNING: This is very expensive operation on Linux
    We cache it here. Call refreshWorkareaSize() to refresh the cache.
    """
    global __workarea_size
    if __workarea_size is None or force_refresh:
        refreshWorkareaSize()
    return __workarea_size


def processWindowManagerPendingEvents():
    _graphics.processWindowManagerPendingEvents()
    return None
