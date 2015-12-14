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
#   enso.quasimode
#
# ----------------------------------------------------------------------------

"""
    Implements the Quasimode.

    This module implements a singleton class that represents the
    quasimode. It handles all quasimodal key events, and the logic for
    transitioning in and out of the quasimode.  When the quasimode
    terminates, it initiates the execution of the command, if any,
    that the user indicated while in the quasimode.  It also handles
    the various kinds of user "error", which primarily consist of "no command
    matches the text the user typed".
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import time
import weakref
import logging
import traceback
import operator

from enso import messages
from enso import config
from enso import input

from enso.utils.strings import stringRatioBestMatch
from enso.utils.xml_tools import escape_xml
from enso.quasimode.suggestionlist import SuggestionList
from enso.quasimode.parametersuggestionlist import ParameterSuggestionList
from enso.quasimode.window import QuasimodeWindow
from enso.quasimode import layout
from enso.messages.windows import computeWidth
from enso.utils.memoize import memoized

# Import the standard allowed key dictionary, which relates virtual
# key codes to character strings.
from enso.quasimode.charmaps import STANDARD_ALLOWED_KEYCODES \
    as ALLOWED_KEYCODES


# ----------------------------------------------------------------------------
# TheQuasimode
# ----------------------------------------------------------------------------

class Quasimode(object):
    """
    Encapsulates the command quasimode state and event-handling.

    Future note: In code review, we realized that implementing the
    quasimode is an ideal case for the State pattern; the Quasimode
    singleton would have a private member for quasimode state, which
    would be an instance of one of two classes, InQuasimode or
    OutOfQuasimode, both descended from a QuasimodeState interface
    class.  Consequances of this include much cleaner transition code
    and separation of event handling into the two states.
    """

    __instance = None

    @classmethod
    def get( cls ):
        return cls.__instance

    @classmethod
    def install( cls, eventManager ):
        from enso.commands import CommandManager

        cls.__instance = cls( eventManager, CommandManager.get() )

    def __init__( self, eventManager, commandManager ):
        """
        Initialize the quasimode.
        """

        self.__cmdManager = commandManager

        # Boolean variable that records whether the quasimode key is
        # currently down, i.e., whether the user is "in the quasimode".
        self._inQuasimode = False

        # The QuasimodeWindow object that is responsible for
        # drawing the quasimode; set to None initially.
        # A QuasimodeWindow object is created at the beginning of
        # the quasimode, and destroyed at the completion of the
        # quasimode.
        self.__quasimodeWindow = None

        # The suggestion list object, which is responsible for
        # maintaining all the information about the auto-completed
        # command and suggested command names, and the text typed
        # by the user.
        self.__suggestionList = SuggestionList( self.__cmdManager )

        # The parameter-suggestion list object, which is responsible for
        # maintaining all the information about the parameter suggestions.
        # Used for suggesting history entries or web-query suggestions.
        self.__parameterSuggestionList = ParameterSuggestionList( self.__cmdManager )

        # Boolean variable that should be set to True whenever an event
        # occurs that requires the quasimode to be redrawn, and which
        # should be set to False when the quasimode is drawn.
        self.__needsRedraw = False

        # Whether the next redraw should redraw the entire quasimodal
        # display, or only the description and user text.
        self.__nextRedrawIsFull = False

        self.__eventMgr = eventManager

        # Register a key event responder, so that the quasimode can
        # actually respond to quasimode events.
        self.__eventMgr.registerResponder( self.onKeyEvent, "key" )

        # Creates new event types that code can subscribe to, to find out
        # when the quasimode (or mode) is started and completed.
        self.__eventMgr.createEventType( "startQuasimode" )
        self.__eventMgr.createEventType( "endQuasimode" )

        # Creates new event type that code can subscribe to, to find out
        # when the quasimode text has been modified.
        self.__eventMgr.createEventType( "textModified" )

        # Read settings from config file: are we modal?
        # What key activates the quasimode?
        # What keys exit and cancel the quasimode?

        self.setQuasimodeKeyByName( input.KEYCODE_QUASIMODE_START, #IGNORE:E1101
                                    config.QUASIMODE_START_KEY )
        self.setQuasimodeKeyByName( input.KEYCODE_QUASIMODE_END, #IGNORE:E1101
                                    config.QUASIMODE_END_KEY )
        self.setQuasimodeKeyByName( input.KEYCODE_QUASIMODE_CANCEL, #IGNORE:E1101
                                    config.QUASIMODE_CANCEL_KEY )
        self.setQuasimodeKeyByName( input.KEYCODE_QUASIMODE_CANCEL2, #IGNORE:E1101
                                    config.QUASIMODE_CANCEL_KEY2 )

        self.__isModal = config.IS_QUASIMODE_MODAL

        self.__eventMgr.setModality( self.__isModal )

        self.__lastQuasimodeStarted = None

        self._lastRunCommand = None

        self.__lastParameterSuggestionsCheck = 0.0
        self.__lastParameterSuggestions = None

        # Unique numeric ID of the Quasimode "session"
        self.__quasimodeID = 0



    def setQuasimodeKeyByName( self, function_name, key_name ):
        # Sets the quasimode to use the given key (key_name must be a
        # string corresponding to a constant defined in the os-specific
        # input module) for the given function ( which should be one of
        # the KEYCODE_QUASIMODE_START/END/CANCEL constants also defined
        # in input.)
        key_code = getattr( input, key_name )
        assert key_code, "Undefined quasimode key in config file: %s." % key_name
        self.__eventMgr.setQuasimodeKeycode( function_name, key_code )

    def getQuasimodeKeyByName( self, function_name ):
        return self.__eventMgr.getQuasimodeKeycode( function_name )

    def isModal( self ):
        return self.__isModal

    def setModal( self, isModal ):
        assert type( isModal ) == bool
        config.IS_QUASIMODE_MODAL = isModal

        self.__isModal = isModal
        self.__eventMgr.setModality( isModal )

    def getSuggestionList( self ):
        return self.__suggestionList

    def getLastRunCommand(self):
        return self._lastRunCommand

    def setDidyoumeanHint( self, hint ):
        is_dirty = (self.__suggestionList.getDidyoumeanHint() != hint)
        if hint == "":
            hint = None
        self.__suggestionList.setDidyoumeanHint(hint)
        if is_dirty:
            self.__needsRedraw = True

    def getDidyoumeanHint( self ):
        return self.__suggestionList.getDidyoumeanHint()

    def setParameterSuggestions( self, suggestions ):
        self.__parameterSuggestionList.setSuggestions(suggestions)

    def onKeyEvent( self, eventType, keyCode ):
        """
        Handles a key event of particular type.
        """

        if eventType == input.EVENT_KEY_QUASIMODE: #IGNORE:E1101

            if keyCode == input.KEYCODE_QUASIMODE_START: #IGNORE:E1101
                #assert not self._inQuasimode
                #self.__quasimodeBegin()
                if not self._inQuasimode:
                    self.__quasimodeBegin()
            elif keyCode == input.KEYCODE_QUASIMODE_END: #IGNORE:E1101
                #assert self._inQuasimode
                #self.__quasimodeEnd()
                if self._inQuasimode:
                    self.__quasimodeEnd()
                else:
                    self.__quasimodeEnd()
            elif keyCode in [input.KEYCODE_QUASIMODE_CANCEL, input.KEYCODE_QUASIMODE_CANCEL2]: #IGNORE:E1101
                self.__suggestionList.clearState()
                self.__quasimodeEnd()

        elif eventType == input.EVENT_KEY_DOWN and self._inQuasimode: #IGNORE:E1101
            # The user has typed a character, and we need to redraw the
            # quasimode.
            oldText = self.__suggestionList.getUserText()

            if keyCode in (input.KEYCODE_TAB, input.KEYCODE_RIGHT): #IGNORE:E1101
                if self.__parameterSuggestionList.isActive():
                    self.__parameterSuggestionList.cycleActiveSuggestion( 1 )
                    suggestion = self.__parameterSuggestionList.getActiveSuggestion()
                    #print suggestion
                    activeCmd = self.__suggestionList.getActiveCommand()
                    try:
                        userText = "%s%s" % (
                            activeCmd.PREFIX,
                            suggestion)
                        self.__suggestionList.setUserText(userText)
                    except:
                        pass
                    #self.__parameterSuggestionList.setSuggestions([])
                else:
                    # Allow handlers to act upon Tab key even if the text
                    # has not been modified
                    self.__eventMgr.triggerEvent("textModified", keyCode, oldText, oldText, quasimodeId=self.__quasimodeID)
                    self.__suggestionList.autoType()
            elif keyCode == input.KEYCODE_RETURN: #IGNORE:E1101
                self.__suggestionList.autoType()
            elif keyCode == input.KEYCODE_ESCAPE: #IGNORE:E1101
                self.__suggestionList.clearState()
                self.__parameterSuggestionList.setSuggestions([])
            elif keyCode == input.KEYCODE_DELETE: #IGNORE:E1101
                self.__onDelete()
                self.__onParameterModified(keyCode, oldText, self.__suggestionList.getUserText())
            elif keyCode == input.KEYCODE_BACK: #IGNORE:E1101
                # Backspace has been pressed.
                self.__onBackspace()
                self.__onParameterModified(keyCode, oldText, self.__suggestionList.getUserText())
            elif keyCode == input.KEYCODE_DOWN: #IGNORE:E1101
                # The user has pressed the down arrow; change which of the
                # suggestions is "active" (i.e., will be executed upon
                # termination of the quasimode)
                self.__suggestionList.cycleActiveSuggestion( 1 )
                if self.__parameterSuggestionList.isActive() and self.__suggestionList.getActiveIndex() > 0:
                    self.__parameterSuggestionList.setSuggestions([])
                    #self.__parameterSuggestionList.cycleActiveSuggestion( 1 )
                self.__nextRedrawIsFull = True
            elif keyCode == input.KEYCODE_UP: #IGNORE:E1101
                # Up arrow; change which suggestion is active.
                self.__suggestionList.cycleActiveSuggestion( -1 )
                if self.__parameterSuggestionList.isActive() and self.__suggestionList.getActiveIndex() > 0:
                    self.__parameterSuggestionList.setSuggestions([])
                    #self.__parameterSuggestionList.cycleActiveSuggestion( -1 )
                self.__nextRedrawIsFull = True
            elif keyCode == input.KEYCODE_HOME: #IGNORE:E1101
                # The user has pressed the down arrow; change which of the
                # suggestions is "active" (i.e., will be executed upon
                # termination of the quasimode)
                if self.__parameterSuggestionList.isActive():
                    self.__parameterSuggestionList.setActiveSuggestion(0)
            elif keyCode == input.KEYCODE_END: #IGNORE:E1101
                # Up arrow; change which suggestion is active.
                if self.__parameterSuggestionList.isActive():
                    self.__parameterSuggestionList.setActiveSuggestion(-1)
            elif keyCode in ALLOWED_KEYCODES: #IGNORE:E1101
                # The user has typed a valid key to add to the userText.
                self.__addUserChar( keyCode )
                self.__onParameterModified(keyCode, oldText, self.__suggestionList.getUserText())
            else:
                # The user has pressed a key that is not valid.
                pass

            self.__needsRedraw = True


    def __onParameterModified( self, keyCode, oldText, newText ):
        cmd = self.__suggestionList.getActiveCommand()
        try:
            prefixLen = len(cmd.PREFIX)
            cmd.onParameterModified(keyCode,
                oldText[prefixLen:], newText[prefixLen:],
                quasimodeId=self.__quasimodeID)
        except AttributeError as e:
            pass
        except Exception as e:
            logging.error(e)

        self.__eventMgr.triggerEvent("textModified", keyCode, oldText, newText, quasimodeId=self.__quasimodeID)


    def __addUserChar( self, keyCode ):
        """
        Adds the character corresponding to keyCode to the user text.
        """

        newCharacter = ALLOWED_KEYCODES[keyCode]
        oldUserText = self.__suggestionList.getUserText()

        # If known command was typed, examine the command object.
        # If the command object has OVERRIDE_ALLOWED_KEYCODES dictionary, use it to remap
        # keys while user is typing the command parameter.
        # This is useful for instance for 'calculate' command where we can remap some keys
        # to provide different mathematical symbols ('='->'+', '['->'(', ']'->')', '?'='/') etc.
        cmd = self.__suggestionList.getActiveCommand()
        if cmd and hasattr(cmd, "OVERRIDE_ALLOWED_KEYCODES") and oldUserText.startswith(cmd.PREFIX):
            newCharacter = cmd.OVERRIDE_ALLOWED_KEYCODES.get(keyCode, newCharacter)

        self.__suggestionList.setUserText( oldUserText + newCharacter )

        # If the user had indicated one of the suggestions, then
        # typing a character snaps the active suggestion back to the
        # user text and auto-completion.
        self.__suggestionList.resetActiveSuggestion()


    def __onBackspace( self ):
        """
        Deletes one character, if possible, from the user text.
        """

        oldUserText = self.__suggestionList.getUserText()
        if len( oldUserText ) == 0:
            # There is no user text; backspace does nothing.
            return

        self.__suggestionList.setUserText( oldUserText[:-1] )

        # If the user had indicated anything on the suggestion list,
        # then hitting backspace snaps the active suggestion back to
        # the user text.
        self.__suggestionList.resetActiveSuggestion()


    def __onDelete( self ):
        userText = self.__suggestionList.getUserText()
        if userText:
            prefix = self.__cmdManager.getCommandPrefix(userText)
            if prefix is not None and len(userText) > len(prefix):
                self.__suggestionList.setUserText(prefix)
            else:
                self.__suggestionList.clearState()

            self.__parameterSuggestionList.setSuggestions([])


    def __quasimodeBegin( self ):
        """
        Executed when user presses the quasimode key.
        """

        assert self._inQuasimode == False

        self.__quasimodeID = time.clock()

        if (config.QUASIMODE_DOUBLETAP_DELAY > 0
            and config.QUASIMODE_DOUBLETAP_COMMAND is not None):
            if self.__lastQuasimodeStarted is not None:
                elapsed = time.time() - self.__lastQuasimodeStarted
                if elapsed < config.QUASIMODE_DOUBLETAP_DELAY:
                    self.__suggestionList.clearState()
                    self.__suggestionList.setUserText(
                        "%s " % config.QUASIMODE_DOUBLETAP_COMMAND)
                    #self.__nextRedrawIsFull = True

        self.__lastQuasimodeStarted = time.time()

        if self.__quasimodeWindow is None:
            assert logging.debug( "Created a new quasimode window!" ) or True
            self.__quasimodeWindow = QuasimodeWindow()

        self.__eventMgr.triggerEvent( "startQuasimode" )

        self._inQuasimode = True
        self.__needsRedraw = True
        self.__lastParameterSuggestionsCheck = 0

        self.__eventMgr.registerResponder( self.__onTick, "timer" )

        # Postcondition
        assert self._inQuasimode == True


    def __onTick( self, timePassed ):
        """
        Timer event responder.  Re-draws the quasimode, if it needs it.
        Only registered while in the quasimode.

        NOTE: Drawing the quasimode takes place in __onTick() for
        performance reasons.  If a user mashed down 10 keys in
        the space of a few milliseconds, and the quasimode was re-drawn
        on every single keystroke, then the quasimode could suddenly
        be lagging behind the user a half a second or more.
        """

        # So pychecker doesn't complain...
        dummy = timePassed

        assert self._inQuasimode == True

        self.__refreshParameterSuggestionsList(timePassed)
        
        if self._inQuasimode:
            if self.__needsRedraw:
                self.__needsRedraw = False
                self.__quasimodeWindow.update( self, self.__nextRedrawIsFull )
                self.__nextRedrawIsFull = False
            else:
                # If the quasimode hasn't changed, then continue drawing
                # any parts of it (such as the suggestion list) that
                # haven't been drawn/updated yet.
                self.__quasimodeWindow.continueDrawing()


    def __quasimodeEnd( self ):
        """
        Executed when user releases the quasimode key.
        """

        # The quasimode has terminated; remove the timer responder
        # function as an event responder.
        self.__eventMgr.removeResponder( self.__onTick, sync=True )
        
        self.__eventMgr.triggerEvent( "endQuasimode" )

        # Hide the Quasimode window.
        self.__quasimodeWindow.hide()
        self.__parameterSuggestionList.hide()
        self.__parameterSuggestionList.clearState()

        activeCommand = self.__suggestionList.getActiveCommand()
        cmdName = self.__suggestionList.getActiveCommandName()
        userText = self.__suggestionList.getUserText()
        if activeCommand is None and len( userText ) > config.BAD_COMMAND_MSG_MIN_CHARS and config.NO_COMMAND_FALLBACK:
            cmdName = config.NO_COMMAND_FALLBACK % userText
            activeCommand = self.__get_fallback_command( cmdName )

        if activeCommand is not None:
            self.__executeCommand( activeCommand, cmdName )
        elif len( userText ) > config.BAD_COMMAND_MSG_MIN_CHARS:
            # The user typed some text, but there was no command match
            self.__showBadCommandMsg( userText )

        self.__suggestionList.clearState()

        self.__quasimodeID = 0

        self._inQuasimode = False


    def __get_fallback_command(self, cmdName ):
        return self.__cmdManager.getCommand( cmdName )


    def __executeCommand( self, cmd, cmdName ):
        """
        Attempts to execute the command.  Catches any errors raised by
        the command code and deals with them appropriately, e.g., by
        launching a bug report, informing the user, etc.

        Commands should deal with user-errors, like lack of selection,
        by displaying messages, etc.  Exceptions should only be raised
        when the command is actually broken, or code that the command
        calls is broken.
        """

        # The following message may be used by system tests.
        logging.info( "COMMAND EXECUTED: %s" % cmdName )
        try:
            cmd.run()
            self._lastRunCommand = cmd
        except Exception:
            # An exception occured during the execution of the command.
            logging.error( "Command \"%s\" failed." % cmdName )
            logging.error( traceback.format_exc() )
            raise


    def __showBadCommandMsg( self, userText ):
        """
        Displays an error message telling the user that userText does
        not match any command.  Also, if there are any reasonable
        commands that were similar but not matching, offers those to
        the user as suggestions.
        """

        # Generate a caption for the message with a couple suggestions
        # for command names similar to the user's text
        caption = self.__commandSuggestionCaption( escape_xml( userText ) )
        badCmd = userText.lower()
        badCmd = escape_xml( badCmd )
        # Create and display a primary message.
        text = config.BAD_COMMAND_MSG
        text = text % ( badCmd, caption )

        messages.displayMessage( text )


    def __commandSuggestionCaption( self, userText ):
        """
        Creates and returns a caption suggesting one or two commands
        that are similar to userText.
        """

        # Retrieve one or two command name suggestions.
        suggestions = self.__cmdManager.retrieveSuggestions( userText )
        cmds = [ s.toText() for s in suggestions ]
        if len(cmds) > 0:
            ratioBestMatch = stringRatioBestMatch( userText.lower(), cmds )
            caption = config.ONE_SUGG_CAPTION
            caption = caption % ratioBestMatch
        else:
            # There were no suggestions; so we don't want a caption.
            caption = ""

        return caption


    def __refreshParameterSuggestionsList( self, timePassed ):
        self.__lastParameterSuggestionsCheck += timePassed

        # Check only each 10 milliseconds
        if self.__lastParameterSuggestionsCheck < 10:
            return

        self.__lastParameterSuggestionsCheck = 0

        # Check active command
        cmd = self.__suggestionList.getActiveCommand()
        if not cmd:
            return

        try:
            suggestions = cmd.getParameterSuggestions()
        except AttributeError as e:
            # Check if it is arbitrary-postfix command that supports suggestions
            return
        except Exception as e:
            logging.error("Error calling command.getParameterSuggestions(): %s", e)
            return

        if not suggestions and not self.__lastParameterSuggestions:
            return
            
        # No suggestions returned or the list has not changed since last time
        if suggestions is None or suggestions == self.__lastParameterSuggestions:
            return

        if not self.__parameterSuggestionList.getSuggestions():
            # The window has not been displayed yet, compute its horizontal position
            line = layout.layoutXmlLine(
                xml_data = "<document><line>%s</line></document>" % cmd.PREFIX,
                styles = layout.retrieveAutocompleteStyles(),
                scale = layout.AUTOCOMPLETE_SCALE
            )
            xPos = computeWidth(line)
        else:
            xPos = None

        # Display and refresh the suggestion window
        self.__parameterSuggestionList.setSuggestions(suggestions, xPos)
        self.__lastParameterSuggestions = suggestions


    def quasimodeBegin(self):
        assert not self._inQuasimode
        self.__quasimodeBegin()

    def quasimodeEnd(self):
        assert self._inQuasimode
        self.__quasimodeEnd()

    def replaceText( self, newText ):
        userText = self.__suggestionList.getUserText()
        if userText:
            prefix = self.__cmdManager.getCommandPrefix(userText)
            if prefix is not None and len(userText) > len(prefix):
                self.__suggestionList.setUserText(prefix + " " + newText)
            else:
                self.__suggestionList.setUserText(newText)


    def forceRedraw(self):
        self.__needsRedraw = True
        self.__nextRedrawIsFull = True
        self.__suggestionList.markDirty()
        #self.__quasimodeWindow.updateSuggestionList( self )
        # If the user had indicated one of the suggestions, then
        # typing a character snaps the active suggestion back to the
        # user text and auto-completion.
        #self.__suggestionList.resetActiveSuggestion()
        #self.__quasimodeWindow.updateSuggestionList( self )
        #self.__suggestionList.markDirty()
        #self.__quasimodeWindow.updateSuggestionList( self )

