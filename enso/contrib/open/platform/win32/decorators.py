# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:

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

import pythoncom

from functools import wraps

from enso.utils import suppress

try:
    # Python 3.x
    from contextlib import ContextDecorator, contextmanager
except ImportError:
    try:
        # Python 2.6+
        from contextdecorator import ContextDecorator, contextmanager
    except ImportError:
        # Python 2.7+
        from contextlib2 import ContextDecorator, contextmanager


@contextmanager
def __initialize_pythoncom(func, *args, **kwargs):
    """ Function decorator. Initialize Python COM interface before function call
    """
    with suppress():
        pythoncom.CoInitialize()
    yield func(*args, **kwargs)


def initialize_pythoncom(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with suppress():
            pythoncom.CoInitialize()
        return fn(*args, **kwargs)
    return wrapper
