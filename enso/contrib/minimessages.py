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
#   enso.contrib.minimessages
#
# ----------------------------------------------------------------------------

"""
    An Enso plugin that makes all mini-messages related commands available.
    Commands:
        hide mini messages

"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from xml.sax.saxutils import escape as xml_escape

import enso.messages

from enso.commands import CommandManager, CommandObject
from enso.commands.factories import ArbitraryPostfixFactory
from enso.messages import MessageManager, TimedMiniMessage
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.ensoapi import EnsoApi

ensoapi = EnsoApi()



# ----------------------------------------------------------------------------
# The 'hide mini messages' command
# ---------------------------------------------------------------------------

class HideMiniMessagesCommand( CommandObject ):
    """
    The 'hide mini messages' command.
    """

    NAME = "hide mini messages"
    DESCRIPTION = "Hides all mini messages."

    def __init__( self ):
        super( HideMiniMessagesCommand, self ).__init__()
        self.setDescription( self.DESCRIPTION )
        self.setName( self.NAME )

    @safetyNetted
    def run( self ):
        MessageManager.get().finishMessages()


# ----------------------------------------------------------------------------
# The 'show mini message' testing command
# ---------------------------------------------------------------------------

class ShowMiniMessageCommand( CommandObject ):
    """
    The 'show mini message {text}' command.
    """

    LOREMIPSUM = u"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "\
    "Nunc fringilla ipsum dapibus mi porta et laoreet turpis porta. Class aptent "\
    "taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. "\
    "Duis commodo massa nec arcu mollis auctor. Nunc et orci quis lacus suscipit "\
    "dictum eu vitae est. Donec neque massa, pretium sed venenatis sed, consequat "\
    "quis est. Proin auctor consequat euismod. Praesent iaculis placerat libero eu "\
    "gravida. Curabitur ullamcorper velit sit amet tortor fermentum fringilla. "\
    "Pellentesque non lectus mauris, a iaculis ipsum. Cum sociis natoque penatibus "\
    "et magnis dis parturient montes, nascetur ridiculus mus. Vivamus mauris nibh, "\
    "ultrices in accumsan in, bibendum sed mi. Ut ut nunc a mi vestibulum luctus. "\
    "Sed ornare euismod justo a condimentum."

    def __init__(self, postfix):
        super( ShowMiniMessageCommand, self ).__init__()

        self._postfix = postfix
        self._msgmanager = MessageManager.get()

    @safetyNetted
    def run(self):
        import random

        text = self._postfix

        if text and "," in text:
            timeout, text = text.split(",")
            timeout = max(int(timeout), 0)
        else:
            timeout = None

        if not text:
            pos = random.randint(0, self.LOREMIPSUM.count(" ") - 10 + 1)
            cnt = random.randint(5, 10)
            words = self.LOREMIPSUM.split()
            text = " ".join(words[pos:pos+cnt])
            if text[0].upper() != text[0]:
                text = "..." + text
            if text[-1] != ".":
                text = text + "..."

        if timeout:
            caption = "test message (timed %ds)" % timeout
        else:
            caption = "test message"

        msg = xml_escape(text)
        caption = xml_escape(caption)

        if caption:
            xmltext = u"<p>%s</p><caption>%s</caption>" % (msg, caption)
        else:
            xmltext = u"<p>%s</p>" % (msg)

        msg = TimedMiniMessage(
            primaryXml = None,
            miniXml = xmltext,
            waitTime = timeout
        )
        self._msgmanager.newMessage( msg )


class ShowMiniMessageFactory( ArbitraryPostfixFactory ):
    """
    Generates a "show mini message {text}" command.
    """

    PREFIX = "show mini message "
    DESCRIPTION = "Show mini message with given timeout and text, both optional."
    HELP_TEXT = "{timeout,text}"
    NAME = "%s%s" % (PREFIX, HELP_TEXT)

    def _generateCommandObj( self, postfix ):
        cmd = ShowMiniMessageCommand( postfix )
        cmd.setDescription( self.DESCRIPTION )
        cmd.setName( self.NAME )
        cmd.setHelp( self.HELP_TEXT )
        return cmd


class ShowRecentMessageCommand( CommandObject ):
    """
    The 'show recent message' command.
    """

    NAME = "show recent message"
    DESCRIPTION = "Show recent message."

    def __init__( self ):
        super( ShowRecentMessageCommand, self ).__init__()
        self.setDescription( self.DESCRIPTION )
        self.setName( self.NAME )

    @safetyNetted
    def run( self ):
        if not enso.messages.displayRecentMessage():
            ensoapi.display_message(u"No recent messages.")


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    cmdMan = CommandManager.get()
    cmdMan.registerCommand(
        HideMiniMessagesCommand.NAME,
        HideMiniMessagesCommand()
        )
    cmdMan.registerCommand(
        ShowMiniMessageFactory.NAME,
        ShowMiniMessageFactory()
        )
    cmdMan.registerCommand(
        ShowRecentMessageCommand.NAME,
        ShowRecentMessageCommand()
        )

# vim:set tabstop=4 shiftwidth=4 expandtab: