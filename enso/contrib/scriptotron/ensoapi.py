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
#   enso
#
# ----------------------------------------------------------------------------

import xml.sax.saxutils
import os
import tracker

from enso.messages import displayMessage
from enso import selection



class EnsoApi(object):
    """
    A simple facade to Enso's functionality for use by commands.
    """

    def display_message(self, msg, caption=None):
        """
        Displays the given message, with an optional caption.  Both
        parameters should be unicode strings.
        """

        if not isinstance(msg, basestring):
            msg = unicode(msg)

        msg = xml.sax.saxutils.escape(msg)
        xmltext = "<p>%s</p>" % msg
        if caption:
            caption = xml.sax.saxutils.escape(caption)
            xmltext += "<caption>%s</caption>" % caption
        return displayMessage(xmltext)

    def get_selection(self):
        """
        Retrieves the current selection and returns it as a
        selection dictionary.
        """

        return selection.get()

    def set_selection(self, seldict):
        """
        Sets the current selection to the contents of the given
        selection dictionary.

        Alternatively, if a string is provided instead of a
        dictionary, the current selection is set to the unicode
        contents of the string.
        """

        if isinstance(seldict, basestring):
            seldict = { "text" : unicode(seldict) }
        return selection.set(seldict)

    def get_enso_commands_folder(self):
        """
        Returns the location of the Enso scripts folder.
        """
        return os.path.expanduser(tracker.getScriptsFolderName())


    def get_commands_from_text(self, text):
        """
        Given a block of Python text, returns all the valid Enso
        commands defined therein.
        """
        from cmdretriever import getCommandsFromObjects
        execGlobals = {}
        exec text in execGlobals
        commands = getCommandsFromObjects( execGlobals )
        return commands 

