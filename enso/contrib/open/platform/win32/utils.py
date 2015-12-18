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

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import os
import win32api
import win32con
import ctypes

try:
    import regex as re
except Exception, e:
    import re


def expand_win_path_variables(file_path):
    re_env = re.compile(r'%\w+%')

    def expander(mo):
        return os.environ.get(mo.group()[1:-1], 'UNKNOWN')

    return os.path.expandvars(re_env.sub(expander, file_path))


def platform_windows_vista():
    #FIXME: Replace with proper test as soon as this issue is fixed in Python dist
    #See http://bugs.python.org/issue7863
    maj, min, buildno, plat, csd = win32api.GetVersionEx()
    return maj == 6 and min == 0


def platform_windows_7():
    #FIXME: Replace with proper test as soon as this issue is fixed in Python dist
    #See http://bugs.python.org/issue7863
    maj, min, buildno, plat, csd = win32api.GetVersionEx()
    return maj == 6 and min == 1



def _splitcmdline(cmdline):
    """
    Parses the command-line and returns the tuple in the form
    (command, [param1, param2, ...])

    >>> splitcmdline('c:\\someexecutable.exe')
    ('c:\\\\someexecutable.exe', [])

    >>> splitcmdline('C:\\Program Files\\Internet Explorer\\iexplore.exe')
    ('C:\\\\Program Files\\\\Internet Explorer\\\\iexplore.exe', [])

    >>> splitcmdline('c:\\someexecutable.exe "param 1" param2')
    ('c:\\\\someexecutable.exe', ['param 1', 'param2'])

    >>> splitcmdline(r'c:\\program files\\executable.exe')
    ('c:\\\\program', ['files\\\\executable.exe'])

    >>> splitcmdline(r'"c:\\program files\\executable.exe" param1 param2   ')
    ('c:\\\\program files\\\\executable.exe', ['param1', 'param2'])
    """
    from pyparsing import Combine, OneOrMore, Word, Optional, Literal, LineEnd, CharsNotIn, quotedString, delimitedList

    # Replace tabs and newlines with spaces
    cmdline = cmdline.strip(' \r\n\t').replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')

    """
    _nonspace = "".join( [ c for c in printables if c not in (" ", "\t") ] )
    _spacesepitem = Combine(OneOrMore(CharsNotInWord(_nonspace) +
                                Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
    """
    spaceSeparatedList = delimitedList(
            Optional( quotedString | CharsNotIn(" \t"), default=""), delim=" "
        ).setName("spaceSeparatedList")

    print spaceSeparatedList.parseString(cmdline)
    pass


def splitcmdline(cmdline):
    """
    Parses the command-line and returns the tuple in the form
    (command, [param1, param2, ...])

    >>> splitcmdline('c:\\someexecutable.exe')
    ('c:\\\\someexecutable.exe', [])

    >>> splitcmdline('C:\\Program Files\\Internet Explorer\\iexplore.exe')
    ('C:\\\\Program Files\\\\Internet Explorer\\\\iexplore.exe', [])

    >>> splitcmdline('c:\\someexecutable.exe "param 1" param2')
    ('c:\\\\someexecutable.exe', ['param 1', 'param2'])

    >>> splitcmdline(r'c:\\program files\\executable.exe')
    ('c:\\\\program', ['files\\\\executable.exe'])

    >>> splitcmdline(r'"c:\\program files\\executable.exe" param1 param2   ')
    ('c:\\\\program files\\\\executable.exe', ['param1', 'param2'])
    """

    # Replace tabs and newlines with spaces
    cmdline = cmdline.strip(' \r\n\t').replace('\t', ' ').replace('\r', ' ').replace('\n', ' ')

    # Handle special cases first
    if " " not in cmdline:
        # Nothing to parse if there is no space, it's filename only
        return cmdline, []
    elif "\"" not in cmdline:
        # There are spaces but no quotes
        # Handle special cases of long filename not enclosed in quotes
        if os.path.isfile(expand_win_path_variables(cmdline)):
            return cmdline, []
        else:
            # otherwise split it by spaces
            parts = cmdline.split(" ")
            return parts[0], [part for part in parts[1:] if len(part) > 0]
    else:
        """
        import ctypes
        from ctypes import windll, wintypes

        CommandLineToArgvW = windll.shell32.CommandLineToArgvW
        CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, wintypes.POINTER(ctypes.c_int)]
        CommandLineToArgvW.restype = wintypes.POINTER(wintypes.LPWSTR)

        argc = ctypes.c_int(0)
        argv = CommandLineToArgvW(cmdline, ctypes.byref(argc))

        if argc.value > 0:
            for a in [argv[i].encode('utf-8') for i in range(argc.value)]:
                parts.append(a)
        return parts[0], [part for part in parts[1:] if len(part) > 0]
        """
        # Spaces and quotes are present so parse it carefully
        parts = []
        part = ""
        between_quotes = False

        for c in cmdline:
            if c == "\"":
                between_quotes = not between_quotes
                if not between_quotes:
                    # Just ended quotes, append part
                    parts.append(part)
                    part = ""
            elif c in (" ", "\t", "\n") and not between_quotes:
                if part:
                    parts.append(part)
                    part = ""
            else:
                part += c

        if part:
            parts.append(part)

        return parts[0], [part for part in parts[1:] if len(part) > 0]


def get_exe_version_info(file_name):
    result = {}
    
    ver_strings=('Comments','InternalName','ProductName', 
        'CompanyName','LegalCopyright','ProductVersion', 
        'FileDescription','LegalTrademarks','PrivateBuild', 
        'FileVersion','OriginalFilename','SpecialBuild')

    def_lang = 1033 # English
    def_user_lang = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    def_system_lang = ctypes.windll.kernel32.GetSystemDefaultUILanguage()

    try:
        d = win32api.GetFileVersionInfo(file_name, '\\')
        # backslash as parm returns dictionary of numeric info corresponding to VS_FIXEDFILEINFO struc
        #for n, v in d.iteritems():
        #    print n, v
        result.update(d)
    except Exception, e:
        pass

    try:
        pairs = win32api.GetFileVersionInfo(file_name, '\\VarFileInfo\\Translation')
        ## \VarFileInfo\Translation returns list of available (language, codepage) pairs that can be used to retreive string info
        ## any other must be of the form \StringfileInfo\%04X%04X\parm_name, middle two are language/codepage pair returned from above
        for lang, codepage in pairs:
            print 'lang: ', lang, 'codepage:', codepage
            for ver_string in ver_strings:
                str_info = u'\\StringFileInfo\\%04X%04X\\%s' %(lang,codepage,ver_string)
                ## print str_info
                value = win32api.GetFileVersionInfo(file_name, str_info)
                print ver_string, value
                result[ver_string] = value
    except Exception, e:
        pass

    return result


def get_exe_name(file_name, default=None):
    
    def get_value(lang, codepage, ver_string):
        str_info = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, ver_string)
        return win32api.GetFileVersionInfo(file_name, str_info)

    PRODUCT_NAME = "ProductName"
    def_lang = win32con.LANG_ENGLISH # English
    def_system_lang = win32con.PRIMARYLANGID(ctypes.windll.kernel32.GetSystemDefaultUILanguage())
    def_user_lang = win32con.PRIMARYLANGID(ctypes.windll.kernel32.GetUserDefaultUILanguage())

    try:
        pairs = win32api.GetFileVersionInfo(file_name, '\\VarFileInfo\\Translation')
        ## \VarFileInfo\Translation returns list of available (language, codepage) pairs that can be used to retreive string info
        ## any other must be of the form \StringfileInfo\%04X%04X\parm_name, middle two are language/codepage pair returned from above
        
        lang_codes = dict((win32con.PRIMARYLANGID(lang),(lang, codepage)) for (lang, codepage) in pairs)
        
        if def_user_lang in lang_codes:
            name = get_value(lang_codes[def_user_lang][0], lang_codes[def_user_lang][1], PRODUCT_NAME)
            if name:
                return name
        
        if def_system_lang in lang_codes:
            name = get_value(lang_codes[def_system_lang][0], lang_codes[def_system_lang][1], PRODUCT_NAME)
            if name:
                return name

        if def_lang in lang_codes:
            name = get_value(lang_codes[def_lang][0], lang_codes[def_lang][1], PRODUCT_NAME)
            if name:
                return name

        for lang, codepage in pairs:
            name = get_value(lang, codepage, PRODUCT_NAME)
            if name:
                return name
    except Exception, e:
        pass

    return None


if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: