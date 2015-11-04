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

# TODO: Setup proxy in configuration

# ----------------------------------------------------------------------------
#
#   enso.commands.mixins
#
# ----------------------------------------------------------------------------

"""
    A couple useful mixins for use in commands.

"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import time
import threading
import urllib2
import logging

from contextlib import closing

from enso.commands import abstractmethod
from enso import config

# ----------------------------------------------------------------------------
# Private Utility Functions
# ----------------------------------------------------------------------------

# Force no-proxy initially. Can be overriden by config setting HTTP_PROXY_URL
urllib2.install_opener(
    urllib2.build_opener(
        urllib2.ProxyHandler({})
    )
)


# ----------------------------------------------------------------------------
# Prefix Command Factory
# ----------------------------------------------------------------------------

class CommandParameterWebSuggestionsMixin( object ):
    """
    CommandParameterWebSuggestionsMixin provides web-query based suggestions
    ability for an Enso command object.
    It can be used in commands that implement ArbitraryPostfixFactory.

    Two abstract methods must be overriden:

    getSuggestionsUrl()
    decodeSuggestions()

    This mixin monitors typed parameters text and queries specified web URL 
    (returned by getSuggestionsUrl() method) for suggestions.
    If any suggestions are returned and parsed (by decodeSuggestions() method),
    it will show the command suggestions (calls setParameterSuggestions() of
    ArbitraryPostfixFactory).
    
    TODO:
        * Start suggestion thread everytime suggestions should be active and exit
        it as soon as quasimode is off
    """

    #__queries_queue = Queue.Queue()
    __suggestion_thread = None
    __last_text_for_suggestions = None


    @abstractmethod
    def getSuggestionsUrl( self, text ):
        """
        Override this method.

        It must return URL for suggestions query based on given text.
        This method is called each time the command parameter text is changed.
        It can return either URL as a string, or urllib2.Request instance.

        Return None to suppress the suggestions query for given text.

        Example (implementing google suggest, simplified):

          query = urllib.quote_plus(text.encode("ISO-8859-1"))
          return "http://clients1.google.com/complete/search?hl=en&gl=en&client=firefox&q=%s" % query

        """
        pass


    @abstractmethod
    def decodeSuggestions( self, data, headers=None ):
        """
        Override this method.

        It must parse data returned by suggestions URL query
        and return the suggestions as list of strings.

        Example (implementing google suggest, simplified):

          json_data = json.loads( data.decode("ISO-8859-1") )
          if json_data and len(json_data) > 1 and json_data[1]:
              return = json_data[1]
          else:
              return []

        """
        pass


    def onSuggestQueryError( self, url_or_request, exception ):
        pass


    def onParameterModified(self, keyCode, oldText, newText):
        """
        This method is called automatically whenever the command parameter text
        changes, i.e. when user is typing or deleting the parameter text.
        (These calls are performed from quasimode module on every command that
        implements this method)

        It will initialize the suggestion-thread if and feed it with changed text.
        """
        #if not self.do_suggestions:
        #    return

        # If new text is empty, parameter text has been deleted, so also clear
        # the suggestions list
        if len(newText) == 0:
            self.__typed_text = newText
            self.setParameterSuggestions([])
            #self.quasimode.setParameterSuggestions(None)
            #self.__parameterSuggestions = None
            #self.__last_text_for_suggestions = None
            return

        """
        if keyCode == input.KEYCODE_TAB and self.__last_text_for_suggestions:
            self.quasimode.setParameterSuggestions(None)
            self.quasimode.replaceText(self.__last_text_for_suggestions)
            self.quasimode.forceRedraw()
            self.__last_text_for_suggestions = None
            return
        """
        # Cache recently typed text
        self.__typed_text = newText
        #self.__queries_queue.put_nowait(newText)
        # Initialize the suggestions thread is not yet started
        if self.__suggestion_thread is None:
            self.__suggestion_thread = threading.Thread(target=self.__suggest_thread)
            self.__suggestion_thread.setDaemon(True)
            self.__suggestion_thread.start()


    def __suggest_thread(self):
        last_query_time = 0
        last_typed_text = None
        while 1:
            time.sleep(0.01)
            """
            try:
                text = self.__queries_queue.get_nowait()
                self.__queries_queue.task_done()
                print "QUEUE GET SUCCESS: %s" % text
            except Queue.Empty:
                continue
            except Exception, e:
                print e
                continue

            while 1:
                try:
                    t = self.__queries_queue.get_nowait()
                    if t:
                        text = t
                        print "SKIPPED, QUEUE GET SUCCESS: %s" % text
                    self.__queries_queue.task_done()
                except Queue.Empty:
                    break
                except Exception, e:
                    print e
                    continue
            """
            now = time.time()
            if now - last_query_time < 0.100:
                continue
            text = self.__typed_text
            if text != last_typed_text:
            #if text != self.__last_text_for_suggestions:
                suggestions = self.__suggest(text)
                last_typed_text = text
                last_query_time = now
                if suggestions:
                    self.__last_text_for_suggestions = text
                    self.setParameterSuggestions(suggestions)
                    #self.quasimode.forceRedraw()
            else:
                pass


    def __suggest(self, text):
        try:
            url_or_request = self.getSuggestionsUrl( text )
            if not url_or_request:
                return None
        except Exception, e:
            logging.error("Getting the suggestion url/request failed: %s", e)
            return None

        suggestions = []
        data = None

        if not hasattr(self, "_http_opener"):
            if hasattr(config, "HTTP_PROXY_URL") and config.HTTP_PROXY_URL is not None:
                if config.HTTP_PROXY_URL == "":
                    # Force no-proxy
                    proxy_handler = urllib2.ProxyHandler({})
                else:
                    proxy_handler = urllib2.ProxyHandler({"http":config.HTTP_PROXY_URL})
                    self._http_opener = urllib2.build_opener(proxy_handler)
            else:
                self._http_opener = urllib2.build_opener()

        try:
            with closing(self._http_opener.open(url_or_request, timeout=1)) as resp:
                data = resp.read()
        except Exception, e:
            logging.error("Suggest query failed: %s; url: %s", e, url_or_request)
            self.onSuggestQueryError(url_or_request, e)
        else:
            if data:
                try:
                    suggestions = self.decodeSuggestions(data, resp.headers)
                except Exception, e:
                    logging.error("Suggest response parsing failed: %s", e)

        return suggestions
