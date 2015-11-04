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
#   enso.contrib.recentresults
#
# ----------------------------------------------------------------------------

"""
    An Enso plugin that makes 'put' command available.
    Put command pastes the result of last command (if that command supports it)
    For instance the results of 'calculate' command works with 'put'. 

"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from xml.sax.saxutils import escape as xml_escape

from enso.commands import CommandManager, CommandObject
from enso.messages import MessageManager, ConditionMiniMessage
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.ensoapi import EnsoApi
from enso import selection

ensoapi = EnsoApi()


# ----------------------------------------------------------------------------
# The RecentResult singleton calss providing access to recent command results,
# handling displaying of accompanying mini messages.
# ---------------------------------------------------------------------------

class RecentResult( object ):

    __instance = None

    @classmethod
    def get(cls):
        if cls.__instance is None:
            cls.__instance = RecentResult()
        return cls.__instance

    def __init__(self):
        self.__recent_result = None
        self.__result_popped = False

    def push_result(self, result, msg):
        assert msg

        self.__recent_result = result
        self.__result_popped = False

        msg = xml_escape(msg)
        caption = u"Use <command>put</command> command to paste result into your text."

        if caption:
            xmltext = u"<p>%s</p><caption>%s</caption>" % (msg, caption)
        else:
            xmltext = u"<p>%s</p>" % (msg)

        msg = ConditionMiniMessage(
            primaryXml = xmltext,
            miniXml = xmltext,
            is_finished_func = self._poll_recent_result
        )

        MessageManager.get().newMessage( msg )

    def pop_result(self):
        self.__result_popped = True
        return self.__recent_result

    def get_result(self):
        return self.__recent_result

    def _poll_recent_result(self):
        return self.__result_popped


# ----------------------------------------------------------------------------
# The 'put' command
# ---------------------------------------------------------------------------

class PutCommand( CommandObject ):
    """
    The 'put' command.
    """

    NAME = "put"
    DESCRIPTION = "Puts the result of a recent command into your text."

    def __init__( self ):
        super( PutCommand, self ).__init__()
        self.setDescription( self.DESCRIPTION )
        self.setName( self.NAME )

    @safetyNetted
    def run( self ):
        result = RecentResult.get().get_result()

        if result is None:
            ensoapi.display_message(u"Nothing to put!")
            return

        pasted = selection.set({"text":unicode(result)})
        print pasted
        if not pasted:
            ensoapi.display_message(u"Can't paste the text here!")
        else:
            # Trigger disappearing of mini-message
            _ = RecentResult.get().pop_result()


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    cmdMan = CommandManager.get()
    cmdMan.registerCommand(
        PutCommand.NAME,
        PutCommand()
        )

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: