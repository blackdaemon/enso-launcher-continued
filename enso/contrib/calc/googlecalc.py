import urllib
import urllib2
import httplib
import time
import threading
import re
import os
import logging
from xml.sax.saxutils import escape as xml_escape
from iniparse import SafeConfigParser

from enso.commands import CommandManager, CommandObject
from enso.commands.factories import ArbitraryPostfixFactory
from enso import selection
from enso.messages import displayMessage
from enso.messages import Message, MessageManager
from enso.contrib.scriptotron import ensoapi
import enso.config



def cmd_gcalc(ensoapi, query = None):
    u""" Google calculator """

    MAX_QUERY_LENGTH = 2048

    if query is not None:
        query = query.decode()
        # '...' gets replaced with current selection
        if "..." in query:
            seldict = selection.get()
            query = query.replace(
                "...", seldict.get( "text", u"" ).strip().strip("\0"))
    else:
        seldict = selection.get()
        query = seldict.get( "text", u"" )

    query = query.strip(" \0\t\r\n")

    if not query:
        ensoapi.display_message(u"No query.")
        return

    if not query.endswith("="):
        query += "="

    if len(query) > MAX_QUERY_LENGTH:
        ensoapi.display_message(u"Your query is too long.")
        return

    start='<h2 class=r style="font-size:138%"><b>'
    end='</b>'

    url = "http://www.google.com/search?num=1&q=%s" % urllib.quote_plus(
        query.encode("utf-8") )
    try:
        logging.info(url)
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'Lynx (textmode)')]
        resp = opener.open(url)
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            logging.error("HTTPError %d: %s" % e.reason)
            ensoapi.display_message(u"HTTPError %d: %s" % e.reason)
        elif hasattr(e, 'code'):
            ensoapi.display_message(u"HTTPError #%d" % e.code)
        return
    else:
        data = resp.read()

    if data.find(start)==-1:
        ensoapi.display_message(u"Results not found.")
        print len(data), data
    else:
        begin = data.index(start)
        result = data[begin+len(start):begin+data[begin:].index(end)]
        result = result.replace("<font size=-2> </font>",",").replace(" &#215; 10<sup>","E").replace("</sup>","").replace("\xa0",",")
        print result
        ensoapi.display_message(xml_escape(result))


# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: