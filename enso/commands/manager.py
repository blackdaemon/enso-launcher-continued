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
#   enso.commands.manager
#
# ----------------------------------------------------------------------------

"""
    The CommandManager singleton.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import operator
import logging

from enso.commands.interfaces import CommandExpression, CommandObject
from enso.commands.interfaces import AbstractCommandFactory
from enso.commands.factories import GenericPrefixFactory
from enso import config


# ----------------------------------------------------------------------------
# The Command Manager
# ----------------------------------------------------------------------------

class CommandManager:
    """
    Provides an interface to register and retrieve all commands.

    Allows client code to register new command implementations, find
    suggestions, and retrieve command objects.
    """

    __instance = None

    @classmethod
    def get( cls ):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance

    CMD_KEY = CommandExpression( "{all named commands}" )

    def __init__( self ):
        """
        Initializes the command manager.
        """

        self.__cmdObjReg = CommandObjectRegistry()
        self.__cmdFactoryDict = {
            self.CMD_KEY : self.__cmdObjReg,
            }


    def registerCommand( self, cmdName, cmdObj ):
        """
        Called to register a new command with the command manager.
        """

        try:
            cmdExpr = CommandExpression( cmdName )
        except AssertionError, why:
            logging.error( "Could not register %s : %s "
                           % ( cmdName, why ) )
            raise

        if cmdExpr.hasArgument():
            # The command expression has an argument; it is a command
            # with an argument.
            assert isinstance( cmdObj, AbstractCommandFactory ), \
                "Command object with a parameter must be instance " \
                "of AbstractCommandFactory"
            assert hasattr(cmdObj, "PREFIX"), \
                "Missing attribute 'PREFIX' in the command object '%s'" % cmdName
            assert hasattr(cmdObj, "HELP_TEXT"), \
                "Missing attribute 'HELP_TEXT' in the command object '%s'" % cmdName
            assert cmdExpr not in self.__cmdFactoryDict,\
                "Command is already registered: %s" % cmdExpr
            self.__cmdFactoryDict[ cmdExpr ] = cmdObj
        else:
            # The command expression has no argument; it is a
            # simple command with an exact name.
            assert isinstance( cmdObj, CommandObject ), \
                   "Could not register %s. Object has not type CommandObject." % cmdName
            self.__cmdObjReg.addCommandObj( cmdObj, cmdExpr )


    def unregisterCommand( self, cmdName ):
        for cmdExpr in self.__cmdFactoryDict.keys(): # Need keys() to obtain copy so we can mutate
            if cmdExpr.getString() == cmdName and cmdExpr != self.CMD_KEY: # Protect cmdObjeReg from deletion
                del self.__cmdFactoryDict[cmdExpr]
                break
        else:
            self.__cmdObjReg.removeCommandObj( cmdName )
        assert self.CMD_KEY in self.__cmdFactoryDict


    def getCommandPrefix( self, commandName ):
        """
        Returns the unique command expression that is associated with
        commandName.  For example, if commandName is 'open emacs', and
        the command expression was 'open {file}', then a command expression
        object for 'open {file}' will be returned.
        """

        prefixes = []

        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( commandName ):
                # This expression matches commandName; try to fetch a
                # command object from the corresponding factory.
                cmd = factory.getCommandObj( commandName )
                if expr == self.CMD_KEY and cmd is not None:
                    prefixes.append( commandName )
                elif cmd is not None:
                    # The factory returned a non-nil command object.
                    # Make sure that nothing else has matched this
                    # commandName.
                    prefixes.append( expr.getPrefix() )

        if len(prefixes) == 0:
            return None
        elif len(prefixes) == 1:
            # There is exactly one match
            return prefixes[0]
        else:
            # There are more matches, choose the best one
            #prefixes_dict = dict(prefixes)
            # Try to find longest possible exact match first:

            longest_name = commandName
            # If there is no space at the end, it is a parameter there
            if not longest_name.endswith(' '):
                # Strip parameter off
                longest_name = longest_name[:longest_name.rfind(" ")]
            else:
                longest_name = longest_name.rstrip(" ")
            for _ in range(longest_name.count(" ") + 1):
                if longest_name+' ' in prefixes:
                    assert logging.debug("Command-prefix exact match: '%s'", longest_name) or True
                    return longest_name+' '
                longest_name = longest_name[:longest_name.rfind(" ")]

            # Longest match not found so return the alphabetically first
            return min(prefixes)
            

    def getCommandExpression( self, commandName ):
        """
        Returns the unique command expression that is associated with
        commandName.  For example, if commandName is 'open emacs', and
        the command expression was 'open {file}', then a command expression
        object for 'open {file}' will be returned.
        """

        expressions = []

        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( commandName ):
                # This expression matches commandName; try to fetch a
                # command object from the corresponding factory.
                cmd = factory.getCommandObj( commandName )
                if expr == self.CMD_KEY and cmd is not None:
                    expressions.append( ( commandName, commandName ) )
                elif cmd is not None:
                    # The factory returned a non-nil command object.
                    # Make sure that nothing else has matched this
                    # commandName.
                    expressions.append( (expr.getPrefix(), expr) )

        if len(expressions) == 0:
            return None
        elif len(expressions) == 1:
            # There is exactly one match
            return expressions[0][1]
        else:
            # There are more matches, choose the best one
            expressions_dict = dict(expressions)
            # Try to find longest possible exact match first:

            longest_name = commandName
            # If there is no space at the end, it is a parameter there
            if not longest_name.endswith(' '):
                # Strip parameter off
                longest_name = longest_name[:longest_name.rfind(" ")]
            else:
                longest_name = longest_name.rstrip(" ")
            for _ in range(longest_name.count(" ") + 1):
                expr = expressions_dict.get(longest_name+' ') 
                if expr:
                    assert logging.debug("Command-expression exact match for '%s': '%s'" % (longest_name, expr)) or True
                    return expr
                longest_name = longest_name[:longest_name.rfind(" ")]

            # Longest match not found so return the alphabetically first
            return min(expressions_dict, key=operator.itemgetter(0))[1]


    def getCommand( self, commandName ):
        """
        Returns the unique command with commandName, based on the
        registered CommandObjects and the registered CommandFactories.

        If no command matches, returns None explicitly.
        """

        commands = []

        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( commandName ):
                # This expression matches commandName; try to fetch a
                # command object from the corresponding factory.
                cmd = factory.getCommandObj( commandName )
                if cmd is not None:
                    # The factory returned a non-nil command object.
                    commands.append( ( expr, cmd ) )

        if len( commands ) == 0:
            # There is no match
            return None
        elif len( commands ) == 1:
            # There is exactly one match
            return commands[0][1]
        else:
            # There are more matches, choose the best one
            prefixes = [ (e.getPrefix(),c) for (e,c) in commands ]
            prefixes_dict = dict(prefixes)

            # Try to find longest possible exact match first:
            longest_name = commandName
            # If there is no space at the end, it is a parameter there
            if not longest_name.endswith(' '):
                # Strip parameter off
                longest_name = longest_name[:longest_name.rfind(" ")]
            else:
                longest_name = longest_name.rstrip(" ")
            for _ in range(longest_name.count(" ") + 1):
                cmd = prefixes_dict.get(longest_name+' ')
                if cmd:
                    assert logging.debug("Longest match: '%s'", longest_name) or True
                    return cmd
                longest_name = longest_name[:longest_name.rfind(" ")]

            # Longest match not found so return the alphabetically first
            return min(prefixes, key=operator.itemgetter(0))[1]


    def autoComplete( self, userText ):
        """
        TODO:Implement optional sorting by name and usage-frequency
        Returns the best match it can find to userText, or None.
        """

        completions = []

        # Check each of the command factories for a match.
        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( userText ):
                completion = factory.autoComplete( userText )
                if completion is not None:
                    completions.append( completion )

        if len( completions ) == 0:
            return None
        elif len( completions ) == 1:
            return completions[0]
        else:
            if userText.startswith("o") and config.PRIORITIZE_OPEN_COMMAND:
                # Special handling for 'open' command.
                for c in completions:
                    if c.toText() == "open ":
                        return c
            #Original:
            # Sort by nearness
            #completions.sort( lambda a,b : cmp( a.toText(), b.toText() ) )
            #return completions[0]
            return min(completions)


    # FIXME: Make this faster by implementing factory.hasSuggestions()
    # This is not used anywhere now
    def hasSuggestions( self, userText ):
        """
        Returns True if the userText yields any suggestions
        """
        raise NotImplementedError()
        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( userText ):
                if len(factory.retrieveSuggestions( userText )) > 0:
                    return True
        else:
            return False


    def retrieveSuggestions( self, userText ):
        """
        Returns an unsorted list of suggestions.
        """

        suggestions = []
        # Extend the suggestions using each of the command factories
        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr.matches( userText ):
                suggestions.extend(factory.retrieveSuggestions( userText ))

        return suggestions


    def getCommands( self ):
        """
        Returns a dictionary of command expression strings and their
        associated implementations (command objects or factories).
        """

        # Get a dictionary form of the command object registry:
        cmdDict = self.__cmdObjReg.getDict()

        # Extend the dictionary to cover the command factories.
        for expr, factory in self.__cmdFactoryDict.iteritems():
            if expr == self.CMD_KEY:
                # This is the command object registry; pass.
                pass
            else:
                # Cast the expression as a string.
                cmdDict[ str(expr) ] = factory

        return cmdDict


# ----------------------------------------------------------------------------
# A CommandObject Registry
# ----------------------------------------------------------------------------

class CommandAlreadyRegisteredError( Exception ):
    """
    Error raised when someone tries to register two commands under
    the same name with the registry.
    """

    pass


class CommandObjectRegistry( GenericPrefixFactory ):
    """
    Class for efficiently storing and searching a large number of
    commands (where each command is an object with a corresponding
    command name).
    """

    PREFIX = ""

    def __init__( self ):
        """
        Initialize the command registry.
        """

        GenericPrefixFactory.__init__( self )

        self.__cmdObjDict = {}
        self.__dictTouched = False

    def update( self ):
        pass

    def getDict( self ):
        return self.__cmdObjDict

    def addCommandObj( self, command, cmdExpr ):
        """
        Adds command to the registry under the name str(cmdExpr).
        """

        assert isinstance( cmdExpr, CommandExpression ),\
            "addCommandObj(): cmdExpr arg is not CommandExpression type"
        assert not cmdExpr.hasArgument()

        cmdName = str(cmdExpr)
        if cmdName in self.__cmdObjDict:
            raise CommandAlreadyRegisteredError()

        self.__cmdObjDict[ cmdName ] = command
        self.__dictTouched = True

        self._addPostfix( cmdName )


    def removeCommandObj( self, cmdExpr ):
        if cmdExpr in self.__cmdObjDict:
            del self.__cmdObjDict[cmdExpr]
            self.__dictTouched = True
            self._removePostfix( cmdExpr )
        else:
            raise RuntimeError( "Command object '%s' not found." % cmdExpr )



    def getCommandObj( self, cmdNameString ):
        """
        Returns the object corresponding to cmdNameString.

        NOTE: This will raise a KeyError if cmdNameString is not a
        valid command name.
        """

        try:
            return self.__cmdObjDict[ cmdNameString ]
        except KeyError:
            return None


    def _generateCommandObj( self, postfix ):
        """
        Virtual method for getting an actual command object.
        'postfix' is the name of the postfix supplied, if any.

        Must be overriden by subclasses.
        """
        return None


if __name__ == "__main__":
    import doctest

    doctest.testmod()


# vim:set tabstop=4 shiftwidth=4 expandtab:
