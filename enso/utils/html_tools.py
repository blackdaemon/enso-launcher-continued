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
#   enso.utils.html_tools
#
# ----------------------------------------------------------------------------

"""
    HTML utility functions.  This module is called "html_tools" instead
    of simply "html" because that would cause a namespace conflict due
    to Python 2.x's default prioritization of relative imports over
    absolute imports (this will change in Py3k, though).
"""

__all__ = ("strip_html_tags", "unescape_html_entities")

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from htmlentitydefs import name2codepoint
try:
    import regex as re
except ImportError:
    import re

LXML_AVAILABLE = False
try:
    import lxml.html
    LXML_AVAILABLE = True
except ImportError:
    pass


# ----------------------------------------------------------------------------
# Public Constants
# ----------------------------------------------------------------------------

# for some reason, python 2.5.2 doesn't have this one (apostrophe)
name2codepoint['#39'] = 39

RE_SUB_HTMLENTITIES = re.compile(r"&(%s);" % '|'.join(name2codepoint), re.UNICODE).sub
RE_SUB_HTMLCODEPOINTS = re.compile(r"&#(\d+);", re.UNICODE).sub

RE_SUB_HTMLTAGS = re.compile(r"<.*?>", re.UNICODE).sub

    
def __strip_html_tags__lxml(html):
    return lxml.html.fromstring(html).text_content()

def __strip_html_tags__re(html, replacement=""):
    return RE_SUB_HTMLTAGS(replacement, html)

def strip_html_tags(html, replacement=""):
    if replacement:
        return __strip_html_tags__re(html, replacement)
    elif LXML_AVAILABLE:
        return __strip_html_tags__lxml(html)
    else:
        return __strip_html_tags__re(html)

def unescape_html_entities(html):
    "unescape HTML code refs; c.f. http://wiki.python.org/moin/EscapingHtml"
    r = RE_SUB_HTMLENTITIES(lambda m: unichr(name2codepoint[m.group(1)]), html)
    r = RE_SUB_HTMLCODEPOINTS(lambda m: unichr(int(m.group(1))), r)
    return r
