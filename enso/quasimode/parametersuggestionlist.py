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
#   enso.quasimode.parametersuggestionlist
#
# ----------------------------------------------------------------------------

"""
    Implements a SuggestionList to keep track of auto-completions,
    suggestions, and other data related to typing in the quasimode.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import time

from collections import namedtuple

from enso import commands
from enso import config
from enso import cairo
from enso import graphics
from enso.events import EventManager
from enso.graphics.measurement import pointsToPixels, pixelsToPoints
from enso.graphics.measurement import convertUserSpaceToPoints
from enso.graphics.transparentwindow import TransparentWindow
from enso.graphics import rounded_rect
from enso.quasimode import layout
from enso.graphics import xmltextlayout
from enso.utils.xml_tools import escape_xml
from enso.utils.decorators import suppress

Position = namedtuple('Position', 'x y')

ANIMATION_TIME = 10
MAX_OPACITY = 255


class ParameterSuggestionWindow:
    """
    Encapsulates the drawing of a single line of text, with optional
    rounded corners and an optional "override width", which overides the
    default width (margins + text width).
    """

    def __init__( self, height, position ):
        """
        Creates the underlying TransparentWindow and Cairo context.

        Position and height should be in pixels.
        """

        # Use the maximum width that we can, i.e., the desktop width.
        desk_width, desk_height = graphics.getDesktopSize()
        desk_left, desk_top = graphics.getDesktopOffset()

        xPos, yPos = position
        if yPos+height > desk_height:
            pass
        self.__window = TransparentWindow(xPos+desk_left, yPos+desk_top, desk_width, desk_height-desk_top-yPos)
        self.__context = self.__window.makeCairoContext()
        self.__is_visible = False
        self.__animatingShow = False
        self.__animatingHide = False
        self.__timeSinceDismissal = 0
        self.__evtManager = EventManager.get()
        

    def getHeight( self ):
        """
        LONGTERM TODO: Document this.
        """

        return self.__window.getHeight()


    def getPosition(self):
        """
        LONGTERM TODO: Document this.
        """

        return Position(self.__window.getX(), self.__window.getY())


    def setPosition(self, x, y):
        """
        LONGTERM TODO: Document this.
        """
        self.__window.setPosition(x, y)


    def draw( self, document, activeIndex ):
        """
        Draws the text described by document.

        An updating call; at the end of this method, the displayed
        window should reflect the drawn content.
        """

        def _computeWidth( doc ):
            lines = []
            for b in doc.blocks:
                lines.extend( b.lines )
            if len( lines ) == 0:
                return 0
            return max( [ l.xMax for l in lines ] )
        def _computeHeight( doc ):
            height = 0
            for b in doc.blocks:
                height += b.height
                #for line in b.lines:
                #    height += line.lineHeight
            return height

        width = _computeWidth(document) + layout.L_MARGIN + layout.R_MARGIN
        width = max(width, 300)
        height = document.height #_computeHeight(document)

        cr = self.__context

        # Clear the areas where the corners of the rounded rectangle will be.

        cr.save()
        cr.set_source_rgba( 0, 0, 0, 0 )
        cr.set_operator( cairo.OPERATOR_SOURCE ) #IGNORE:E1101 @UndefinedVariable
        cr.rectangle( width - rounded_rect.CORNER_RADIUS,
                      height - rounded_rect.CORNER_RADIUS,
                      rounded_rect.CORNER_RADIUS,
                      rounded_rect.CORNER_RADIUS )
        cr.rectangle( width - rounded_rect.CORNER_RADIUS,
                      0,
                      rounded_rect.CORNER_RADIUS,
                      rounded_rect.CORNER_RADIUS )
        cr.paint()

        """
        # Draw the background rounded rectangle.
        corners = []
        #corners.append( rounded_rect.UPPER_LEFT )
        #if document.roundUpperRight:
        corners.append( rounded_rect.UPPER_RIGHT )
        #if document.roundLowerRight:
        corners.append( rounded_rect.LOWER_RIGHT )
        #if document.roundLowerLeft:
        corners.append( rounded_rect.LOWER_LEFT )
        """
        corners = {
            rounded_rect.UPPER_RIGHT:None,
            rounded_rect.LOWER_RIGHT:14,
            rounded_rect.LOWER_LEFT:None
            }
        
        document.background = xmltextlayout.colorHashToRgba( layout.MAIN_BACKGROUND_COLOR )

        cr.set_source_rgba( *document.background )
        rounded_rect.drawRoundedRect( context = cr,
                                      rect = ( 0, 0, width, height ),
                                      softenedCorners=corners )
        cr.fill_preserve()

        cr.set_source_rgba( *xmltextlayout.colorHashToRgba( "#404040" ) )
        cr.set_line_width(1.0)

        if activeIndex is not None:
            bar_left = layout.L_MARGIN - 2
            bar_width = width - bar_left - layout.L_MARGIN + 2
            bar_height = document.blocks[0].height
            bar_top = activeIndex * bar_height + document.marginTop

            rounded_rect.drawRoundedRect( context = cr,
	                                      rect = (
	                                          bar_left,
	                                          bar_top,
	                                          bar_width,
	                                          bar_height),
	                                      softenedCorners = rounded_rect.ALL_CORNERS,
	                                      radius=2 )

        cr.fill_preserve()
        #cr.stroke()

        cr.restore()

        # Next, draw the text.
        document.draw( layout.L_MARGIN,
                       document.shrinkOffset,
                       self.__context )

        width = min( self.__window.getMaxWidth(), width )

        #height = document.blocks[0].height * len(document.blocks) #layout.PARAMETERSUGGESTION_SCALE[-1]*layout.HEIGHT_FACTOR
        #height = min( self.__window.getMaxHeight(), height )

        #self.__window.setSize( width, height )
        
        if not self.__is_visible and not self.__animatingShow:
            self.__animatingShow = True
            self.__animatingHide = False
            self.__is_visible = True
            self.__timeSinceDismissal = 0
            with suppress(AssertionError):
                self.__evtManager.registerResponder( self.animationTick, "timer" )
        else:
            # Just refreshing
            started = time.time()
            self.__window.setOpacity( MAX_OPACITY )
            #print time.time() - started
            self.__window.update()
        #print time.time() - started


    def hide( self, animated=True ):
        """
        Clears the window's surface (making it disappear).
        """
        if not self.__is_visible:
            return

        if self.__animatingHide or self.__animatingShow:
            self.__onAnimationFinished()
            return

        # LONGTERM TODO: Clearing the surface, i.e., painting it
        # clear, seems like a potential performance bottleneck.

        #self.__window.setSize( 1, 1 )

        # Frankly, I don't know why this works, but after this
        # function, the resulting window is totally clear. I find it
        # odd, since the alpha value is not being set.  It is a
        # wierdness of Cairo. -- Andrew

        #self.__context.set_operator (cairo.OPERATOR_CLEAR)
        #self.__context.paint ()
        #self.__context.set_operator (cairo.OPERATOR_OVER)

        #self.__window.update()

        if animated:
            self.__timeSinceDismissal = 0
            self.__animatingHide = True
            self.__animatingShow = False
            self.__evtManager.registerResponder( self.animationTick, "timer" )
        else:
            self.__window.hide()
            self.__animatingHide = False
            self.__animatingShow = False


    def animationTick( self, msPassed ):
        """
        Called on a timer event to animate the window fadeout
        """

        self.__timeSinceDismissal += msPassed
        if self.__timeSinceDismissal > ANIMATION_TIME:
            if self.__animatingShow and self.__is_visible:
                self.__onAnimationFinished()
            return

        timeLeft  = ANIMATION_TIME - self.__timeSinceDismissal
        frac = timeLeft / float(ANIMATION_TIME)
        opacity = int( MAX_OPACITY*frac )
        
        if self.__animatingHide:
            self.__window.setOpacity( opacity )
            if opacity == 0:
                self.__is_visible = False
        elif self.__animatingShow:
            self.__is_visible = True
            self.__window.setOpacity( MAX_OPACITY-opacity )

        self.__window.update()

    
    def __onAnimationFinished(self):
        self.__evtManager.removeResponder( self.animationTick )
        if self.__animatingHide:
            self.__animatingHide = False
            self.__window.hide()
            self.__is_visible = False
        elif self.__animatingShow:
            self.__animatingShow = False


# ----------------------------------------------------------------------------
# The SuggestionList Singleton
# ----------------------------------------------------------------------------

class ParameterSuggestionList( object ):
    """
    A singleton class that encapsulates all of the textual information
    created when a user types in the quasimode, including the user's
    typed text, the auto-completion, any suggestions, the command
    description/help text and optional "did you mean?" hint.
    """

    # LONGTERM TODO: The trio of main data elements:
    #   ( __autoCompletion, __suggestions, __activeIndex )
    # These should never be updated except together; and they
    # should never be accessed unless updated. Right now, this
    # involves a nasty, hard-to-maintain cludge of an "update"
    # mechanism.
    # This class should be a new-style class, and these attributes
    # should be properties whose getters appropriately update them.
    # This eliminates the burden on client code to remember to call
    # update near/around fetching these attributes, and will eliminate
    # a source of errors.

    def __init__( self, commandManager ):
        """
        Initializes the ParameterSuggestionList.
        """
        super(ParameterSuggestionList, self).__init__()

        self.__cmdManager = commandManager

        # Set all of the member variables to their empty values.
        self.clearState()

        yPos = layout.DESCRIPTION_SCALE[-1]*layout.HEIGHT_FACTOR \
            + layout.AUTOCOMPLETE_SCALE[-1]*layout.HEIGHT_FACTOR
        height = layout.PARAMETERSUGGESTION_SCALE[-1]*layout.HEIGHT_FACTOR
        self.__window = ParameterSuggestionWindow(
            height = 200,
            position = [ 200, yPos ],
            )
        # Nothing selected initialy
        self.__activeIndex = None
        self.styles = layout.retrieveParameterSuggestionStyles()


    def clearState( self ):
        """
        Clears all of the variables relating to the state of the
        quasimode's generated information.
        """

        # An index of the above suggestion list indicating which
        # command name the user has indicated.
        self.__activeIndex = None
        #self.__activeIndex = 0

        # The current list of suggestions. The 0th element is the
        # auto-completion.
        self.__suggestions = []

        self.__isDirty = False


    def __markDirty(self):
        self.__isDirty = True


    def isActive(self):
        return len(self.__suggestions) > 0

    def getSuggestions( self ):
        """
        In a pair with getAutoCompletion(), this method gets the latest
        suggestion list, making sure that the internal variable is
        updated.
        """
        return self.__suggestions


    def setSuggestions( self, suggestions, xPos=None ):
        """
        Sets the suggestions list and displays/hides the suggestions window.
        If xPos parameter is specified, the window is placed at the given
        horizontal position.
        """
        if suggestions is None:
            suggestions = []

        # Check if suggestions changed
        if self.__suggestions == suggestions:
            return

        self.__markDirty()

        self.__suggestions = suggestions

        if suggestions:
            self.__activeIndex = None
            #self.__activeIndex = min(self.__activeIndex, len(suggestions)-1)
            if xPos is not None:
                self.__window.setPosition(xPos, self.__window.getPosition()[1])
            self.draw()
        else:
            self.__activeIndex = None
            self.hide()


    def getActiveSuggestion( self ):
        """
        Determines the command name of the "active" command, i.e., the
        name that is indicated to the user as the command that will
        be activated on exiting the quasimode.
        """

        activeSugg = self.__suggestions[self.__activeIndex]
        return activeSugg


    def setActiveSuggestion( self, pos ):
        """
        Changes which of the suggestions is "active", i.e., which suggestion
        will be activated when the user releases the CapsLock key.
        """
        if pos == self.__activeIndex:
            return
        if pos < 0:
            pos = len(self.getSuggestions()) + pos
        pos = min(pos, len(self.getSuggestions())-1)
        pos = max(0, pos)
        self.__activeIndex = pos
        # One of the source variables has changed.
        self.__markDirty()
        self.draw()


    def cycleActiveSuggestion( self, distance ):
        """
        Changes which of the suggestions is "active", i.e., which suggestion
        will be activated when the user releases the CapsLock key.

        Used to implement the up/down arrow key behavior.
        """
        if self.__activeIndex is None:
            self.__activeIndex = 0
            self.__activeIndex += distance - 1
        else:
            self.__activeIndex += distance
        if len( self.getSuggestions() ) > 0:
            truncateLength = len( self.getSuggestions() )
            self.__activeIndex = self.__activeIndex % truncateLength
        else:
            self.__activeIndex = 0
        # One of the source variables has changed.
        self.__markDirty()
        self.draw()


    def getActiveIndex( self ):
        return self.__activeIndex


    def resetActiveSuggestion( self ):
        """
        Sets the active suggestion to 0, i.e., the user's
        text/auto-completion.
        """

        self.__activeIndex = None

        # One of the source variables has changed.
        self.__markDirty()


    def hide( self ):
        self.__window.hide()


    def draw( self ):
        if not self.__isDirty:
            return

        self.__isDirty = False

        suggestions = self.getSuggestions()
        if not suggestions:
            self.hide()
            return

        #styles = layout.retrieveParameterSuggestionStyles()
        #styles.update('document', margin_top = '0.0pt')

        DOCUMENT_XML = "<document>%s</document>"
        LINE_XML = "<line>%s</line>"
        ACTIVE_LINE_XML = "<line><alt>%s</alt></line>"

        lines_xml = []
        active = self.getActiveIndex()
        for i, line in enumerate(suggestions):
            lines_xml.append((ACTIVE_LINE_XML if i == active else LINE_XML) % escape_xml(line))

        xml_data = DOCUMENT_XML % "".join(lines_xml)

        lines = layout.layoutXmlLine(
            xml_data = xml_data,
            styles = self.styles,
            scale = layout.PARAMETERSUGGESTION_SCALE,
            )
        self.__window.draw( lines, active )


# vim:set tabstop=4 shiftwidth=4 expandtab: