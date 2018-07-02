# vim:set tabstop=4 shiftwidth=4 expandtab:

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
#   enso.contrib.websearch
#
# ----------------------------------------------------------------------------

"""
    An Enso plugin that makes the web search commands available.
    Commands support search suggestions if defined.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import locale
import logging
import threading
import urllib
import urllib2
import webbrowser
from abc import ABCMeta
from contextlib import closing
from functools import partial

try:
    import regex as re
except ImportError:
    import re
try:
    import ujson as jsonlib
except ImportError as e:
    logging.warning(
        "Consider installing 'ujson' library for JSON parsing performance boost.")
    import json as jsonlib

import enso.config
from enso import selection
from enso.commands import CommandManager
from enso.commands.decorators import warn_overriding
from enso.commands.factories import ArbitraryPostfixFactory
from enso.commands.mixins import CommandParameterWebSuggestionsMixin
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.messages import displayMessage
from enso.utils import suppress
from enso.utils.html_tools import strip_html_tags


# Default suggestions polling interval in milliseconds (minimum allowed is 100)
SUGGESTIONS_POLLING_INTERVAL = 100
# Default maximum length of query the site accepts
#
# Google limits their search requests to 2048 bytes, so let's be
# nice and not send them anything longer than that.
#
# See this link for more information:
#
#   http://code.google.com/apis/soapsearch/reference.html
MAX_QUERY_LENGTH = 2048

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

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
        GOOGLE_DOMAIN = domain[domain.index("google.") + 7:]
    except Exception as e:
        logging.warning("Error parsing google.com redirect TLS: %s", e)
    else:
        logging.info("Google local domain has been set to .%s", GOOGLE_DOMAIN)

t = threading.Thread(target=_get_local_domain)
t.setDaemon(True)
t.start()


@warn_overriding
class AbstractSearchCommandFactory(CommandParameterWebSuggestionsMixin, ArbitraryPostfixFactory):
    """
    Implementation of the web-search command.
    """

    __metaclass__ = ABCMeta

    def __init__(self, command_name, suggest, polling_interval):
        """
        Initializes the web-search command.
        """
        assert isinstance(command_name, basestring)
        assert len(command_name) > 0

        super(AbstractSearchCommandFactory, self).__init__()
        # super() should call the mixin init properly
        # CommandParameterWebSuggestionsMixin.__init__(self)
        self.command_name = command_name
        self.parameter = None
        self.do_suggestions = suggest
        self.setSuggestionsPollingInterval(polling_interval)

    @safetyNetted
    def run(self):
        """
        Runs the web-search command.
        """

        if self.parameter is not None:
            text = self.parameter.decode()
            # '...' gets replaced with current selection
            if "..." in text:
                seldict = selection.get()
                to_replace = " %s " % seldict.get(
                    "text", u"").strip().strip("\0")
                text = text.replace("...", to_replace)
                text = re.sub(r"\s+", " ", text)
                text = re.sub(r"\r\n", " ", text)
                text = re.sub(r"\n", " ", text)
        else:
            seldict = selection.get()
            text = seldict.get("text", u"")
            text = re.sub(r"\s+", " ", text)

        text = text.strip().strip("\0")
        if not text:
            displayMessage("<p>No text was selected.</p>")
            return

        if len(text) > MAX_QUERY_LENGTH:
            displayMessage("<p>Your query is too long.</p>")
            return

        # For compatibility with older core, use default locale if setting
        # is not used in the config...
        languageCode, _ = locale.getdefaultlocale()
        if languageCode:
            language = languageCode.split("_")[0]
        else:
            language = "en"

        # The following is standard convention for transmitting
        # unicode through a URL.
        text = urllib.quote_plus(text.encode("utf-8"))

        url = self.BASE_URL % {
            "google_tld": GOOGLE_DOMAIN, # Used just for Google services
            "langcode": language,
            "query": text,
        }

        # Catch exception, because webbrowser.open sometimes raises exception
        # without any reason
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            logging.warning(e)

    def onSuggestQueryError(self, url_or_request, exception):
        pass

    def _generateCommandObj(self, parameter=None):
        self.parameter = parameter
        if self.parameter is not None:
            self.setDescription(
                u"Performs %s search for \u201c%s\u201d."
                % (self.command_name, self.parameter)
            )
        else:
            self.setDescription(
                u"Performs %s search on the selected or typed text." % (
                    self.command_name)
            )
        return self


class ConfigurableSearchCommandFactory(AbstractSearchCommandFactory):

    remove_google_jsonp_wrapper = partial(
        re.compile(r"^(?:window.google.ac.h\()?(.*?)\)?$").sub,
        r"\1"
    )

    def __init__(
            self,
            command_name,
            command_prefix,
            help_text,
            base_url,
            suggest,
            suggestions_url,
            parser,
            is_json,
            minimum_chars,
            polling_interval):
        super(ConfigurableSearchCommandFactory, self).__init__(
            command_name, suggest, polling_interval)
        self.HELP_TEXT = help_text
        self.PREFIX = command_prefix
        self.NAME = "%s{%s}" % (command_prefix, help_text)
        self.BASE_URL = base_url
        self.suggestions_url = suggestions_url
        self.parser = parser
        self.is_json = is_json
        self.minimum_chars = max(1, minimum_chars)
        self.setCacheId(
            "ConfigurableSearch%s" % re.sub(
                r"[^A-Za-z0-9]", "", command_prefix.strip()
            ).title()
        )

    def getSuggestionsUrl(self, text):
        if not self.do_suggestions:
            return None

        if text is None or len(text.strip()) < self.minimum_chars:
            return None

        charset = "utf-8"
        query = urllib.quote_plus(text.encode(charset))
        # For compatibility with older core, use default locale if setting
        # is not used in the config...
        languageCode, _ = locale.getdefaultlocale()
        if languageCode:
            language = languageCode.split("_")[0]
        else:
            language = "en"

        url = self.suggestions_url % {
            "query": query,
            "charset": charset,
            "tld": GOOGLE_DOMAIN,
            "langcode": language,
        }

        request = urllib2.Request(url, headers=HTTP_HEADERS)

        return request

    def decodeSuggestions(self, data, headers=None):
        suggestions = []
        charset = "utf-8"
        if headers:
            with suppress(Exception):
                content_type = headers.get(
                    "Content-Type", headers.get("content-type", "")).lower()
                if content_type and "charset=" in content_type:
                    charset = content_type.split("charset=")[-1]
        try:
            decoded = data.decode(charset)
        except Exception, e:
            logging.error(
                "%s-suggest query unicode decoding failed: %s", self.name, e)
        else:
            try:
                # Optionally remove JSONP function wrapper (google searches)
                decoded = self.remove_google_jsonp_wrapper(decoded)
                json = jsonlib.loads(decoded)
            except Exception as e:
                logging.error(
                    u"Error parsing JSON data: %s; data: '%s'", e, decoded)
            else:
                if json:
                    suggestions = [strip_html_tags(s) for s in self.parser(json)][:10]  # Limit number of suggestions
        return suggestions


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------
def load():
    PLUGIN_CONFIG_PREFIX = "PLUGIN_WEBSEARCH"
    RE_PLUGIN_CONFIG = re.compile(r"^%s_([a-zA-Z0-9]+)" % PLUGIN_CONFIG_PREFIX)
    for plugin_name in (RE_PLUGIN_CONFIG.sub(r"\1", e) for e in dir(enso.config) if RE_PLUGIN_CONFIG.match(e)):
        config_key = "%s_%s" % (PLUGIN_CONFIG_PREFIX, plugin_name)
        try:
            conf = getattr(enso.config, config_key)
            command = ConfigurableSearchCommandFactory(
                command_name=conf["name"],
                command_prefix=conf["prefix"],
                help_text=conf["argument"],
                base_url=conf["base_url"],
                suggest=conf["suggest"],
                suggestions_url=conf["suggestions_url"],
                parser=conf["result_parser"],
                is_json=conf["is_json"],
                minimum_chars=conf.get(
                    "minimum_chars", 1),
                polling_interval=conf.get(
                    "polling_interval", SUGGESTIONS_POLLING_INTERVAL),
            )
            CommandManager.get().registerCommand(
                command.NAME,
                command
            )
            if not conf["suggest"]:
                logging.info(
                    "%s command search-suggestions are turned off. "
                    "To turn it on, modify 'suggest' parameter of %s entry "
                    "in your .ensorc configuration file." %
                    (conf["name"], config_key)
                )
        except Exception as e:
            logging.error(
                "Error parsing/registering websearch command from enso.config: %s; %s",
                config_key, e
            )
