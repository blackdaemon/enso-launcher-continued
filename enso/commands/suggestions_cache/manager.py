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
import logging
from glob import glob
from ctypes import c_ulong

from os import makedirs 
from os.path import join as path_join
from os.path import exists as path_exists
from os.path import isfile, getmtime

from enso import config
from enso.utils.memoize import memodict, lru_cache
from enso.events import EventManager
import enso.providers


DISK_CACHING = True
MAX_CACHE_AGE = 60 * 60 * 12

# The directory path for cached google results
CACHE_DIR = path_join(enso.providers.getInterface("system").get_enso_cache_dir(), "suggestions")

CACHE_SESSIONS = {}


if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, 0o744)
        
def maybe_clean_cache():
    """Delete all .cache files in the cache directory that are older than 12 hours."""
    now = time.time()
    for fname in glob(path_join(CACHE_DIR, "*", "*", "*.cache")):
        if now > getmtime(fname) + MAX_CACHE_AGE:
            os.remove(fname)

# Clean the CACHEDIR once in a while
maybe_clean_cache()


def sdbm_l_hash(L):
    h = 0
    for c in L:
        h = c_ulong(ord(c) + (h << 6) + (h << 16) - h).value
    return h
  
  
def cached_file_name(search_params):
    #sha = hashlib.sha256()
    # Make a unique file name based on the values of the google search parameters.
    #sha.update(search_params.encode())
    return '%s.%s' % (str(sdbm_l_hash(search_params)), "cache")


@lru_cache()
def ensure_cache_dir_exists(cache_id):
    assert isinstance(cache_id, basestring) and cache_id.isalnum()
    complete_cache_dir = path_join(CACHE_DIR, cache_id)
    if not path_exists(complete_cache_dir):
        makedirs(complete_cache_dir, 0o744)
    for i in range(10):
        cache_subdir = path_join(complete_cache_dir, str(i))
        if not path_exists(cache_subdir):
            makedirs(cache_subdir, 0o744)
    return complete_cache_dir


def write_list_to_cache_file(fname, lst):           
    with open(fname, "wbt") as f:
        f.write(u"\n".join(lst).encode("UTF-8"))


def read_list_from_cache_file(fname):           
    with open(fname, "rb", 1024*1024) as f:
        txt = f.read(1024*1024).decode("UTF-8")
        return txt.splitlines()


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
            
        if not DISK_CACHING:
            return default
        
        #return self._caches.get(key, [])
        cache_dir = ensure_cache_dir_exists(self.cache_id)      
        
        fname = cached_file_name(key)
        fname = path_join(cache_dir, fname[0], fname)
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

            result = read_list_from_cache_file(fname)

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
    
        if not DISK_CACHING:
            return
        
        # Flush memory cache to disk and purge memory cache
        cache_dir = ensure_cache_dir_exists(self.cache_id)
        #print "Persisting cache '%s' into %s (%d items)" % (self.cache_id, cache_dir, len(self.__cache))
        for key, value in self.__cache.items()[:]:      
            fname = cached_file_name(key)
            fname = path_join(cache_dir, fname[0], fname)
            # Already saved
            try:
                if not path_exists(fname):
                    write_list_to_cache_file(fname, value)
            except Exception as e:
                logging.error(e)
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
        assert isinstance(key, basestring)
        assert isinstance(cache_id, basestring) and cache_id.isalnum()
        assert session_id is None or isinstance(session_id, basestring)
        assert isinstance(data, list)
        
        self.__caches.setdefault(cache_id, Cache(cache_id)).set_object(key, data)
        
        
    def get_data(self, key, cache_id, session_id=None):
        assert isinstance(key, basestring)
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
