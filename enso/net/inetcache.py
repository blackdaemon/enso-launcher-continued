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
#
#   enso.net.inetcache
#
# ----------------------------------------------------------------------------
import os
import re
import time
import threading
import logging
import urllib2
import Queue
import socket
from enso.net import ping

from contextlib import closing


def is_online():
    def _get_addr(url, results):
        try:
            res = ping.do_one(url, timeout=2)
            #print "ping ",url,res
            #print url, percent_lost, mrtt, artt
            #with closing(urllib2.urlopen("http://%s/" % url, timeout=4)) as resp:
            results.put(
                (
                    url, 
                    True
                    #percent_lost < 100 and mrtt is not None and artt is not None
                )
            )
        except socket.error, e:
            #print "error",e
            res = os.system("ping %s -q -c 1 -w 2 | grep '1 received' > /dev/null" % url)
            #print "ping ",url,res
            if res == 0:
                results.put(
                    (
                        url, 
                        True
                #percent_lost < 100 and mrtt is not None and artt is not None
                    )
                )
            else:
                results.put(
                    (
                        url, 
                        False 
                    )
                )
        except Exception, e:
            # e.reason.errno == 11004 (getaddrinfofailed)
            results.put(
                (
                    url, 
                    False, 
                    e
                )
            )

    results = Queue.Queue()
    addresses = ("www.google.com", "www.microsoft.com", "www.ibm.com")
    threads_count = len(addresses)
    for addr in addresses:
        t = threading.Thread(target=_get_addr, args=(addr,results,))
        t.setDaemon(True)
        t.start()

    while threads_count > 0:
        try:
            result = results.get(timeout = 5)
            if result[1]:
                return True
            results.task_done()
            threads_count -= 1
        except Queue.Empty:
            break    
    
    return False

        
def retrieve_online_data(retrieval_func, offline_result_func, retry_count=1, retry_wait=5.0, async=False):
    assert retry_count > 0
    assert retry_wait >= 0.0

    def _retrieval_func(retrieval_func, offline_result_func, retry_count, retry_wait):
        retry = retry_count
        while retry:
            try:
                result = retrieval_func()
                return result
            except Exception, e:
                retry -= 1
                time.sleep(retry_wait)
                
        return offline_result_func()
            
    if async:
        t = threading.Thread(
            target=_retrieval_func, 
            args=(retrieval_func, offline_result_func, retry_count, retry_wait))
        t.setDaemon(True)
        t.start()
        return t
    else:
        return _retrieval_func()

isonline = is_online()
print "ISONLINE:", isonline

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: