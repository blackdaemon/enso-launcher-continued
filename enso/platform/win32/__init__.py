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

import os
import sys
import atexit

import enso.platform

if not sys.platform.startswith("win"):
    raise enso.platform.PlatformUnsupportedError()

# Hack the PATH so we can load dlls from the enso.platform.win32 directory
# Our path must be at the beginning, otherwise libcairo-2.dll from other
# applications can get in the way
os.environ["PATH"] = "%s;%s" % (os.path.abspath( __path__[0] ), os.environ["PATH"])

os_path_expanduser = os.path.expanduser

def _expanduser( path ):
    """
    Expand ~ and ~user constructs.
    """
    # Rewrite logic from ntpath.py for Windows platform
    #assert isinstance(path, unicode), "'path' parameter must be unicode string"
    if not isinstance(path, unicode):
        # Use original function for non-unicode path
        return os_path_expanduser(path)

    if path[:1] != '~':
        return path
    i, n = 1, len(path)
    while i < n and path[i] not in '/\\':
        i = i + 1

    # Microsoft approved way of getting the personal directory path:
    # Use this as it always returns unicode string in contrary to standard
    # method using environ['USERPRPFILE'] that contains national-encoded string
    from win32com.shell import shell, shellcon # @UnresolvedImport
    userhome = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, 0, 0)

    if i != 1: #~user
        userhome = os.path.join(os.path.dirname(userhome), path[1:i])

    return userhome + path[i:]

# Monkeypatch standard os.path.expanduser with fixed one correctly handling national
# characters in username.
os.path.expanduser = _expanduser


def get_script_folder_name():
    """Returns the folder where Enso commands are found. This function
    is responsible for ensuring that this folder exists: it must not
    return a path that is not present! It is expected to place this
    folder in some platform-specific logical location."""
    raise NotImplementedError("This platform does not define a "
        "scripts folder (this needs fixing)")

# Import and return the Win32 implementation of the requested interface.

def provide_interface( name ):
    if name == "input":
        import enso.platform.win32.input
        return enso.platform.win32.input
    elif name == "graphics":
        # async event thread must be started before we create any
        # TransparentWindows, and stopped when we shut down:
        import enso.platform.win32.input.AsyncEventThread
        enso.platform.win32.input.AsyncEventThread.start()
        atexit.register( enso.platform.win32.input.AsyncEventThread.stop )
        # TODO make sure nothing bad will happen here if
        # provide_interface( "graphics" ) gets called more than once.
        import enso.platform.win32.graphics
        return enso.platform.win32.graphics
    elif name == "cairo":
        import enso.platform.win32.cairo
        return enso.platform.win32.cairo
    elif name == "selection":
        import enso.platform.win32.selection
        return enso.platform.win32.selection
    elif name == "system":
        import enso.platform.win32.system
        return enso.platform.win32.system
    elif name == "scripts_folder":
        from enso.platform.win32.scriptfolder import get_script_folder_name
        return get_script_folder_name
    else:
        return None

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:
