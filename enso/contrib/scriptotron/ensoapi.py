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

from os.path import expanduser
import tracker
from xml.sax.saxutils import escape as xml_escape

from enso.messages import displayMessage as display_xml_message, hideMessage
from enso import selection


class EnsoApi(object):
    """
    A simple facade to Enso's functionality for use by commands.
    """

    def display_message(self, msg, caption=None,
                        show_mini_msg=False, mini_msg=None,
                        primary_wait=None, mini_wait=None):
        """
        Displays the given message, with an optional caption.  Both
        parameters should be unicode strings.

        If mini_msg argument is not empty, mini-message is shown after
        primary-message disappears.

        If show_mini_msg argument is True, and mini_msg argument is not set,
        mini-message is shown after primary-message disappears, with
        text specified in the msg argument.

        Optional to_wait argument specifies how many seconds mini-message
        will stay on screen. It is set to None by default (wait until
        user dismiss the mini messages using 'hide mini messages' command).
        """

        if not isinstance(msg, basestring):
            msg = unicode(msg)

        if caption and not isinstance(caption, basestring):
            caption = unicode(caption)

        if mini_msg and not isinstance(mini_msg, basestring):
            mini_msg = unicode(mini_msg)

        xmltext = "<p>%s</p>" % xml_escape(msg)
        if caption:
            caption_escaped = xml_escape(caption)
            xmltext += "<caption>%s</caption>" % caption_escaped
        xmltext_mini = None
        if show_mini_msg or mini_msg is not None:
            if mini_msg is None:
                xmltext_mini = xmltext
            else:
                xmltext_mini = "<p>%s</p>" % xml_escape(mini_msg)
                if caption:
                    xmltext_mini += "<caption>%s</caption>" % caption_escaped
        return display_xml_message(
            xmltext, miniMsgXml=xmltext_mini,
            primaryWaitTime=primary_wait, miniWaitTime=mini_wait)

    def display_xml_message(self, msg_xml, show_mini_msg=False,
                            mini_msg_xml=None, primary_wait=None, mini_wait=None):
        """
        Displays the given message, with an optional caption.  Both
        parameters should be unicode strings.

        If mini_msg argument is not empty, mini-message is shown after
        primary-message disappears.

        If show_mini_msg argument is True, and mini_msg argument is not set,
        mini-message is shown after primary-message disappears, with
        text specified in the msg argument.

        Optional to_wait argument specifies how many seconds mini-message
        will stay on screen. It is set to None by default (wait until
        user dismiss the mini messages using 'hide mini messages' command).
        """

        if not isinstance(msg_xml, basestring):
            msg_xml = unicode(msg_xml)

        if mini_msg_xml and not isinstance(mini_msg_xml, basestring):
            mini_msg_xml = unicode(mini_msg_xml)

        return display_xml_message(
            msg_xml, miniMsgXml=mini_msg_xml,
            primaryWaitTime=primary_wait, miniWaitTime=mini_wait)

    def hide_message(self, skip_animation=False):
        hideMessage(skip_animation)

    def get_selection(self):
        """
        Retrieves the current selection and returns it as a
        selection dictionary.
        """
        return selection.get()

    def get_text_selection(self, default=None):
        """
        Retrieves the current text selection as string.
        Returns default if nothing is selected.
        """
        return selection.get().get("text", default)

    def set_selection(self, seldict):
        """
        Sets the current selection to the contents of the given
        selection dictionary.

        Alternatively, if a string is provided instead of a
        dictionary, the current selection is set to the unicode
        contents of the string.
        """

        if isinstance(seldict, basestring):
            seldict = {"text": unicode(seldict)}
        return selection.set(seldict)

    @staticmethod
    def get_enso_commands_folder():
        """
        Returns the location of the Enso scripts folder.
        """
        return expanduser(tracker.getScriptsFolderName())

    @staticmethod
    def get_commands_from_text(text):
        """
        Given a block of Python text, returns all the valid Enso
        commands defined therein.
        """
        from cmdretriever import getCommandsFromObjects
        execGlobals = {}
        exec text in execGlobals
        commands = getCommandsFromObjects(execGlobals)
        return commands
