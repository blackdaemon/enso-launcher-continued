from collections import namedtuple
import enso.providers

Position = namedtuple('Position', 'x y')
Size = namedtuple('Size', 'width height')

_graphics = enso.providers.getInterface("graphics")

from enso.graphics.measurement import pointsToPixels, pixelsToPoints

def getDesktopOffset():
    """ Return primary monitor desktop offset in points. """
    left, top = _graphics.getDesktopOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints (top)
    return Position(left, top)

def getDesktopSize():
    """ Return primary monitor desktop size in points. """
    width, height = _graphics.getDesktopSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    return Size(width, height)

def getWorkareaOffset():
    """
    Return primary monitor workarea offset in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    left, top = _graphics.getWorkareaOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints (top)
    return Position(left, top)

def getWorkareaSize():
    """
    Return primary monitor workarea size in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    width, height = _graphics.getWorkareaSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    return Size(width, height)

def processWindowManagerPendingEvents():
    _graphics.processWindowManagerPendingEvents()
    return None
    