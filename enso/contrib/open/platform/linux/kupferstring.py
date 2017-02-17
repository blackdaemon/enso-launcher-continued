# -*- encoding: UTF-8 -*-
# vim:set tabstop=4 shiftwidth=4 expandtab:
#
# This code has been borrowed from Kupfer
#
# Homepage:  http://kaizer.se/wiki/kupfer/
# Credits:   Copyright 2007-2011 Ulrik Sverdrup <ulrik.sverdrup@gmail.com>
# Licence:   GNU General Public License v3 (or any later version)

import locale
from unicodedata import category, normalize


def _folditems():
    _folding_table = {
        # general non-decomposing characters
        # FIXME: This is not complete
        u"ł": u"l",
        u"œ": u"oe",
        u"ð": u"d",
        u"þ": u"th",
        u"ß": u"ss",
        # germano-scandinavic canonical transliterations
        u"ü": u"ue",
        u"å": u"aa",
        u"ä": u"ae",
        u"æ": u"ae",
        u"ö": u"oe",
        u"ø": u"oe",
    }

    for c, rep in _folding_table.iteritems():
        yield (ord(c.upper()), rep.title())
        yield (ord(c), rep)

folding_table = dict(_folditems())


def tounicode(utf8str):
    """Return `unicode` from UTF-8 encoded @utf8str
    This is to use the same error handling etc everywhere
    """
    if isinstance(utf8str, unicode):
        return utf8str
    return utf8str.decode("UTF-8", "replace") if utf8str is not None else u""


def toutf8(ustr):
    """Return UTF-8 `str` from unicode @ustr
    This is to use the same error handling etc everywhere
    if ustr is `str`, just return it
    """
    if isinstance(ustr, str):
        return ustr
    return ustr.encode("UTF-8")


def fromlocale(lstr):
    """Return a unicode string from locale bytestring @lstr"""
    assert isinstance(lstr, str)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return lstr.decode(enc, "replace")


def tolocale(ustr):
    """Return a locale-encoded bytestring from unicode @ustr"""
    assert isinstance(ustr, unicode)
    enc = locale.getpreferredencoding(do_setlocale=False)
    return ustr.encode(enc)


def tofolded(ustr):
    u"""Fold @ustr

    Return a unicode string where composed characters are replaced by
    their base, and extended latin characters are replaced by
    similar basic latin characters.

    >>> tofolded(u"Wyłącz")
    u'Wylacz'
    >>> tofolded(u"naïveté")
    u'naivete'

    Characters from other scripts are not transliterated.

    >>> print tofolded(u"Ἑλλάς")
    Ελλας
    """
    srcstr = normalize("NFKD", ustr.translate(folding_table))
    return u"".join([c for c in srcstr if category(c) != 'Mn'])
