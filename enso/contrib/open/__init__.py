# -*- coding: utf-8 -*-
# vim:set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
#
# Author : Pavel Vitis "blackdaemon"
# Email  : blackdaemon@seznam.cz
#
# Copyright (c) 2010, Pavel Vitis <blackdaemon@seznam.cz>
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
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso.contrib.open
#
# ----------------------------------------------------------------------------

"""
An Enso plugin providing the 'open', 'open with', 'learn as open',
'unlearn open', 'undo unlearn open' commands.

This is main class implementing all basic command functionality, without
platform specific code.

For platform specific code, platform command implementation is called.
See open_command_impl initialization in load():

  global open_command_impl
  # Import platform specific implementation class
  # This imports and initializes
  # enso.contrib.open.platform.<platform_name>.OpenCommandImpl class:

  open_command_impl = enso.contrib.platform.get_command_platform_impl("open")()

And then for platform specific task, methods of open_command_impl class are
called:

  open_command_impl.save_shortcut()

To tweak platform-specific code, see the implementations of OpenCommandImpl
class in open-command platform directories:

  enso.contrib.open.platform.win32
  enso.contrib.open.platform.osx
  enso.contrib.open.platform.linux

TODO:
    * Implement OSX variant
    * Open multiple files. Special text file .enrosun should be created
      in the LEARN_AS_DIR with the list of files to open(?)
      Or maybe create subdirectory in LEARN_AS_DIR and put multiple links there.
    * It should be possible to unlearn even any of desktop/startmenu/quicklaunch
      shortcuts. But we do not want to invasively remove items from desktop/
      startmenu/quicklaunch on unlearn.
      Implement this using LEARN_AS_DIR/.unlearned subdirectory to remember
      such unlearned shortcuts.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

# Future imports
from __future__ import with_statement

# Imports
import os
import logging
import sys
from xml.sax.saxutils import escape as xml_escape

# Enso imports
from enso.commands import CommandManager, CommandObject
from enso.commands.factories import ArbitraryPostfixFactory, GenericPrefixFactory
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.utils.memoize import memoized
from enso.events import EventManager
from enso.contrib.scriptotron.ensoapi import EnsoApi

from enso.contrib.open import utils
from enso.contrib.open import shortcuts

import enso.contrib.platform

logger = logging.getLogger('enso.contrib.open')

# Platform specific command-implementation class. This is initialized in load().
open_command_impl = None
recent_command_impl = None
ensoapi = EnsoApi()

#def xml_escape(data):
#    """ Escape &, <, and > in a string of data """
#    # must do ampersand first
#    return data.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;")


# ----------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def display_xml_message(msg):
    import enso.messages
    enso.messages.displayMessage("<p>%s</p>" % msg)


# ----------------------------------------------------------------------------
# LearnAsOpen command
# ---------------------------------------------------------------------------

class LearnAsOpenCommand( CommandObject ):
    """ Learns to open a document or application as {name} """

    def __init__( self, postfix = None ):
        super( LearnAsOpenCommand, self ).__init__()
        self.name = postfix

    @safetyNetted
    def run( self ):
        with utils.Timer("get_selection"):
            seldict = ensoapi.get_selection()
        if seldict.get('files'):
            #TODO: Handle opening of multiple files
            file = seldict['files'][0]
        elif seldict.get('text'):
            file = seldict['text'].strip()
        else:
            ensoapi.display_message(u"No file is selected")
            return

        if self.name is None:
            from enso.contrib.open.platform.win32.utils import get_exe_name
            product_name = get_exe_name(file)
            if product_name:
                self.name = product_name.lower()
            else:
                ensoapi.display_message(u"You must provide name")
                return

        if (not os.path.isfile(file)
            and not os.path.isdir(file)
            and not open_command_impl._is_url(file)):
            ensoapi.display_message(
                u"Selection represents no existing file, folder or URL.")
            return

        shortcut = open_command_impl.add_shortcut(self.name, file)
        if shortcut:
            display_xml_message(u"<command>open %s</command> is now a command"
                % xml_escape(self.name))
        else:
            display_xml_message(
                u"<command>open %s</command> already exists. Please choose another name."
                % xml_escape(self.name))
            return



# ----------------------------------------------------------------------------
# Open command
# ---------------------------------------------------------------------------

class OpenCommand( CommandObject ):
    """ Opens application, file or folder referred by given name """

    def __init__( self, postfix = None ):
        super( OpenCommand, self ).__init__()
        self.target = postfix

    @safetyNetted
    def run( self ):
        #TODO: Implement opening current selection if no postfix provided?
        if not self.target:
            return

        display_xml_message(u"Opening <command>%s</command>..."
            % xml_escape(self.target))

        open_command_impl.run_shortcut(self.target)


# ----------------------------------------------------------------------------
# OpenWith command
# ---------------------------------------------------------------------------

class OpenWithCommand( CommandObject ):
    """ Opens your currently selected file(s) or folder with the specified application """

    def __init__( self, postfix = None ):
        super( OpenWithCommand, self ).__init__()
        self.target = postfix

    @safetyNetted
    def run( self ):
        seldict = ensoapi.get_selection()
        if seldict.get('files'):
            files = seldict['files']
        elif seldict.get('text'):
            text = seldict['text'].strip("\r\n\t\0 ").replace("\r", "\n").replace("\n\n", "\n")
            files = (file for file in text.split("\n"))
            files = [file for file in files if os.path.isfile(file) or os.path.isdir(file)]
        else:
            files = []

        if len(files) == 0:
            ensoapi.display_message(u"No file or folder is selected")
            return

        open_command_impl.open_with_shortcut(self.target, files)




# ----------------------------------------------------------------------------
# UnlearnOpen command
# ---------------------------------------------------------------------------

class UnlearnOpenCommand( CommandObject ):
    u""" Unlearn \u201copen {name}\u201d command """

    def __init__( self, postfix = None ):
        super( UnlearnOpenCommand, self ).__init__()
        self.target = postfix

    @safetyNetted
    def run( self ):
        open_command_impl.remove_shortcut(self.target)

        display_xml_message(u"Unlearned <command>open %s</command>" % self.target)


# ----------------------------------------------------------------------------
# UndoUnlearnOpen command
# ---------------------------------------------------------------------------

class UndoUnlearnOpenCommand( CommandObject ):
    """
    The "undo unlearn open" command.
    """

    NAME = "undo unlearn open"
    DESCRIPTION = "Undoes your last \u201cunlearn open\u201d command."

    def __init__( self ):
        super( UndoUnlearnOpenCommand, self ).__init__()
        self.setDescription( self.DESCRIPTION )
        self.setName( self.NAME )

    @safetyNetted
    def run( self ):
        sh = open_command_impl.undo_remove_shortcut()
        if sh:
            display_xml_message(
                u"Undo successful. <command>open %s</command> is now a command"
                % sh.name)
        else:
            ensoapi.display_message(u"There is nothing to undo")


# ----------------------------------------------------------------------------
# Recent command
# ---------------------------------------------------------------------------

class RecentCommand( CommandObject ):
    """ Opens recent application, file or folder referred by given name """

    def __init__( self, postfix = None ):
        super( RecentCommand, self ).__init__()
        self.target = postfix

    @safetyNetted
    def run( self ):
        #TODO: Implement opening current selection if no postfix provided?
        if not self.target:
            return

        display_xml_message(u"Opening <command>%s</command>..."
            % xml_escape(self.target))

        recent_command_impl.run_shortcut(self.target)


# ----------------------------------------------------------------------------
# Command factories
# ---------------------------------------------------------------------------

class LearnAsOpenCommandFactory( ArbitraryPostfixFactory ):
    """
    Generates a "learn as open {name}" command.
    """

    HELP_TEXT = "name"
    PREFIX = "learn as open "
    NAME = "%s{name}" % PREFIX
    DESCRIPTION = "Learn to open a document or application as {name}"

    def __init__( self ):
        """
        Instantiantes the command factory.

        Must be called by overriden constructors.
        """

        ArbitraryPostfixFactory.__init__( self )

    def _generateCommandObj( self, postfix ):
        cmd = LearnAsOpenCommand( postfix )
        cmd.setDescription(self.DESCRIPTION)
        return cmd


class OpenCommandFactory( GenericPrefixFactory ):
    """
    Generates a "open {name}" command.
    """

    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "open "
    NAME = "%s{name}" % PREFIX
    DESCRIPTION = "Continue typing to open an application or document"

    def _generateCommandObj( self, parameter = None ):
        cmd = OpenCommand( parameter )
        cmd.setDescription(self.DESCRIPTION)
        return cmd

    @safetyNetted
    def update(self):
        if not hasattr(self, "postfixes_updated_on"):
            self.postfixes_updated_on = 0

        shortcuts_dict = open_command_impl.get_shortcuts()
        if self.postfixes_updated_on < shortcuts_dict.updated_on:
            with utils.Timer("Setting postfixes for 'open' command."):
                self.setPostfixes(shortcuts_dict.keys())
            self.postfixes_updated_on = shortcuts_dict.updated_on


class OpenWithCommandFactory( GenericPrefixFactory ):
    """
    Generates a "open with {name}" command.
    """

    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "open with "
    NAME = "%s{name}" % PREFIX
    DESCRIPTION = "Opens your currently selected file(s) or folder with the specified application"

    def _generateCommandObj( self, parameter = None ):
        cmd = OpenWithCommand( parameter )
        cmd.setDescription(self.DESCRIPTION)
        return cmd

    @safetyNetted
    def update(self):
        if not hasattr(self, "postfixes_updated_on"):
            self.postfixes_updated_on = 0

        shortcuts_dict = open_command_impl.get_shortcuts()
        if self.postfixes_updated_on < shortcuts_dict.updated_on:
            with utils.Timer("Setting postfixes for 'open with' command."):
                self.setPostfixes(
                    [s.name for s in shortcuts_dict.values()
                     if s.type == shortcuts.SHORTCUT_TYPE_EXECUTABLE])
            self.postfixes_updated_on = shortcuts_dict.updated_on


class UnlearnOpenCommandFactory( GenericPrefixFactory ):
    """
    Generates a "unlearn open {name}" command.
    """

    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "unlearn open "
    NAME = "%s{name}" % PREFIX
    DESCRIPTION = u" Unlearn \u201copen {name}\u201d command "

    def _generateCommandObj( self, parameter = None ):
        cmd = UnlearnOpenCommand( parameter )
        cmd.setDescription(self.DESCRIPTION)
        return cmd

    @safetyNetted
    def update(self):
        if not hasattr(self, "postfixes_updated_on"):
            self.postfixes_updated_on = 0

        shortcuts_dict = open_command_impl.get_shortcuts()
        if self.postfixes_updated_on < shortcuts_dict.updated_on:
            with utils.Timer("Setting postfixes for 'unlearn open' command."):
                self.setPostfixes(shortcuts_dict.keys())
            self.postfixes_updated_on = shortcuts_dict.updated_on


class RecentCommandFactory( GenericPrefixFactory ):
    """
    Generates a "recent {name}" command.
    """

    HELP = "command"
    HELP_TEXT = "command"
    PREFIX = "recent "
    NAME = "%s{name}" % PREFIX
    DESCRIPTION = "Continue typing to open recent application or document"

    def _generateCommandObj( self, parameter = None ):
        cmd = RecentCommand( parameter )
        cmd.setDescription(self.DESCRIPTION)
        return cmd

    @safetyNetted
    def update(self):
        if not hasattr(self, "postfixes_updated_on"):
            self.postfixes_updated_on = 0

        shortcuts_dict = recent_command_impl.get_shortcuts()
        if self.postfixes_updated_on < shortcuts_dict.updated_on:
            with utils.Timer("Setting postfixes for 'recent' command."):
                self.setPostfixes(shortcuts_dict.keys())
            self.postfixes_updated_on = shortcuts_dict.updated_on


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    global open_command_impl, recent_command_impl
    # Import platform specific implementation class
    # This imports enso.contrib.open.platform.<platform_name>.OpenCommandImpl class.
    open_command_impl = enso.contrib.platform.get_command_platform_impl("open")()
    try:
        recent_command_impl = enso.contrib.platform.get_command_platform_impl("open", "RecentCommandImpl")()
    except:
        recent_command_impl = None
    
    # Register commands
    try:
        CommandManager.get().registerCommand(
            OpenCommandFactory.NAME,
            OpenCommandFactory()
            )
        CommandManager.get().registerCommand(
            OpenWithCommandFactory.NAME,
            OpenWithCommandFactory()
            )
        CommandManager.get().registerCommand(
            LearnAsOpenCommandFactory.NAME,
            LearnAsOpenCommandFactory()
            )
        CommandManager.get().registerCommand(
            UnlearnOpenCommandFactory.NAME,
            UnlearnOpenCommandFactory()
            )
        CommandManager.get().registerCommand(
            UndoUnlearnOpenCommand.NAME,
            UndoUnlearnOpenCommand()
            )
        if recent_command_impl:
            CommandManager.get().registerCommand(
                RecentCommandFactory.NAME,
                RecentCommandFactory()
                )
    except Exception, e:
        logger.critical(repr(e))

# ----------------------------------------------------------------------------
# Doctests
# ---------------------------------------------------------------------------

def test_evaluate():
    """
    Set up mock objects:

      >>> def mockDisplayMessage( text ):
      ...   print "message: %s" % text

      >>> class MockSelection( object ):
      ...   def set( self, seldict ):
      ...     print "set selection: %s" % seldict

    Initialize our command with the mock objects:

      >>> c = OpenCommand( mockDisplayMessage, MockSelection() )

    Ensure that the command works if nothing is selected:

      >>> c.run( {} )
      message: <p>No code to evaluate!</p>

    Ensure that the command works in the general case:

      >>> c.run( {'text' : u'5+3'} )
      set selection: {'text': u'8'}

    Ensure that the command works with syntax errors:

      >>> c.run( {'text' : u'5+'} )
      message: <p>Error: unexpected EOF while parsing (&lt;selected text&gt;, line 1)</p>

    Ensure that the command doesn't allow standard Python builtins to be used:

      >>> ec.run( {'text' : u'open("secretfile", "w")'} )
      message: <p>Error: name 'open' is not defined</p>
    """

    pass

if __name__ == "__main__":
    import doctest

    doctest.testmod()
