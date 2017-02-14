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
#   enso.contrib.google
#
# ----------------------------------------------------------------------------

"""
    An Enso plugin that makes the 'google' command available.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
from __future__ import with_statement

try:
    import regex as re
except ImportError:
    import re
    
import urllib
import locale
import webbrowser
import logging
import threading
import urllib2
import random

from contextlib import closing

import enso.config
from abc import ABCMeta
from enso.commands.decorators import warn_overriding
from enso.commands import CommandManager
from enso.commands.factories import ArbitraryPostfixFactory
from enso.commands.mixins import CommandParameterWebSuggestionsMixin
from enso.events import EventManager
from enso import selection
from enso.messages import displayMessage
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.utils.html_tools import strip_html_tags, unescape_html_entities
from enso.utils.decorators import suppress

try:
    import ujson as jsonlib
except ImportError as e:
    logging.warning("Consider installing 'ujson' library for JSON parsing performance boost.")
    import json as jsonlib
    
# Google suggestions polling interval in milliseconds (minimum allowed is 100) 
SUGGESTIONS_POLLING_INTERVAL = 100
# Maximum length of query Google accepts
MAX_QUERY_LENGTH = 2048
# Randomize HTTP user-agent string on Google suggestions queries (changes on every quasimode start)
RANDOMIZE_USER_AGENT = True

HTTP_HEADERS = {
    # This will get ramdomized on every query
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
    
# Several different User-Agents to diversify the requests.
# Keep the User-Agents updated. Last update:  01 Feb 2017
# Get them here: http://techblog.willshouse.com/2012/01/03/most-common-user-agents/
USER_AGENT_STRINGS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/602.3.12 (KHTML, like Gecko) Version/10.0.2 Safari/602.3.12',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393',
    'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:50.0) Gecko/20100101 Firefox/50.0'
]

# ----------------------------------------------------------------------------
# The Google command
# ---------------------------------------------------------------------------

# Here we detect national TLD imposed by Google based on user's location.
# This is used in suggestion-search.
# It offers local suggestions and also speeds up the search.
GOOGLE_DOMAIN = "com"

def _get_local_domain():
    global GOOGLE_DOMAIN
    try:
        with closing(urllib2.urlopen("http://www.google.com/", timeout=4)) as resp:
            # Get redirect URL
            redirected_url = resp.geturl()
        domain = urllib2.urlparse.urlsplit(redirected_url).netloc
        GOOGLE_DOMAIN = domain[domain.index("google.")+7:]
    except Exception as e:
        logging.warning("Error parsing google.com redirect TLS: ", str(e))
    logging.info("Google local domain has been set to .%s", GOOGLE_DOMAIN)

t = threading.Thread(target=_get_local_domain)
t.setDaemon(True)
t.start()


class RandomListItemProvider:
    """
    Returns one random item from the list based on the id.
    It remembers the id and as long as the id does not change between the calls, 
    the returned item stays the same.
    As soon as the id changes, the list is shuffled and same id returns different 
    item next time it's used.
    
    Example:
        get_random_http_agent = RandomListItemProvider(agents_list)
        
        get_random_http_agent(100)
            returns agent21
        get_random_http_agent(100)
            returns agent21
            
        get_random_http_agent(1020)
            returns agent15
        get_random_http_agent(1020)
            returns agent15
            
        get_random_http_agent(100)
            returns agent03
        get_random_http_agent(100)
            returns agent03
    """
    def __init__( self, item_list ):
        self.item_list = item_list
        self.last_id = 0
    
    def __call__(self, id):
        # On change of the id, shuffle the strings
        if id != self.last_id:
            random.shuffle(self.item_list)
            self.last_id = id
        # Always map same string to given id
        return self.item_list[hash(id) % len(self.item_list)]
        
    
@warn_overriding
class AbstractGoogleCommandFactory( CommandParameterWebSuggestionsMixin, ArbitraryPostfixFactory ):
    """
    Implementation of the 'google' command.
    """

    __metaclass__ = ABCMeta
    
    def __init__( self, command_name ):
        """
        Initializes the google command.
        """
        assert isinstance(command_name, basestring)
        assert len(command_name) > 0

        super(AbstractGoogleCommandFactory, self).__init__()
        #super() should call the mixin init properly
        #CommandParameterWebSuggestionsMixin.__init__(self)
        self.command_name = command_name
        self.config_key = command_name.upper().replace(" ", "_") 

        self.parameter = None

        try:
            self.do_suggestions = getattr(enso.config, "PLUGIN_%s_OFFER_SUGGESTIONS" % self.config_key)
        except:
            self.do_suggestions = False

        if not self.do_suggestions:
            logging.info(
                "%s search-suggestions are turned off in config. "
                "Enable 'PLUGIN_%s_OFFER_SUGGESTIONS' "
                "in your .ensorc to turn it on." % (command_name, self.config_key)
            )

        self.setSuggestionsPollingInterval(SUGGESTIONS_POLLING_INTERVAL)
        self.get_random_user_agent = RandomListItemProvider(USER_AGENT_STRINGS)

        
    @safetyNetted
    def run( self ):
        """
        Runs the google command.
        """

        # Google limits their search requests to 2048 bytes, so let's be
        # nice and not send them anything longer than that.
        #
        # See this link for more information:
        #
        #   http://code.google.com/apis/soapsearch/reference.html

        if self.parameter is not None:
            text = self.parameter.decode()
            # '...' gets replaced with current selection
            if "..." in text:
                seldict = selection.get()
                to_replace = " %s " % seldict.get( "text", u"" ).strip().strip("\0")
                text = text.replace("...", to_replace)
                text = re.sub(r"\s+", " ", text)
                text = re.sub(r"\r\n", " ", text)
                text = re.sub(r"\n", " ", text)
        else:
            seldict = selection.get()
            text = seldict.get( "text", u"" )
            text = re.sub(r"\s+", " ", text)

        text = text.strip().strip("\0")
        if not text:
            displayMessage( "<p>No text was selected.</p>" )
            return

        if len( text ) > MAX_QUERY_LENGTH:
            displayMessage( "<p>Your query is too long.</p>" )
            return

        base_url = self.BASE_URL

        # For compatibility with older core, use default locale if setting
        # is not used in the config...
        if (not hasattr(enso.config, "PLUGIN_%s_USE_DEFAULT_LOCALE" % self.config_key)
            # Otherwise check for value
            or getattr(enso.config, "PLUGIN_%s_USE_DEFAULT_LOCALE" % self.config_key)):
            # Determine the user's default language setting.  Google
            # appears to use the two-letter ISO 639-1 code for setting
            # languages via the 'hl' query argument.
            languageCode, _ = locale.getdefaultlocale()
            if languageCode:
                language = languageCode.split( "_" )[0]
            else:
                language = "en"
            base_url = "%s&hl=%s" % (self.BASE_URL, language)

        # The following is standard convention for transmitting
        # unicode through a URL.
        text = urllib.quote_plus( text.encode("utf-8") )

        # Catch exception, because webbrowser.open sometimes raises exception
        # without any reason
        try:
            webbrowser.open_new_tab(base_url % { "tld": GOOGLE_DOMAIN, "query": text})
        except Exception, e:
            logging.warning(e)


    def decodeSuggestions( self, data, headers=None ):
        suggestions = []
        charset = "utf-8"
        if headers:
            with suppress(Exception):
                content_type = headers.get("Content-Type", headers.get("content-type", "")).lower()
                if content_type and "charset=" in content_type:
                    charset = content_type.split("charset=")[-1]
        try:
            # By default Google sends data in ISO-8859-1 encoding.
            # To force another encoding, use URL parameter oe=<encoding>
            #decoded = unicode(data) #data.decode("ISO-8859-1")
            decoded = data.decode(charset)
        except Exception, e:
            logging.error("Google-suggest query unicode decoding failed: %s", e)
        else:
            if decoded.startswith("window.google.ac.h"):
                decoded = decoded.split("window.google.ac.h(")[1][:-1]
                try:
                    json = jsonlib.loads(decoded)
                except Exception, e:
                    logging.error(u"Error parsing JSON data: %s; data: '%s'", e, decoded)
                else:
                    if json and len(json) > 1 and json[1]:
                        suggestions = [unescape_html_entities(strip_html_tags(i[0])) for i in json[1]]
            else:
                try:
                    json = jsonlib.loads(decoded)
                except Exception, e:
                    logging.error(u"Error parsing JSON data: %s; data: '%s'", e, decoded)
                else:
                    if json and len(json) > 1 and json[1]:
                        suggestions = json[1]
        return suggestions

    def onSuggestQueryError( self, url_or_request, exception ):
        pass
        
    def _generateCommandObj( self, parameter=None ):
        self.parameter = parameter
        article = "an" if self.command_name[0] in ("i", "y") else "a" 
        if self.parameter is not None:
            self.setDescription( u"Performs %s %s search for "
                                 u"\u201c%s\u201d." % (article, self.command_name, self.parameter)
            )
        else:
            self.setDescription(
                u"Performs %s %s search on the selected or typed text." % (article, self.command_name)
            )
        return self
    
        

@warn_overriding
class GoogleSearchCommandFactory( AbstractGoogleCommandFactory ):
    HELP_TEXT = "search terms"
    PREFIX = "google "
    NAME = "%s{%s}" % (PREFIX, HELP_TEXT)
    BASE_URL = "http://www.google.%(tld)s/search?q=%(query)s"

    def getSuggestionsUrl( self, text ):
        if not self.do_suggestions:
            return None
        
        if text is None or len(text.strip()) == 0:
            return None

        charset = "utf-8"
        query = urllib.quote_plus(text.encode(charset))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=firefox&ie=%(ie)s&oe=%(oe)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":charset,
                "oe":charset,
                "query":query
            }

        if RANDOMIZE_USER_AGENT:
            # Get random user-agent every quasimode session
            HTTP_HEADERS['User-Agent'] = self.get_random_user_agent(self.quasimodeId)
    
        request = urllib2.Request(url, headers=HTTP_HEADERS)
        
        return request


@warn_overriding
class GoogleImagesCommandFactory( AbstractGoogleCommandFactory ):
    HELP_TEXT = "search terms"
    PREFIX = "images "
    NAME = "%s{%s}" % (PREFIX, HELP_TEXT)
    BASE_URL = "http://images.google.%(tld)s/images?um=1&hl=en&rlz=1C1GGLS_en-USCZ294&safeui=off&btnG=Search+Images&q=%(query)s"

    def getSuggestionsUrl( self, text ):
        if not self.do_suggestions:
            return None

        if text is None or len(text.strip()) == 0:
            return None

        charset = "utf-8"
        query = urllib.quote_plus(text.encode(charset))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=img&ie=%(ie)s&oe=%(oe)s&pq=%(query)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":charset,
                "oe":charset,
                "query":query
            }
        
        if RANDOMIZE_USER_AGENT:
            # Get random user-agent every quasimode session
            HTTP_HEADERS['User-Agent'] = self.get_random_user_agent(self.quasimodeId)

        request = urllib2.Request(url, headers=HTTP_HEADERS)
        
        return request


@warn_overriding
class YoutubeCommandFactory( AbstractGoogleCommandFactory ):
    """
    Implementation of the 'youtube' command.
    """
    HELP_TEXT = "search terms"
    PREFIX = "youtube "
    NAME = "%s{%s}" % (PREFIX, HELP_TEXT)
    BASE_URL = "http://www.youtube.com/results?search_type=&aq=0&nofeather=True&oq=&search_query=%(query)s"

    def getSuggestionsUrl(self, text):
        if not self.do_suggestions:
            return None

        if text is None or len(text.strip()) == 0:
            return None

        charset = "utf-8"
        query = urllib.quote_plus(text.encode(charset))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&ds=yt&client=firefox&hjson=t&ie=%(ie)s&oe=%(oe)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":charset,
                "oe":charset,
                "query":query
            }

        if RANDOMIZE_USER_AGENT:
            # Get random user-agent every quasimode session
            HTTP_HEADERS['User-Agent'] = self.get_random_user_agent(self.quasimodeId)

        request = urllib2.Request(url, headers=HTTP_HEADERS)
        
        return request


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    CommandManager.get().registerCommand(
        GoogleSearchCommandFactory.NAME,
        GoogleSearchCommandFactory("Google")
        )
    CommandManager.get().registerCommand(
        GoogleImagesCommandFactory.NAME,
        GoogleImagesCommandFactory("Google images")
        )
    CommandManager.get().registerCommand(
        YoutubeCommandFactory.NAME,
        YoutubeCommandFactory("YouTube")
        )

# vim:set tabstop=4 shiftwidth=4 expandtab: