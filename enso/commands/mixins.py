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

import datetime
import logging
import threading
import urllib2
import urllib3
from abc import ABCMeta, abstractmethod
from Queue import Queue, Empty

from enso import config
from enso.commands.factories import ArbitraryPostfixFactory
from enso.contrib.scriptotron import EnsoApi
from enso.events import EventManager

from enso.utils.decorators import suppress

urllib3.disable_warnings()

# ----------------------------------------------------------------------------
# Constants and global variables
# ----------------------------------------------------------------------------

DEFAULT_SUGGESTIONS_POLLING_INTERVAL = 300

# Do not allow to go below this
_MINIMAL_SUGGESTIONS_POLLING_INTERVAL = 100

DEFAULT_HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0',
    #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'DNT': '1'
}


ENSOAPI = EnsoApi()
ENSO_COMMANDS_DIR = EnsoApi().get_enso_commands_folder()

# Whether caching shall be enabled
CACHING_ENABLED = True
cache_manager = None

if CACHING_ENABLED:
    try:
        from enso.commands.suggestions_cache.manager import CacheManager
        cache_manager = CacheManager.get()
    except ImportError as e:
        logging.error("Error importing cache manager, the web suggestions caching will not be available: %s" % str(e))
        cache_manager = None
        CACHING_ENABLED = False

__all__ = ['CommandParameterWebSuggestionsMixin']

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
# PersistentHTTPConnectionManager
# ----------------------------------------------------------------------------

class PersistentHTTPConnectionManager(object):
    """Peristent HTTP1.1 connection manager.
    
    Instantiate the manager and call get_connection() to get the persistent connection.
    The manager will open the connection on first call to get_connection() and then return
    the same connection on subsequent calls to get_connection() until
        - connection is closed by the server
        - "endQuasimode" event occurs
        - close_connections() is called
    in which case new connection is opened on next call to get_connection().
    """
    
    def __init__(self, url_or_request):
        self.url_or_request = url_or_request
        self._connection_pool = None
        self.__eventManager = EventManager.get()
        if isinstance(url_or_request, basestring):
            self._url = url_or_request
            self._headers = DEFAULT_HTTP_HEADERS
        else:
            self._url = url_or_request.get_full_url()
            self._headers = dict(url_or_request.header_items())
        # Force compression if not set by the caller
        # urllib3 auto-decompress the response data based on Content-Encoding header
        if "Accept-Encoding" not in self._headers and "accept-encoding" not in self._headers:
            self._headers["Accept-Encoding"] = "gzip, deflate"
       
    def get_connection(self):
        if not self.is_connected():
            try:
                # TODO: use proxy_from_url if proxy handling is needed
                self._connection_pool = urllib3.connection_from_url(self._url, timeout=1, headers=self._headers)
            except Exception as e:
                logging.error("Error getting persistent HTTP connection: %s", str(e))
            else:
                #print "persistent-connection endQuasimode responder registered"
                self.__eventManager.registerResponder(self._onEndQuasimode, "endQuasimode")
        return self._connection_pool

    def is_valid(self):
        return self._connection_pool is not None

    def is_connected(self):
        return self._connection_pool and self._connection_pool.num_connections > 0
        
    def num_connections(self):
        return self._connection_pool.num_connections if self._connection_pool else 0

    def num_requests(self):
        return self._connection_pool.num_requests if self._connection_pool else 0

    def close_connections(self):
        """Close any HTTP1.1 persistent connections and invalidate connection pool"""
        if self._connection_pool is not None:
            with suppress(Exception):
                #print "Closing current HTTP1.1 persistent connection"
                self._connection_pool.close()
            #print "Invalidating connection pool"
            self._connection_pool = None

    def _onEndQuasimode(self):
        """Close all connections on 'endQuasimode' event"""
        try:
            self.close_connections()
        finally:
            self.__eventManager.removeResponder(self._onEndQuasimode)


# ----------------------------------------------------------------------------
# CommandParameterWebSuggestionsMixin
# ----------------------------------------------------------------------------
 
class CommandParameterWebSuggestionsMixin(object):
    """CommandParameterWebSuggestionsMixin provides web-query based suggestions
    ability for an Enso command object. It can be used in commands that implement
    ArbitraryPostfixFactory.

    Two abstract methods which must be overriden:

    getSuggestionsUrl()
    decodeSuggestions()

    This mixin monitors typed parameters text and queries specified web URL
    (returned by getSuggestionsUrl() method) for suggestions.
    If any suggestions are returned and parsed (by decodeSuggestions() method),
    it will show the command suggestions (calls setParameterSuggestions() of
    ArbitraryPostfixFactory).
    """
    
    __metaclass__ = ABCMeta
    
    class _Impl(object):
        def __init__(self, caller):
            self.caller = caller
            self.polling_interval = max(DEFAULT_SUGGESTIONS_POLLING_INTERVAL, _MINIMAL_SUGGESTIONS_POLLING_INTERVAL)
            
            self.__suggestion_thread = None
            self.__stop_suggestion_thread = False
            self.__last_text_for_suggestions = None
            
            self._connection_manager = None
    
            self._update_queue = Queue()
            self.quasimodeId = 0.0
        
            self.__eventManager = EventManager.get()
            
            self._cache_id = None

        def setPollingInterval(self, interval_in_ms):
            self.polling_interval = interval_in_ms

        @property
        def cache_id(self):
            """
            Optionally set cacheId for cache manager.
            By default it is set to caller.__class__.__name__
            """
            if self._cache_id:
                return self._cache_id
            return self.caller.__class__.__name__

        @cache_id.setter
        def cache_id(self, value):
            self._cache_id = value

        def onParameterModified(self, keyCode, oldText, newText, quasimodeId=0.0):
            """This method is called automatically whenever the command parameter text
            changes, i.e. when user is typing or deleting the parameter text.
            (These calls are performed from quasimode module on every command that
            implements this method)
    
            It will first initialize the suggestion-thread and then feed it with changed text
            on subsequent calls.
            """
            self.quasimodeId = quasimodeId
            
            #if not self.do_suggestions:
            #    return
    
            # If new text is empty, parameter text has been deleted, so also clear
            # the suggestions list
            if len(newText) == 0:
                self.__typed_text = newText
                self.caller.setParameterSuggestions([])
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
    
            # Initialize the suggestions thread if not yet started
            self.__startSuggestionThread()
    
            self._update_queue.put_nowait(newText)
    
        def onEndQuasimode(self):
            """
            Stop suggestion thread on "endQuasimode" event
            """
            self.__eventManager.removeResponder(self.onEndQuasimode)
            self.__stopSuggestionThread()

        def __startSuggestionThread(self):
            """Start suggestion thread if not yet started.
            Register responder to stop the thread on "endQuasimode" event.
            """
            if self.__suggestion_thread is None:
                #print "Starting suggestion thread"
                self.__stop_suggestion_thread = False
                self.__suggestion_thread = threading.Thread(target=self.__suggestion_thread_func)
                #self.__suggestion_thread.setDaemon(True)
                self.__suggestion_thread.start()
                self.__eventManager.registerResponder(self.onEndQuasimode, "endQuasimode")
    
        def __stopSuggestionThread(self):
            """Issue stop request to the suggestion thread"""
            #print "Stopping suggestion thread"
            self.__stop_suggestion_thread = True
            # Provoke queue update with empty task so that suggestion thread unblocks
            self._update_queue.put_nowait(None)
            
        def __suggestion_thread_func(self):
            """Suggestions thread. This thread waits for text and if the text
            has changed between the calls, it calls the self.__suggest(text)
            function.
    
            It polls for text changes only every 100ms to avoid overloading
            of the webservice used for suggestions.
            """
            last_typed_text = None
            text = None
            self.__stop_suggestion_thread = False
    
            try:
                while not self.__stop_suggestion_thread:
                    # Act only on valid text.
                    if not text:
                        try:
                            # Blocking wait for first update request
                            text = self._update_queue.get(block=True)
                        finally:
                            self._update_queue.task_done()
                    # text == None is issued only on thread stop request in order to wakeup the initial
                    # blocking queue.get().
                    if text is None:
                        continue
                    if text != last_typed_text:
                        # If text differs, get the suggestions from webservice
                        suggestions = self.__suggest(text)
                        last_typed_text = text
                        if suggestions:
                            self.__last_text_for_suggestions = text
                            # If we got any suggestions, update the command parameter suggestions
                            self.caller.setParameterSuggestions(suggestions)
                    text = None
                    # Wait for any additional requests to accumulate before updating
                    # Loop for 100ms and collect the most recently typed text
                    started = datetime.datetime.now()
                    elapsed_ms = 0
                    while elapsed_ms < self.polling_interval:
                        time_to_wait = self.polling_interval - elapsed_ms
                        if time_to_wait > 0:
                            with suppress(Empty):
                                text = self._update_queue.get(block=True, timeout=time_to_wait / 1000)
                                self._update_queue.task_done()
                        tdiff = datetime.datetime.now() - started
                        elapsed_ms = (tdiff.days * 24 * 60 * 60 + tdiff.seconds) * 1000 + tdiff.microseconds / 1000.0
                    else:
                        pass
            finally:
                self.__suggestion_thread = None

        def __suggest(self, text):
            """Get list of suggestions based on text arg.
            This queries the suggestions webservice.
            """
            if not text:
                return None

            try:
                url_or_request = self.caller.getSuggestionsUrl(text)
                if not url_or_request:
                    # Abstract method can return invalid URL on purpose to avoid suggestions
                    return None
                assert isinstance(url_or_request, basestring) or isinstance(url_or_request, urllib2.Request)
            except Exception as e:
                logging.error("Getting the suggestion url/request failed: %s", e)
                return None

            # First try to get cached result. This should always return hit on backtracking (user deleting characters)
            if cache_manager:
                suggestions = cache_manager.get_data(text, self.cache_id, session_id=str(self.quasimodeId))
                if suggestions:
                    #print "Returning %d cached results for query '%s'" % (len(suggestions), text)
                    return suggestions
    
            suggestions = []
            data = None
    
            if isinstance(url_or_request, basestring):
                url = url_or_request
            else:
                url = url_or_request.get_full_url()

            try:
                # Lazily open persistent connection to the webservice
                if self._connection_manager is None:
                    self._connection_manager = PersistentHTTPConnectionManager(url_or_request)
                conn = self._connection_manager.get_connection()
                resp = conn.urlopen('GET', url, release_conn=True)
                data = resp.data
            except Exception as e:
                logging.error("Suggest query failed: %s; url: %s", e, url_or_request)
                self.caller.onSuggestQueryError(url_or_request, e)
            else:
                if data:
                    try:
                        suggestions = self.caller.decodeSuggestions(data, resp.headers)
                    except Exception as e:
                        logging.error("Suggest response parsing failed: %s", e)
    
            # Cache suggestions even when empty is returned to avoid re-query the web service with invalid input
            if cache_manager:
                #print "Cached %d results for query '%s'" % (len(suggestions), text)
                cache_manager.set_data(text, suggestions, self.cache_id, session_id=str(self.quasimodeId))
            
            return suggestions

    override = ('getSuggestionsUrl', 'decodeSuggestions', 'onSuggestQueryError')

    def __init__(self):
        #print "CommandParameterWebSuggestionsMixin.__init__() called"
        assert isinstance(self, ArbitraryPostfixFactory), "CommandParameterWebSuggestionsMixin usage requires the class to be descendant of ArbitraryPostfixFactory"
        
        super(CommandParameterWebSuggestionsMixin, self).__init__()
        
        self.__impl = CommandParameterWebSuggestionsMixin._Impl(self)

    @abstractmethod
    def getSuggestionsUrl(self, text):
        """Abstract method which should return suggestion webservice URL
        as string or a Request object.

        Always override this method.

        Return URL for suggestions query based on given text.
        This method is called each time the command parameter text is changed.
        It can return either URL as a string, or urllib2.Request instance.

        Return None to suppress the suggestions query for given text.

        Example (implementing google suggest, simplified):

          query = urllib.quote_plus(text.encode("ISO-8859-1"))
          return "http://clients1.google.com/complete/search?hl=en&gl=en&client=firefox&q=%s" % query
        """
        pass

    @abstractmethod
    def decodeSuggestions(self, data, headers=None):
        """Decode the output from the suggestions webservice
        and return the suggestions as a simple list of strings.

        Always override this method.

        Example (implementing google suggest, simplified):

          json_data = json.loads( data.decode("ISO-8859-1") )
          if json_data and len(json_data) > 1 and json_data[1]:
              return = json_data[1]
          else:
              return []
        """
        pass

    @abstractmethod
    def onSuggestQueryError(self, url_or_request, exception):
        """This is called whenever error occurs on call to the suggestion
        web service.

        Optionally override. By default it does nothing.
        """
        pass

    def onParameterModified(self, keyCode, oldText, newText, quasimodeId=0.0):
        """This method is called automatically whenever the command parameter text
        changes, i.e. when user is typing or deleting the parameter text.
        (These calls are performed from quasimode module on every command that
        implements this method)

        It will first initialize the suggestion-thread and then feed it with changed text
        on subsequent calls.
        """
        self.quasimodeId = quasimodeId
        self.__impl.onParameterModified(keyCode, oldText, newText, quasimodeId)

    def setSuggestionsPollingInterval(self, interval_in_ms):
        """Override the default polling interval"""
        if interval_in_ms < _MINIMAL_SUGGESTIONS_POLLING_INTERVAL:
            raise Exception(
                "The polling interval can't go below %d ms (%d)!"
                % (_MINIMAL_SUGGESTIONS_POLLING_INTERVAL, interval_in_ms)
            )
        self.__impl.setPollingInterval(interval_in_ms)

    def setCacheId(self, cacheId):
        """Optionally set cacheId for cache manager.
        By default it is set to caller.__class__.__name__
        
        cacheId is used for properly naming the cache directories.
        """
        self.__impl.cache_id = cacheId
