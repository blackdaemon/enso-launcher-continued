# Copyright (c) 2008, Humanized, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso.graphics.font
#
# ----------------------------------------------------------------------------

"""
    This module provides a high-level interface for registering and
    accessing fonts, including their font metrics information, their
    glyphs, and their rendering.

    This module requires no initialization or shutdown.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import logging
import sys

import enso
from enso import cairo, config
from enso.utils import do_once
from enso.utils.memoize import memoized

_graphics = enso.providers.getInterface("graphics")


# ----------------------------------------------------------------------------
# Fonts
# ----------------------------------------------------------------------------

class Font(object):
    """
    Encapsulates a font face, which describes both a given typeface
    and style.
    """

    __slots__ = (
        '__weakref__',
        'ascent',
        'cairoContext',
        'descent',
        'font_name',
        'font_opts',
        'height',
        'isItalic',
        'maxXAdvance',
        'maxYAdvance',
        'name',
        'size',
        'slant',
    )

    _cairoContext = None

    def __init__(self, name, size, isItalic):
        """
        Creates a Font with the given properties.
        """

        self.name = name
        self.size = size
        self.isItalic = isItalic
        self.font_name = None
        self.font_opts = {}
        
        if self.isItalic:
            self.slant = cairo.FONT_SLANT_ITALIC  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
        else:
            self.slant = cairo.FONT_SLANT_NORMAL  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy

        if not Font._cairoContext:
            dummySurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
            Font._cairoContext = cairo.Context(dummySurface)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy

        self.cairoContext = Font._cairoContext

        self.cairoContext.save()

        self.loadInto(self.cairoContext)

        # Make our font metrics information visible to the client.

        (self.ascent,
         self.descent,
         self.height,
         self.maxXAdvance,
         self.maxYAdvance) = self.cairoContext.font_extents()

        self.cairoContext.restore()

    @classmethod
    @memoized
    def get(cls, name, size, isItalic):
        """
        Retrieves the Font object with the given properties.

        The fact that this class method is memoized effectively makes
        this mechanism a flyweight pool of Font objects.
        """

        return cls(name, size, isItalic)

    @memoized
    def getGlyph(self, char):
        """
        Returns a glyph of the font corresponding to the given Unicode
        character.
        """

        return FontGlyph(char, self, self.cairoContext)

    def getKerningDistance(self, charLeft, charRight):
        """
        Returns the kerning distance (in points) between the two
        Unicode characters for this font face.
        """

        # LONGTERM TODO: Get this to work. This may involve modifying
        # the source code of Cairo.
        return 0.0

    def loadInto(self, cairoContext):
        """
        Sets the cairo context's current font to this font.
        """

        def get_font_name(font_id):
            """
            Get the font name based on the font_id.
            Font_id equals font name on Linux.
            On Windows, we need to return the font filename.
            """
            if not sys.platform.startswith("win"):
                # font_id represents the name on Linux/OSX
                return font_id
            
            """
            TODO: Used Cairo version does not have any usable font registry
            implementation on Windows. This win32 specific code handling should
            go away as soon as Cairo is updated to newer version with better
            font support for Windows.
            """
            # For Win32, we have to lookup the font filename
            font_name = None
            # FIXME: FontRegistry is present only for Win32 platform
            font_detail = _graphics.FontRegistry.get().get_font_detail(font_id)
            if font_detail:
                font_name = font_detail.filepath
                do_once(
                    logging.info,
                    u"Font used: %s" % repr(font_detail)
                )
            else:
                do_once(
                    logging.error,
                    u"Specified font was not found in the system: %s" % font_id
                )
            return font_name

        def font_exists(font_id):
            """
            Find out if the font with given font_id exists on the system
            Font_id is the font name like "Input Consensed Light" or "Arial"
            """
            if sys.platform.startswith("win"):
                return _graphics.FontRegistry.get().get_font_detail(font_id) is not None
            else:
                # FIXME: Provide OSX code
                from enso.platform.linux.utils import get_cmd_output
                rc, _ = get_cmd_output(
                    "fc-list | grep -E \"{0}\"".format(font_id.replace(" ", " ?"))
                )
                return rc == 0
            
        # Set it just once
        if not self.font_name:
            font_name = None
            font_opts = {}

            if hasattr(config, "FONT_NAME"):
                # Search for suitable font in config
                f = config.FONT_NAME["normal"]
                if self.isItalic and "italic" in config.FONT_NAME:
                    # italic font
                    f = config.FONT_NAME["italic"]
                if isinstance(f, basestring):
                    font_name = get_font_name(f)
                else:
                    font_list = f + ["Helvetica", "Arial", "Liberation Sans"]
                    for font_spec in font_list:
                        if isinstance(font_spec, basestring):
                            font_id = font_spec
                        else:
                            font_id, font_opts = font_spec
                        if font_exists(font_id):
                            font_name = get_font_name(font_id)
                            break
            else:
                logging.error(
                    "There is no FONT_NAME setting in enso.config.")

            self.font_name = font_name
            self.font_opts = font_opts

        if self.font_name:
            if self.isItalic:
                do_once(
                    logging.info,
                    "Using font (italic): {0}".format(self.font_name)
                )
            else:
                do_once(
                    logging.info,
                    "Using font (normal): {0}".format(self.font_name)
                )

            fo = cairo.FontOptions()  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
            try:
                fo.set_antialias(cairo.ANTIALIAS_GRAY)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
                #fo.set_hint_metrics(cairo.HINT_METRICS_ON)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
            except:
                pass
            else:
                cairoContext.set_font_options(fo)
            
            cairoContext.select_font_face(
                self.font_name,
                self.slant,
                cairo.FONT_WEIGHT_NORMAL  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
            )

            cairoContext.set_font_size(self.size)


# ----------------------------------------------------------------------------
# Font Glyphs
# ----------------------------------------------------------------------------

class FontGlyph(object):
    """
    Encapsulates a glyph of a font face.
    """

    __slots__ = (
        '__weakref__',
        'advance',
        'char',
        'charAsUtf8',
        'font',
        'xMax',
        'xMin',
        'yMax',
        'yMin',
    )
    
    def __init__(self, char, font, cairoContext):
        """
        Creates the font glyph corresponding to the given Unicode
        character, using the font specified by the given Font object
        and the given cairo context.
        """

        # Encode the character to UTF-8 because that's what the cairo
        # API uses.
        self.charAsUtf8 = char.encode("UTF-8")
        self.char = char
        self.font = font

        cairoContext.save()

        self.font.loadInto(cairoContext)

        # Make our font glyph metrics information visible to the client.

        (xBearing,
         yBearing,
         width,
         height,
         xAdvance,
         yAdvance) = cairoContext.text_extents(self.charAsUtf8)

        # The xMin, xMax, yMin, yMax, and advance attributes are used
        # here to correspond to their values in this image:
        # http://freetype.sourceforge.net/freetype2/docs/glyphs/Image3.png

        self.xMin = xBearing
        self.xMax = xBearing + width
        self.yMin = -yBearing + height
        self.yMax = -yBearing

        # User can specify custom spacing between letters
        xAdvanceModifier = 1.0
        try:
            xAdvanceModifier = self.font.font_opts.get("xAdvanceModifier", xAdvanceModifier) * 1.0
        except:
            pass
        if xAdvanceModifier < 0.5 or xAdvanceModifier > 1.5:
            logging.error("config.FONT_NAME option 'xAdvanceModifier' must be decimal number between 0.0 and 1.0")
            xAdvanceModifier = 1.0
        self.advance = xAdvance * xAdvanceModifier

        cairoContext.restore()
