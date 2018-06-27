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
import sys
import time
import threading
import logging
import socket

from contextlib import closing

if sys.platform.startswith("win"):
    platform_name = "win32"
elif any(map(sys.platform.startswith, ("linux","openbsd","freebsd","netbsd"))):
    from enso.platform.linux.utils import get_cmd_output
    platform_name = "linux"
elif sys.platform == "darwin":
    from enso.platform.linux.utils import get_cmd_output
    platform_name = "osx"


def is_online():
    try:
        DEFAULT_TIMEOUT = 4
        socket.setdefaulttimeout(DEFAULT_TIMEOUT)
        # Trying to open the socket seems to be better than pinging as the ICMP
        # protocol is sometimes blocked either on the OS level (on RHEL you have to be root)
        # or by various antivirus or firewall software, or also by routers across network.
        # Whereas DNS lookup should always be available. If it is not, for any reason,
        # we additionally try HTTP connect to reliable servers.

        #TODO: Parameterize following hosts/ports
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            """
            Host: 8.8.8.8 (google-public-dns-a.google.com)
            OpenPort: 53/tcp
            Service: domain (DNS/TCP)
            """
            s.settimeout(DEFAULT_TIMEOUT)
            s.connect(("8.8.8.8", 53))
            s.shutdown(socket.SHUT_RDWR)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(DEFAULT_TIMEOUT)
            s.connect(("www.microsoft.com", 80))
            s.shutdown(socket.SHUT_RDWR)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(DEFAULT_TIMEOUT)
            s.connect(("www.ibm.com", 80))
            s.shutdown(socket.SHUT_RDWR)
    except socket.error as e:
        print e
        return False
    except socket.timeout as e:
        print e
        return False
    except Exception as e:
        print e
        return False
    else:
        return True

# TODO: Finish the online retrieval function with offline data caching
def retrieve_online_data(retrieval_func, offline_result_func, retry_count=1, retry_wait=5.0, async=False):
    assert retry_count > 0
    assert retry_wait >= 0.0

    def _retrieval_func(retrieval_func, offline_result_func, retry_count, retry_wait):
        retry = retry_count
        while retry:
            try:
                result = retrieval_func()
                return result
            except Exception as e:
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
        return _retrieval_func(retrieval_func, offline_result_func, retry_count, retry_wait)

isonline = is_online()

# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: