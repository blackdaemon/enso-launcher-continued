__updated__ = "2019-05-13"

import enso.providers

from enso.graphics.measurement import pointsToPixels, pixelsToPoints
from enso.graphics.measurement import convertUserSpaceToPoints
from enso import cairo

_graphics = enso.providers.get_interface("graphics")

# This is a wrapper for the platform-specific implementation of a
# TransparentWindow that makes the class use points instead of
# pixels.


class TransparentWindow(object):

    __slots__ = (
        '__cached_opacity',
        '__cached_position',
        '__cached_size',
        '__weakref__',
        '_impl',
    )
    
    def __init__(self, xPos, yPos, width, height):
        # Convert from points to pixels
        xPos = int(pointsToPixels(xPos))
        yPos = int(pointsToPixels(yPos))
        width = max(int(pointsToPixels(width)), 1)
        height = max(int(pointsToPixels(height)), 1)
        self.__cached_opacity = None
        self.__cached_position = None
        self.__cached_size = None
        self._impl = _graphics.TransparentWindow(xPos, yPos,
                                                 width, height)

    def makeCairoContext(self):
        context = cairo.Context(self._impl.makeCairoSurface())  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
        convertUserSpaceToPoints(context)
        return context

    def update(self):
        return self._impl.update()

    def hide(self):
        return self._impl.hideWindow()

    def finish(self):
        try:
            self._impl.finish()
        except:
            pass
        del self._impl

    def setOpacity(self, opacity):
        # OPTIMIZATION BEGIN:
        # Caching last set opacity for doing it only if the value is different
        # as setting the opacity is quite expensive
        if opacity != self.__cached_opacity:
            self.__cached_opacity = opacity
            return self._impl.setOpacity(opacity)
        else:
            return True
        # OPTIMIZATION END

    def getOpacity(self):
        return self._impl.getOpacity()

    def setPosition(self, x, y):
        # OPTIMIZATION BEGIN:
        # Caching last set position for doing it only if the value is different
        if (x, y) != self.__cached_position:
            self.__cached_position = (x, y)
            return self._impl.setPosition(
                int(pointsToPixels(x)),
                int(pointsToPixels(y))
            )
        else:
            return True
        # OPTIMIZATION END

    def getX(self):
        return pixelsToPoints(self._impl.getX())

    def getY(self):
        return pixelsToPoints(self._impl.getY())

    def setSize(self, width, height):
        # OPTIMIZATION BEGIN:
        # Caching last set size for doing it only if the value is different
        if (width, height) != self.__cached_size:
            self.__cached_size = (width, height)
            return self._impl.setSize(
                max(int(pointsToPixels(width)), 1),
                max(int(pointsToPixels(height)), 1)
            )
        else:
            return True
        # OPTIMIZATION END

    def getWidth(self):
        return pixelsToPoints(self._impl.getWidth())

    def getHeight(self):
        return pixelsToPoints(self._impl.getHeight())

    def getMaxWidth(self):
        return pixelsToPoints(self._impl.getMaxWidth())

    def getMaxHeight(self):
        return pixelsToPoints(self._impl.getMaxHeight())

    def grabPointer(self):
        try:
            return self._impl.grab_pointer()
        except AttributeError:
            # Not implemented and not needed on win32
            pass

    def ungrabPointer(self):
        try:
            return self._impl.ensure_pointer_ungrabbed()
        except AttributeError:
            # Not implemented and not needed on win32
            pass

    def __del__(self):
        '''Destroy the inner instance'''
        self.finish()
