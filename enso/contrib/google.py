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

import re
import urllib
import locale
import webbrowser
import logging
import threading
import json as jsonlib
import urllib2

from random import choice
from contextlib import closing
from htmlentitydefs import name2codepoint

import enso.config
from abc import ABCMeta
from enso.commands.decorators import warn_overriding
from enso.commands import CommandManager
from enso.commands.factories import ArbitraryPostfixFactory
from enso.commands.mixins import CommandParameterWebSuggestionsMixin
from enso import selection
from enso.messages import displayMessage
from enso.contrib.scriptotron.tracebacks import safetyNetted

RANDOMIZE_USER_AGENT = True

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0',
    #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Connection': 'Keep-Alive',
    #'Accept-Encoding': 'gzip, deflate',
    'DNT': '1'
}
    
# Several different User-Agents to diversify the requests.
# Keep the User-Agents updated. Last update:  19 Nov 2015
# Get them here: http://techblog.willshouse.com/2012/01/03/most-common-user-agents/
USER_AGENT_STRINGS = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11) AppleWebKit/601.1.56 (KHTML, like Gecko) Version/9.0 Safari/601.1.56',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/601.2.7 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.7'
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
        # Parse TLD
        domain = re.findall(
            r"\bgoogle\.([a-z]+(?:\.[a-z]+)?)$",
            urllib2.urlparse.urlsplit(redirected_url).netloc)
        if domain:
            GOOGLE_DOMAIN = domain[0]
    except:
        pass
    logging.info("Google local domain has been set to .%s", GOOGLE_DOMAIN)

t = threading.Thread(target=_get_local_domain)
#t.setDaemon(True)
t.start()


def unescape_html_tags(html):
    # for some reason, python 2.5.2 doesn't have this one (apostrophe)
    name2codepoint['#39'] = 39

    "unescape HTML code refs; c.f. http://wiki.python.org/moin/EscapingHtml"
    r = re.sub('&(%s);' % '|'.join(name2codepoint),
              lambda m: unichr(name2codepoint[m.group(1)]), html)
    r = re.sub('&#(\d+);', lambda m: unichr(int(m.group(1))), r)
    return r

    
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

        MAX_QUERY_LENGTH = 2048

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
        try:
            # By default Google sends data in ISO-8859-1 encoding.
            # To force another encoding, use URL parameter oe=<encoding>
            decoded = unicode(data) #data.decode("ISO-8859-1")
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
                        suggestions = [unescape_html_tags(re.sub(r"<.*?>", "", i[0])) for i in json[1]]
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

        input_encoding = "utf-8"
        query = urllib.quote_plus(text.encode(input_encoding))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=firefox&ie=%(ie)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":input_encoding,
                "query":query
            }
        if RANDOMIZE_USER_AGENT:
            HTTP_HEADERS['User-Agent'] = choice(USER_AGENT_STRINGS)
    
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

        input_encoding = "utf-8"
        query = urllib.quote_plus(text.encode(input_encoding))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=img&ie=%(ie)s&pq=%(query)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":input_encoding,
                "query":query
            }
        if RANDOMIZE_USER_AGENT:
            HTTP_HEADERS['User-Agent'] = choice(USER_AGENT_STRINGS)
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

        input_encoding = "utf-8"
        query = urllib.quote_plus(text.encode(input_encoding))

        # This URL seems to returns only english matches
        #url = 'http://suggestqueries.google.com/complete/search?output=firefox&client=firefox&%s' % (query)
        
        # This URL returns also national matches
        url = "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&ds=yt&client=firefox&hjson=t&ie=%(ie)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":input_encoding,
                "query":query
            }
        if RANDOMIZE_USER_AGENT:
            HTTP_HEADERS['User-Agent'] = choice(USER_AGENT_STRINGS)
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