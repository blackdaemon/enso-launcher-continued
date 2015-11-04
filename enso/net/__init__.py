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

#==============================================================================
# Version history
#
#
#
# 1.0    [blackdaemon] Initial version
#==============================================================================

__author__ = "blackdaemon@seznam.cz"
__module_version__ = __version__ = "1.0"

#==============================================================================
# Imports
#==============================================================================

import os
import sys
import re
import urllib2
import logging

from urllib2 import URLError
from httplib import HTTPException
from contextlib import closing

if sys.platform.startswith("win"):
    platform_name = "win32"
elif any(map(sys.platform.startswith, ("linux","openbsd","freebsd","netbsd"))):
    platform_name = "linux"
elif sys.platform == "darwin":
    platform_name = "osx"

        
def get_default_gateway():
    if platform_name in ["linux", "osx"]:
        import struct
        import socket
        from socket import error as SocketError
        """Read the default gateway directly from /proc."""
        with open("/proc/net/route") as fh:
            for line in fh:
                fields = line.strip().split()
                if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                    continue
                return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
    elif platform_name == "win32":
        import subprocess
        from operator import itemgetter
        gateway = None
        p = subprocess.Popen(
            "route PRINT 0.0.0.0",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        info = p.stdout.read()
        gateways = re.findall(r"[0-9\.]{7,}\s+[0-9\.]{7,}\s+([0-9\.]{7,})\s+([0-9\.]{7,})\s+([0-9]+)", info)
        if gateways:
            # Sort by metric
            gateway, interface, metric = sorted(gateways, key=itemgetter(2))[0]
        return gateway    
    else:
        raise Exception("Function not implemented for this platform")


def get_local_ip():
    if platform_name in ["linux", "osx"]:
        import socket
        from socket import error as SocketError
        with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    elif platform_name == "win32":
        import subprocess
        from operator import itemgetter
        p = subprocess.Popen(
            "route PRINT 0.0.0.0",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        info = p.stdout.read()
        gateways = re.findall(r"[0-9\.]{7,}\s+[0-9\.]{7,}\s+([0-9\.]{7,})\s+([0-9\.]{7,})\s+([0-9]+)", info)
        if gateways:
            # Sort by metric
            gateway, interface, metric = sorted(gateways, key=itemgetter(2))[0]
        return interface
    else:
        raise Exception("Function not implemented for this platform")
            

def get_external_ip():
    ip = None
    try:
        with closing(urllib2.urlopen("https://api.ipify.org", timeout=2)) as resp:
            text = resp.read()
            if text:
                ip = text
    except Exception, e:
        logging.error(e)
        try:
            with closing(urllib2.urlopen("http://httpbin.org/ip", timeout=2)) as resp:
                text = resp.read()
                if text:
                    r = re.search(r"\"origin\":\s+\"([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})\"", text, re.MULTILINE)
                    if r:
                        ip = r.group(1)
        except Exception, e:
            logging.error(e)
                    
    return ip


def get_mac_address(host):
    """
    Returns a list of MACs for interfaces that have given IP, returns None if not found
    """
    if platform_name in ["linux", "osx"]:
        """
        import netifaces as nif
        'Returns a list of MACs for interfaces that have given IP, returns None if not found'
        for i in nif.interfaces():
            addrs = nif.ifaddresses(i)
            try:
                if_mac = addrs[nif.AF_LINK][0]['addr']
                if_ip = addrs[nif.AF_INET][0]['addr']
            except (IndexError, KeyError), e: #ignore ifaces that dont have MAC or IP
                if_mac = if_ip = None
            if if_ip == host:
                return if_mac.upper()
        return None
        """
        from enso.platform.linux.utils import get_status_output
        rc, out = get_status_output("arp -n %s" % host)
        if rc == 0 and out:
            for entry in out.splitlines():
                r = re.search(r"^%s.*?([a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2}:[a-f0-9]{2})" % re.escape(host), entry, re.IGNORECASE)
                if r:
                    return r.group(1).upper()
        else:
            return None
        
    elif platform_name == "win32":
        """ Returns the MAC address of a network host, requires >= WIN2K. """
        import ctypes
        import struct
        import socket
        # Check for api availability
        try:
            SendARP = ctypes.windll.Iphlpapi.SendARP
        except:
            raise NotImplementedError('Usage only on Windows 2000 and above')
    
        # Doesn't work with loopbacks, but let's try and help.
        if host == '127.0.0.1' or host.lower() == 'localhost':
            host = socket.gethostname()
    
        # gethostbyname blocks, so use it wisely.
        try:
            inetaddr = ctypes.windll.wsock32.inet_addr(host)
            if inetaddr in (0, -1):
                raise Exception
        except:
            hostip = socket.gethostbyname(host)
            inetaddr = ctypes.windll.wsock32.inet_addr(hostip)
    
        buff = ctypes.c_buffer(6)
        addlen = ctypes.c_ulong(ctypes.sizeof(buff))
        if SendARP(inetaddr, 0, ctypes.byref(buff), ctypes.byref(addlen)) != 0:
            raise Exception('Retrieval of MAC address(%s) - failed' % host)
    
        # Convert binary data into a string.
        macaddr = ''
        for intval in struct.unpack('BBBBBB', buff):
            if intval > 15:
                replacestr = '0x'
            else:
                replacestr = 'x'
            macaddr = ''.join([macaddr, hex(intval).replace(replacestr, '')])
    
        return macaddr.upper()
    else:
        raise Exception("Function not implemented for this platform")
        
if __name__ == "__main__":
    print get_external_ip()
    print get_local_ip()
    print get_default_gateway()
    print get_mac_address(get_default_gateway())

