import enso.providers

_graphics = enso.providers.getInterface("graphics")

from enso.graphics.measurement import pointsToPixels, pixelsToPoints

def getDesktopOffset():
    """ Return primary monitor desktop offset in points. """
    left, top = _graphics.getDesktopOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints (top)
    return (left, top)

def getDesktopSize():
    """ Return primary monitor desktop size in points. """
    width, height = _graphics.getDesktopSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    return (width, height)

def getWorkareaOffset():
    """
    Return primary monitor workarea offset in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    left, top = _graphics.getWorkareaOffset()
    left = pixelsToPoints(left)
    top = pixelsToPoints (top)
    return (left, top)

def getWorkareaSize():
    """
    Return primary monitor workarea size in points.
    Workarea is the desktop area not covered with taskbar and appbars.
    """
    width, height = _graphics.getWorkareaSize()
    width = pixelsToPoints(width)
    height = pixelsToPoints(height)
    return (width, height)
