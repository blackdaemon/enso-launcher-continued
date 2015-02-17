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

from contextlib import closing
from htmlentitydefs import name2codepoint

import enso.config
from enso.commands import abstractmethod
from enso.commands import CommandManager
from enso.commands.factories import ArbitraryPostfixFactory
from enso.commands.mixins import CommandParameterWebSuggestionsMixin
from enso import selection
from enso.messages import displayMessage
from enso.contrib.scriptotron.tracebacks import safetyNetted


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
t.setDaemon(True)
t.start()


def unescape_html_tags(html):
    # for some reason, python 2.5.2 doesn't have this one (apostrophe)
    name2codepoint['#39'] = 39

    "unescape HTML code refs; c.f. http://wiki.python.org/moin/EscapingHtml"
    r = re.sub('&(%s);' % '|'.join(name2codepoint),
              lambda m: unichr(name2codepoint[m.group(1)]), html)
    r = re.sub('&#(\d+);', lambda m: unichr(int(m.group(1))), r)
    return r


class GoogleCommandFactory( ArbitraryPostfixFactory, CommandParameterWebSuggestionsMixin ):
    """
    Implementation of the 'google' command.
    """

    def __init__( self, which ):
        """
        Initializes the google command.
        """
        super(GoogleCommandFactory, self).__init__()

        self.which = which

        self.parameter = None

        self.setDescription(
            u"Performs a Google web search on the selected or typed text.")

        try:
            self.do_suggestions = enso.config.PLUGIN_GOOGLE_OFFER_SUGGESTIONS
        except:
            self.do_suggestions = False

        if not self.do_suggestions:
            logging.info(
                "Google search-suggestions are turned off in config. "
                "Enable 'PLUGIN_GOOGLE_OFFER_SUGGESTIONS' "
                "in your .ensorc to turn it on.")


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
        if (not hasattr(enso.config, "enso.config.PLUGIN_GOOGLE_USE_DEFAULT_LOCALE")
            # Otherwise check for value
            or enso.config.PLUGIN_GOOGLE_USE_DEFAULT_LOCALE):
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
            decoded = data.decode("ISO-8859-1")
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


    @abstractmethod
    def get_url(self):
        pass

    def _generateCommandObj( self, parameter=None ):
        self.parameter = parameter
        if self.parameter is not None:
            self.setDescription( u"Performs a Google web search for "
                                 u"\u201c%s\u201d." % self.parameter )
        else:
            self.setDescription(
                u"Performs a Google web search on the selected or typed text.")
        return self



class GoogleSearchCommandFactory( GoogleCommandFactory ):
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
        return "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=firefox&ie=%(ie)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":input_encoding,
                "query":query
            }


class GoogleImagesCommandFactory( GoogleCommandFactory ):
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
        return "http://clients1.google.%(tld)s/complete/search?" \
            "hl=en&gl=en&client=img&ie=%(ie)s&pq=%(query)s&q=%(query)s" \
            % {
                "tld":GOOGLE_DOMAIN,
                "ie":input_encoding,
                "query":query
            }


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    CommandManager.get().registerCommand(
        GoogleSearchCommandFactory.NAME,
        GoogleSearchCommandFactory("google")
        )
    CommandManager.get().registerCommand(
        GoogleImagesCommandFactory.NAME,
        GoogleImagesCommandFactory("images")
        )

# vim:set tabstop=4 shiftwidth=4 expandtab: