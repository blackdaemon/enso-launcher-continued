# Copyrigh (c) 2008, Humanized, Inc.

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
#   enso.commands.suggestions_cache.manager
#
# ----------------------------------------------------------------------------

"""
    The CommandManager singleton.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import os
import time
import locale
import logging
from glob import glob

import fcntlmodule
from io import BlockingIOError

import gzip
from pandas import DataFrame, read_csv   

from contextlib import closing

from os import makedirs 
from os.path import join as path_join
from os.path import exists as path_exists
from os.path import isfile, getmtime


from enso import config
from enso.utils.memoize import memoized
from enso.contrib.scriptotron import EnsoApi
from enso.events import EventManager

ENSOAPI = EnsoApi()
ENSO_COMMANDS_DIR = EnsoApi().get_enso_commands_folder()

CACHING_COMPRESSION = True
MAX_CACHE_AGE = 60 * 60 * 12

# The directory path for cached google results
CACHE_DIR = os.path.expanduser(path_join("~", ".cache", "enso", "suggestions"))

CACHE_SESSIONS = {}



        
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, 0o744)
        
def maybe_clean_cache():
    """Delete all .cache and .cache.gz files in the cache directory that are older than 12 hours."""
    now = time.time()
    for fname in glob(path_join(CACHE_DIR, "*", "*.cache")):
        if now > getmtime(fname) + MAX_CACHE_AGE:
            os.remove(fname)
    for fname in glob(path_join(CACHE_DIR, "*", "*.cache.gz")):
        if now > getmtime(fname) + MAX_CACHE_AGE:
            os.remove(fname)


# Clean the CACHEDIR once in a while
maybe_clean_cache()


from ctypes import c_ulong

def ulong(i): 
    return c_ulong(i).value  # numpy would be better if available

def sdbm_l(L):
    return reduce(lambda h,c: ulong(ord(c) + (h << 6) + (h << 16) - h), L, 0)
  
  
def cached_file_name(search_params):
    #sha = hashlib.sha256()
    # Make a unique file name based on the values of the google search parameters.
    #sha.update(search_params.encode())
    return '%s.%s' % (str(sdbm_l(search_params)), 'cache.gz' if CACHING_COMPRESSION else "cache")


def nonblocking_readlines(f):
    """Generator which yields lines from F (a file object, used only for
       its fileno()) without blocking.  If there is no data, you get an
       endless stream of empty strings until there is data again (caller
       is expected to sleep for a while).
       Newlines are normalized to the Unix standard.
    """

    fd = f.fileno()
    fl = fcntlmodule.fcntl(fd, fcntlmodule.F_GETFL)
    fcntlmodule.fcntl(fd, fcntlmodule.F_SETFL, fl | os.O_NONBLOCK)
    enc = locale.getpreferredencoding(False)

    buf = bytearray()
    while True:
        try:
            block = os.read(fd, 8192)
        except BlockingIOError:
            yield ""
            continue

        if not block:
            if buf:
                yield buf.decode(enc)
                #buf.clear()
            break

        buf.extend(block)

        while True:
            r = buf.find(b'\r')
            n = buf.find(b'\n')
            if r == -1 and n == -1: 
                break

            if r == -1 or r > n:
                yield buf[:(n+1)].decode(enc)
                buf = buf[(n+1):]
            elif n == -1 or n > r:
                yield buf[:r].decode(enc) # + '\n'
                if n == r+1:
                    buf = buf[(r+2):]
                else:
                    buf = buf[(r+1):]
                
                 

@memoized
def ensure_cache_dir_exists(cache_id):
    assert isinstance(cache_id, basestring) and cache_id.isalnum()
    complete_cache_dir = path_join(CACHE_DIR, cache_id)
    if not path_exists(complete_cache_dir):
        makedirs(complete_cache_dir, 0o744)
    return complete_cache_dir

           

# ----------------------------------------------------------------------------
# The cache
# ----------------------------------------------------------------------------

class Cache( object ):
    def __init__(self, cache_id):
        self.cache_id = cache_id
        self.__cache = {}

    def get_object(self, key, default=None):
        if key in self.__cache:
            #print "Getting memory cached object for '%s'" % (key)
            return self.__cache[key]
            
        #return self._caches.get(key, [])
        cache_dir = ensure_cache_dir_exists(self.cache_id)      
        
        fname = path_join(cache_dir, cached_file_name(key))
        if not isfile(fname):
            #print "No cached object for '%s'" % (key)
            return default
    
        try:
            # If the cached file is older than 12 hours, return False and thus
            # make a new fresh request.
            modtime = getmtime(fname)
            if (time.time() - modtime) / 60 / 60 > 12:
                #print "No cached object for '%s'" % (key)
                return default
            df = read_csv(
                fname, 
                sep="\t", 
                header=None, 
                encoding="utf-8", 
                compression=("gzip" if CACHING_COMPRESSION else None)
            )
            result = df[0].tolist()
            #print result
            self.__cache[key] = result
            #print "Getting file cached for '%s'" % (key)
            return result
        except Exception as err:
            print key, err
            
        #print "No cached object for '%s'" % (key)
        return default

        
    def set_object(self, key, value):
        #print "Caching object for '%s' in memory" % (key)
        self.__cache[key] = value


    def persist(self):
        if len(self.__cache) == 0:
            return
        # Flush memory cache to disk and purge memory cache
        cache_dir = ensure_cache_dir_exists(self.cache_id)
        #print "Persisting cache '%s' into %s (%d items)" % (self.cache_id, cache_dir, len(self.__cache))
        for key, value in self.__cache.items()[:]:      
            fname = path_join(cache_dir, cached_file_name(key))
            # Already saved
            try:
                if not path_exists(fname):
                    df = DataFrame(value)
                    
                    if CACHING_COMPRESSION:
                        gz = None
                        try:
                            gz = gzip.open(fname, "wt", compresslevel=9)
                            df.to_csv(gz, sep="\t", header=False, encoding="utf-8", index=False)
                        finally:
                            if gz:
                                gz.close()
                    else:
                        df.to_csv(fname, sep="\t", header=False, encoding="utf-8", index=False)
            except Exception as e:
                print e
            else:            
                del self.__cache[key]


# ----------------------------------------------------------------------------
# The cache manager
# ----------------------------------------------------------------------------
    
class CacheManager( object ):
    """
    Provides an interface to register and retrieve all commands.

    Allows client code to register new command implementations, find
    suggestions, and retrieve command objects.
    """

    __instance = None

    @classmethod
    def get( cls ):
        if not cls.__instance:
            cls.__instance = cls()
        return cls.__instance


    def __init__( self ):
        """
        Initializes the command manager.
        """
        self._current_session_id = None
        self.__caches = {}
        self.__eventManager = EventManager.get()
        self.__eventManager.registerResponder( self._onEndQuasimode, "endQuasimode" )


    def set_data(self, key, data, cache_id, session_id=None):
        assert isinstance(key, basestring) and key.isalnum()
        assert isinstance(cache_id, basestring) and cache_id.isalnum()
        assert session_id is None or isinstance(session_id, basestring)
        assert isinstance(data, list)
        
        self.__caches.setdefault(cache_id, Cache(cache_id)).set_object(key, data)
        
        
    def get_data(self, key, cache_id, session_id=None):
        assert isinstance(key, basestring) and key.isalnum()
        assert isinstance(cache_id, basestring) and cache_id.isalnum()
        assert session_id is None or isinstance(session_id, basestring)
        
        return self.__caches.setdefault(cache_id, Cache(cache_id)).get_object(key, [])

        
    def get_session_cache(self, session_id):
        assert session_id is None or isinstance(session_id, basestring)
        
        if self._current_session_id and session_id != self._current_session_id:
            self._schedule_cache_disposal(self._current_session_id)
            self._current_session_id = session_id
        cache = self._caches.get(session_id, None)
        if not cache:
            cache = Cache(session_id)
            self._caches[session_id] = cache
        return cache

        
    def _schedule_cache_disposal(self, session_id):
        pass

        
    def _onEndQuasimode(self):
        # Flush memory cache to disk on quasimode end
        for cache in self.__caches.itervalues():
            cache.persist()
