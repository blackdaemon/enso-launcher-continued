# -*- coding: utf-8 -*-
# vim:set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
#
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
#   enso.quasimode.suggestionlist
#
# ----------------------------------------------------------------------------

"""
    Implements a SuggestionList to keep track of auto-completions,
    suggestions, and other data related to typing in the quasimode.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
from heapq import nsmallest

from enso import commands
from enso.commands.suggestions import Suggestion, AutoCompletion
from enso import config


# ----------------------------------------------------------------------------
# The SuggestionList Singleton
# ----------------------------------------------------------------------------

class SuggestionList( object ):
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
        Initializes the SuggestionList.
        """
        super(SuggestionList, self).__init__()

        self.__cmdManager = commandManager

        # Set all of the member variables to their empty values.
        self.clearState()


    def clearState( self ):
        """
        Clears all of the variables relating to the state of the
        quasimode's generated information.
        """

        # The "user text".  Together with the active index, constitutes
        # the "source" information, i.e., the information from which
        # all the rest is calculated.
        self.__userText = ""
        self.__userTextPrefix = ""

        # An index of the above suggestion list indicating which
        # command name the user has indicated.
        self.__activeIndex = 0

        # The current auto-completion object.
        self.__autoCompletion = AutoCompletion( originalText = "",
                                                suggestedText = "" )

        # The current list of suggestions. The 0th element is the
        # auto-completion.
        self.__suggestions = [ self.__autoCompletion ]

        # Did-you-mean hint
        self.__didyoumean_hint = None

        self.__activeCommand = None

        # A boolean telling whether the suggestion list and
        # auto-completion attributes above need to be updated.
        self.__isDirty = False


    def getUserText( self, prefixed=False ):
        if prefixed and self.__userTextPrefix:
            return self.__userTextPrefix + " " + self.__userText
        else:
            return self.__userText


    def getSuggestedTextPrefix( self ):
        return self.__userTextPrefix


    def setUserText( self, text ):
        """
        Sets the user text based on the value of text.

        NOTE: The stored user text may not be simply a copy of text
        typed by the user; for example, multiple contiguous spaces in
        text may be reduced to a single space.
        """

        # Only single spaces are allowed in the user text; additional
        # spaces are ignored.
        while text.find( " "*2 ) != -1:
            text = text.replace( " "*2, " " )

        is_dirty = (text != self.__userText)

        self.__userText = text

        if is_dirty:
            # One of the source variables has changed.
            self.__markDirty()


    def setSuggestedTextPrefix( self, textPrefix ):
        """
        Sets the user text prefix.
        The prefix is calculated and provided programatically.
        """

        is_dirty = (textPrefix != self.__userTextPrefix)

        self.__userTextPrefix = textPrefix

        if is_dirty:
            # One of the source variables has changed.
            self.__markDirty()


    def autoType( self ):
        """
        Sets the stored user text to the value indicated by the
        current autocompleted suggestion.
        """

        self.__update()

        completion = self.__suggestions[ self.__activeIndex ]
        if completion == None:
            return

        completion = completion.toText()
        if len(completion) == 0:
            return
        self.__userText = completion

        # One of the source variables has changed.
        self.resetActiveSuggestion()
        self.__markDirty()


    def getDidyoumeanHint( self ):
        return self.__didyoumean_hint


    def setDidyoumeanHint( self, hint ):
        is_dirty = (hint != self.__didyoumean_hint)

        self.__didyoumean_hint = hint

        if is_dirty:
            # One of the source variables has changed.
            self.__markDirty()


    def __update( self ):
        """
        While not good general coding style, this method deliberately
        encapsulates all the calls necessary to update the internal
        suggestion list and auto-completion objects, as such calls (by
        their nature) involve a fair amount of string processing and can
        be performance sensitive.

        It updates the __suggestions and __autoCompletion attributes
        to reflect the current userText.
        """

        if not self.__isDirty:
            return
            
        # NOTE: in the next line, ".lstrip()" is called because the
        # autcompletions hould ignore heading whitespace.
        # Leaving the trailing space intact so we can indicate it by dot
        # in special cases (user typing command parameter).
        self.__autoCompletion = self.__autoComplete(
            self.getUserText().lstrip()
            )
        # NOTE: in the next line, ".strip()" is called because the
        # suggestions should ignore trailing whitespace.
        self.__suggestions = self.__findSuggestions(
            self.getUserText().strip()
            )
        # We need to verify that it is a valid index; if the
        # namespace changed, then the suggestionss in the above
        # getSuggestions() line might be different than the
        # suggestions were the last time the active index was
        # updated.
        maxIndex = max( [ len(self.__suggestions)-1, 0 ] )
        self.__activeIndex = min( [self.__activeIndex, maxIndex] )

        activeCommandName = self.__suggestions[self.__activeIndex].toText()
        if not activeCommandName:
            self.__activeCommand = None
        else:
            self.__activeCommand = self.__cmdManager.getCommand( activeCommandName )

        self.__isDirty = False


    def __autoComplete( self, userText ):
        """
        Uses the CommandManager to determine if userText auto-completes
        to a command name, and what that command name is.

        Returns an AutoCompletion object; if the AutoCompletion object
        is empty (i.e., the text representation has 0 length), then there
        was no valid auto-completed command name.
        """

        if len( userText ) < config.QUASIMODE_MIN_AUTOCOMPLETE_CHARS:
            autoCompletion = AutoCompletion( userText, "" )
        else:
            autoCompletion = self.__cmdManager.autoComplete( userText )
            if autoCompletion is None:
                autoCompletion = AutoCompletion( userText, "" )

        return autoCompletion


    def __findSuggestions( self, userText ):
        """
        Uses the command manager to determine if there are any inexact
        but near matches of command names to userText.

        Returns a complete suggestion list, where the 0th element is
        the auto-completion, and each subsequent element (if any) is a
        suggestion different than the autocompletion for a command
        name that is similar to userText.
        """
        # FIXME: Avoid this function to have side effects, refactor! It belongs to __update() method

        if len( userText ) < config.QUASIMODE_MIN_AUTOCOMPLETE_CHARS:
            return [ self.__autoCompletion ]

        # Cache current autocompletion
        auto = self.__autoCompletion

        # If no command matches the user text, offer "open <usertext>" variant
        # as the autocompletion
        if not auto.hasCompletion():
            #TODO: Handle this dynamically 
            if ((userText[0].isdigit() or userText[0] in ("+", "-", ".", "=", "("))
                and not userText.startswith("calculate ")):
                _a = self.__autoComplete("calculate %s" % userText)
                if _a.hasCompletion():
                    auto = _a
                    userText = "calculate %s" % userText
                    self.setUserText(userText)
                    self.setSuggestedTextPrefix("calculate")
            #TODO: Handle this dynamically 
            elif (config.QUASIMODE_SUGGEST_OPEN_COMMAND_IF_NO_OTHER_MATCH
                and not userText.startswith("open ")):
                _a = self.__autoComplete("open %s" % userText)
                if _a.hasCompletion():
                    auto = _a
                    userText = "open %s" % userText
                    self.setUserText(userText)
                    self.setSuggestedTextPrefix("open")

        # Get N top suggestions based on nearness
        # __cmp__() function on Suggestion object takes care of proper sort 
        suggestions = nsmallest(
            # Get max+1 as the auto-completion can appear in the suggestions 
            # list and we will remove it later
            config.QUASIMODE_MAX_SUGGESTIONS + 1,   
            self.__cmdManager.retrieveSuggestions( userText )
        )

        # Remove the auto-completion entry from the list
        try:
            suggestions.remove(auto)
        except ValueError:
            # Shrink to QUASIMODE_MAX_SUGGESTIONS if not found
            if len(suggestions) > 0:
                del suggestions[-1]

        if len(suggestions) < config.QUASIMODE_MAX_SUGGESTIONS:
            if (config.QUASIMODE_APPEND_OPEN_COMMAND or len(suggestions) == 0) and not userText.startswith("open "):
                opencmd_suggestions = nsmallest(
                    config.QUASIMODE_MAX_SUGGESTIONS - len(suggestions), 
                    self.__cmdManager.retrieveSuggestions("open %s" % userText) 
                )
                if opencmd_suggestions:
                    suggestions.extend(opencmd_suggestions)
                else:
                    pass

        # Make auto-completion the first entry
        suggestions.insert(0, auto)

        return suggestions


    def markDirty( self ):
        self.__isDirty = True


    def __markDirty( self ):
        """
        Sets an internal variable telling the class that the suggestion list
        is "dirty", and should be updated before returning any information.
        """

        self.__isDirty = True


    def getSuggestions( self ):
        """
        In a pair with getAutoCompletion(), this method gets the latest
        suggestion list, making sure that the internal variable is
        updated.
        """

        self.__update()

        return self.__suggestions


    def getAutoCompletion( self ):
        """
        In a pair with getSuggestions(), this method gets the latest
        auto-completion, making sure that the internal variable is updated.
        """

        self.__update()

        return self.__autoCompletion


    def getDescription( self ):
        """
        Determines and returns the description for the currently
        active command.
        """

        active_cmd = self.getActiveCommand()

        if active_cmd is None:
            if len( self.getAutoCompletion().getSource() ) \
                   < config.QUASIMODE_MIN_AUTOCOMPLETE_CHARS:
                # The user hasn't typed enough to match a command.
                descText = config.QUASIMODE_DEFAULT_HELP
            else:
                # There is no command to match the user's text.
                descText =  config.QUASIMODE_NO_COMMAND_HELP
        else:
            # The active index is more than one, so one of the elements
            # of the suggestion list is active, and we are assured
            # that the active command exists.
            descText = active_cmd.getDescription()

        descText = descText.strip()

        # Postcondition
        assert len(descText) > 0

        return descText


    def getActiveCommand( self ):
        """
        Returns the active command, i.e., the command object that
        implements the command that is currently indicated to the
        user, either as the auto-completed command, or as a highlighted
        element on the suggestion list.  If there is no active command,
        then the function returns None.
        """

        self.__update()
        return self.__activeCommand


    def getActiveCommandName( self ):
        """
        Determines the command name of the "active" command, i.e., the
        name that is indicated to the user as the command that will
        be activated on exiting the quasimode.
        """

        self.__update()
        return self.__suggestions[self.__activeIndex].toText()


    def cycleActiveSuggestion( self, distance ):
        """
        Changes which of the suggestions is "active", i.e., which suggestion
        will be activated when the user releases the CapsLock key.

        Used to implement the up/down arrow key behavior.
        """

        self.__activeIndex += distance
        if len( self.getSuggestions() ) > 0:
            truncateLength = len( self.getSuggestions() )
            self.__activeIndex = self.__activeIndex % truncateLength
        else:
            self.__activeIndex = 0
        # One of the source variables has changed.
        self.__markDirty()
        return self.__activeIndex


    def getActiveIndex( self ):
        return self.__activeIndex


    def resetActiveSuggestion( self ):
        """
        Sets the active suggestion to 0, i.e., the user's
        text/auto-completion.
        """

        self.__activeIndex = 0
        # One of the source variables has changed.
        self.__markDirty()
