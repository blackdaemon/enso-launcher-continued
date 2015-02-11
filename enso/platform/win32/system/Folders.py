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
#   enso.system
#
# ----------------------------------------------------------------------------

"""
    This module provides access to important end-user system folders.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import sys
import os
from win32com.shell import shell, shellcon


# ----------------------------------------------------------------------------
# Module variables
# ----------------------------------------------------------------------------

# Windows system folders
# http://www.theutilityfactory.com/online_help/index.html?hidd_special_folders.htm
SYSTEMFOLDER_MYDOCUMENTS = shellcon.CSIDL_PERSONAL
SYSTEMFOLDER_MYMUSIC = shellcon.CSIDL_MYMUSIC
SYSTEMFOLDER_MYPICTURES = shellcon.CSIDL_MYPICTURES
SYSTEMFOLDER_MYVIDEO = shellcon.CSIDL_MYVIDEO
SYSTEMFOLDER_WINDOWS = shellcon.CSIDL_WINDOWS
SYSTEMFOLDER_FONTS = shellcon.CSIDL_FONTS
SYSTEMFOLDER_USERPROFILE = shellcon.CSIDL_PROFILE
SYSTEMFOLDER_APPDATA = shellcon.CSIDL_APPDATA
SYSTEMFOLDER_APPDATALOCAL = shellcon.CSIDL_LOCAL_APPDATA

# ----------------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------------

def get_system_folder(folder_id):
    #folder = shell.SHGetFolderPath(0, folder_id, 0, 0)
    # Following does not return unicode string
    folder = shell.SHGetPathFromIDList(shell.SHGetFolderLocation (0, folder_id))
    if not isinstance(folder, unicode):
        folder = folder.decode(sys.getfilesystemencoding())
    return folder


# Enso special folder - Local data storage
# c:\Documents and Settings\<user>\Local Settings\Application Data\Enso
SPECIALFOLDER_ENSOLOCAL = os.path.join(
    get_system_folder(SYSTEMFOLDER_APPDATALOCAL), u"Enso")

# Enso special folder - Enso's Learn As Open Commands
SPECIALFOLDER_ENSOLEARNAS = os.path.join(
    get_system_folder(SYSTEMFOLDER_MYDOCUMENTS), u"Enso's Learn As Open Commands")

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: