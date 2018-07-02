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
#   enso.utils.decorators
#
# ----------------------------------------------------------------------------

"""
    Contains utility functions for decorators.  Note that this module
    does not contain actual decorators, but rather *utilities* for
    decorators to use.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import inspect
import logging
import os
import sys
import threading
import time

from functools import wraps

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

from enso import config
from enso.utils import do_once


# ----------------------------------------------------------------------------
# Functionality
# ----------------------------------------------------------------------------

def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        @wraps(fn)
        def debounced(*args, **kwargs):
            def call_it():
                print "DEBOUNCE [%s]: called" % fn.__name__
                #print fn, args, kwargs
                return fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            else:
                print "DEBOUNCE [%s]: droped" % fn.__name__
            debounced.t = threading.Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator


def log_once(text):
    """ Decorator for logging the function result once. """
    _cache = {}

    def decorator(fn):
        @wraps(fn)
        def log_func(*args, **kwargs):
            result = fn(*args, **kwargs)
            if not _cache.get(result, None):
                logging.info(text % result)
                _cache[result] = True
            return result
        return log_func
    return decorator


def synchronized(lock=None):
    """ Synchronization function decorator """
    if lock is None:
        lock = threading.Lock()

    def wrap(f):
        def new_function(*args, **kwargs):
            blocking = False
            while not lock.acquire(False):
                do_once(
                    logging.warn,
                    "Lock acquire() has been blocked, waiting for acquire..."
                )
                blocking = True
            else:
                if blocking:
                    logging.warn("...Lock acquired")
            try:
                return f(*args, **kwargs)
            finally:
                lock.release()
        return new_function
    return wrap



def finalizeWrapper(origFunc, wrappedFunc, decoratorName):
    """
    Makes some final modifications to the decorated or 'wrapped'
    version of a function by making the wrapped version's name and
    docstring match those of the original function.

    'decoratorName' is the string name for the decorator,
    e.g. 'Synchronized'.

    Assuming that the original function was of the form 'myFunc( self,
    foo = 1 )' and the decorator name is 'Synchronized', the new
    docstring for the wrapped function will be of the form:

        Synchronized wrapper for:
        myFunc( self, foo = 1 )

        <myFunc's docstring>

    Returns the wrapped function.
    """

    if "pychecker" in sys.modules:
        # If pychecker is in sys.modules, then we can assume that our
        # code is being checked by pychecker.  If this is the case,
        # then we just want to return the original function, because
        # pychecker doesn't like decorators.
        return origFunc

    # Get a prettified representation of the argument list.
    args, varargs, varkw, defaults = inspect.getargspec(origFunc)
    argspec = inspect.formatargspec(
        args,
        varargs,
        varkw,
        defaults
    )

    callspec = "%s%s" % (origFunc.__name__, argspec)

    # Generate a new docstring.
    newDocString = "%s wrapper for:\n%s\n\n%s" % \
                   (decoratorName, callspec, origFunc.__doc__)

    # Set the appropriate attributes on the wrapped function and pass
    # it back.
    wrappedFunc.__doc__ = newDocString
    wrappedFunc.__name__ = origFunc.__name__
    wrappedFunc.__module__ = origFunc.__module__
    return wrappedFunc


class timed_execution( ContextDecorator ):
    """
    Decorator / context-manager to time execution of func/block.
    FIXME: This form does not work properly when chaining function decorators.
    In such case it does fail if called from parent decorator.
    When fixed, it can be used in place of @timed decorator below.
    """
    def __init__( self, text ):
        self._text = text

    def __enter__( self ):
        self._start = time.clock()
        return self

    def __exit__(self, *exc):
        if config.DEBUG_REPORT_TIMINGS:
            logging.info(u"%s: %0.4Fs" % (self._text, time.clock() - self._start))


# next bit filched from 1.5.2's inspect.py
def _get_current_frame():
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except:
        return sys.exc_info()[2].tb_frame.f_back

if hasattr(sys, '_getframe'):
    _get_current_frame = lambda: sys._getframe(0)
# done filching

#
# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
_srcfile = os.path.normcase(_get_current_frame.__code__.co_filename)

def _find_caller(timed_func=None):
    """
    Find the stack frame of the caller so that we can note the source
    file name, line number and function name.
    """
    f = _get_current_frame()
    #On some versions of IronPython, currentframe() returns None if
    #IronPython isn't run with -X:Frames.
    if f is not None:
        f = f.f_back
    rv = "(unknown file)", 0, "(unknown function)"
    while hasattr(f, "f_code"):
        co = f.f_code
        print timed_func
        print co.co_name, f.__class__, f.__str__
        filename = os.path.normcase(co.co_filename)
        if filename == _srcfile:
            f = f.f_back
            continue
        if timed_func and timed_func not in co.co_name:
            f = f.f_back
            continue
        rv = (co.co_filename, f.f_lineno, co.co_name)
        break
    return rv

def _makeRecord(name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
    """
    A factory method which can be overridden in subclasses to create
    specialized LogRecords.
    """
    rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func)
    if extra is not None:
        for key in extra:
            if (key in ["message", "asctime"]): # or (key in rv.__dict__):
                raise KeyError("Attempt to overwrite %r in LogRecord" % key)
            rv.__dict__[key] = extra[key]
    return rv

def _monkeypatch_logger(logger):
    logger.makeRecord = _makeRecord

_monkeypatch_logger(logging.getLogger())

def timed(text, timed_func=None):
    """ Function decorator to time its execution """

#    logging_format = next(handler for handler in logging.getLogger().handlers if handler.stream == sys.stdout).formatter._fmt

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not config.DEBUG_REPORT_TIMINGS:
                return fn(*args, **kwargs)
            try:
                start = time.clock()
                return fn(*args, **kwargs)
            finally:
                extra = None
                try:
                    filename, lno, func = _find_caller(timed_func)
                except ValueError:
                    pass
                else:
                    extra={'pathname': filename, 'lineno': lno, 'funcName': func}
                logging.info(
                    u"%s: %0.4Fs",
                    text,
                    time.clock() - start,
                    extra=extra
                )
        return wrapper
    return decorator
