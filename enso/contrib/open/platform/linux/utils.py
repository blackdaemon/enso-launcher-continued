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

# Future imports
from __future__ import with_statement
import os
from os.path import exists as pathexists, isdir, isfile, islink

import gio

from enso.contrib.open import shortcuts


def get_file_type(text):
    if not pathexists(text):
        # FIXME: Real test for URL here
        return shortcuts.SHORTCUT_TYPE_URL
    if isdir(text):
        return shortcuts.SHORTCUT_TYPE_FOLDER
    if not isfile(text) and not islink(text):
        return shortcuts.SHORTCUT_TYPE_DOCUMENT
    filename = text
    # Sample file contents
    with open(filename, "r") as fd:
        sample = fd.read(128)
    # Guess if it's executable
    can_execute = False
    content_type = None
    try:
        content_type = gio.content_type_guess(filename, sample, want_uncertain=False)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
        print content_type
        can_execute = gio.content_type_can_be_executable(content_type)  # IGNORE:E1101 @UndefinedVariable Keep PyLint and PyDev happy
    except Exception as e:
        print e
    if not can_execute:
        print "not executable? ", content_type
        if os.access(filename, os.X_OK):
            print "has executable perms"
            return shortcuts.SHORTCUT_TYPE_EXECUTABLE
    # FIXME: If is executable but has not execute perms, issue warning
    if can_execute and os.access(filename, os.X_OK):
        print "is executable"
        return shortcuts.SHORTCUT_TYPE_EXECUTABLE
    return shortcuts.SHORTCUT_TYPE_DOCUMENT
