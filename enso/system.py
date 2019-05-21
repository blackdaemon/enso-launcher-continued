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
    This module provides access to important end-user system functions.
"""

#==============================================================================
# Imports
#==============================================================================

from os.path import islink, join as pathjoin
from os import stat

from scandir import scandir

import enso.providers


#==============================================================================
# Module variables
#==============================================================================

# Actual implementation provider for this module.
__systemImpl = enso.providers.get_interface("system")

globals().update(__systemImpl.__dict__)

#==============================================================================
# Classes & Functions
#==============================================================================

def _dirwalk(top, onerror=None, followlinks=True, dotted_dirs=True, max_depth=None):
    """
    Faster dirwalk than os.walk, based on scandir library.

    Based on _walk function from scandir lib, with modifications:
      - Added dotted_dirs param
      - Added max_depth param
      - Removed topdown param. It is always topdown now

    max_depth of None means "infinite"
    max_depth of 0 means "just top dir"
    max_depth of 1 means "1 level below top dir"
    etc...
    """
    dirs = []
    nondirs = []

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        scandir_it = scandir(top)
    except OSError as error:
        if onerror is not None:
            onerror(error)
        return

    while True:
        try:
            try:
                entry = next(scandir_it)
            except StopIteration:
                break
        except OSError as error:
            if onerror is not None:
                onerror(error)
            return

        try:
            is_dir = entry.is_dir()
        except OSError:
            # If is_dir() raises an OSError, consider that the entry is not
            # a directory, same behaviour than os.path.isdir().
            is_dir = False

        if is_dir:
            if dotted_dirs or not entry.name.startswith("."):
                dirs.append(entry.name)
        else:
            nondirs.append(entry.name)

    yield top, dirs, nondirs

    # Recurse into sub-directories
    if max_depth is None or max_depth > 0:
        depth = None if max_depth is None else max_depth - 1
        for name in dirs:
            new_path = pathjoin(top, name)
            # Issue #23605: os.path.islink() is used instead of caching
            # entry.is_symlink() result during the loop on os.scandir() because
            # the caller can replace the directory entry during the "yield"
            # above.
            if followlinks or not islink(new_path):
                for entry in _dirwalk(new_path,
                        onerror=onerror,
                        followlinks=followlinks,
                        dotted_dirs=dotted_dirs,
                        max_depth=depth):
                    yield entry


def dirwalk(top, onerror=None, followlinks=True, dotted_dirs=True, max_depth=None, recursion_guard=False):
    """
    Faster dirwalk than os.walk, based on scandir library.

    Based on _walk function from scandir lib, with modifications:
      - Added dotted_dirs param
      - Added max_depth param
      - Removed topdown param. It is always topdown now
      - Added optional infinite recursion guard if followlinks is True

    max_depth of None means "infinite"
    max_depth of 0 means "just top dir"
    max_depth of 1 means "1 level below top dir"
    etc...
    """
    if not followlinks or not recursion_guard:
        # No infinite recursion guard needed, proceed normally
        for root, dirs, nondirs in _dirwalk(top, onerror=onerror, followlinks=followlinks, dotted_dirs=dotted_dirs, max_depth=max_depth):
            yield root, dirs, nondirs
    else:
        # Infinite recursion guard needed, will remember already traversed dirs
        # and avoid entering them again
        traversed_dirs = set()
        # Remember top dir first
        st = stat(top)
        # Device + inode is the key
        dirkey = (st.st_dev, st.st_ino)
        traversed_dirs.add(dirkey)
        for root, dirs, nondirs in _dirwalk(top, onerror=onerror, followlinks=followlinks, dotted_dirs=dotted_dirs, max_depth=max_depth):
            if dirs:
                # Modify dirs list in place, removing dirs which leads to recursion
                for idx, dirname in enumerate(dirs[:]):
                    st = stat(pathjoin(root, dirname))
                    # Device + inode is the key
                    dirkey = (st.st_dev, st.st_ino)
                    if dirkey not in traversed_dirs:
                        # Remember traversed dir
                        traversed_dirs.add(dirkey)
                    else:
                        # Remove this dir
                        del dirs[idx]
            yield root, dirs, nondirs


#==============================================================================
# Main
#==============================================================================

if __name__ == "__main__":
    from os import walk
    from os.path import expanduser
    from timeit import timeit

    old_list = list(walk(expanduser("~/Documents")))
    new_list = list(dirwalk(expanduser("~/Documents")))
    assert old_list == new_list
    old_list = list(walk(expanduser("~/Dropbox")))
    new_list = list(dirwalk(expanduser("~/Dropbox")))
    assert old_list == new_list
    old_list = list(walk(expanduser("~/Downloads")))
    new_list = list(dirwalk(expanduser("~/Downloads")))
    assert old_list == new_list

    print timeit('list(walk(expanduser("~/Documents")))', setup='from os import walk; from os.path import expanduser', number=10)
    print timeit('list(dirwalk(expanduser("~/Documents")))', setup='from dirwalk import dirwalk; from os.path import expanduser', number=10)
