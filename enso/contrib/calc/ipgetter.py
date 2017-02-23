#!/usr/bin/env python
"""
This module is designed to fetch your external IP address from the internet.
It is used mostly when behind a NAT.
It picks your IP randomly from a serverlist to minimize request
overhead on a single server

If you want to add or remove your server from the list contact me on github


API Usage
=========

    >>> import ipgetter
    >>> myip = ipgetter.myip()
    >>> myip
    '8.8.8.8'

    >>> ipgetter.IPgetter().test()

    Number of servers: 47
    IP's :
    8.8.8.8 = 47 ocurrencies


Copyright 2014 phoemur@gmail.com
This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.
"""

import re
import random

from sys import version_info
from contextlib import closing


PY3K = version_info >= (3, 0)

if PY3K:
    import urllib.request as urllib
else:
    import urllib2 as urllib

__version__ = "0.6"
__updated__ = "2017-02-23"

URL_OPENER = urllib.build_opener()
URL_OPENER.addheaders = [(
    'User-agent',
    "Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0"
)]


SERVER_LIST = [
    'http://api.ipify.org',
    'http://ip.dnsexit.com',
    'http://ifconfig.me/ip',
    'http://echoip.com',
    'http://ipecho.net/plain',
    'http://checkip.dyndns.org/plain',
    'http://ipogre.com/linux.php',
    'http://whatismyipaddress.com/',
    'http://websiteipaddress.com/WhatIsMyIp',
    'http://getmyipaddress.org/',
    'http://www.my-ip-address.net/',
    'http://myexternalip.com/raw',
    'http://www.canyouseeme.org/',
    'http://www.trackip.net/',
    'http://icanhazip.com/',
    'http://www.iplocation.net/',
    'http://www.howtofindmyipaddress.com/',
    'http://www.ipchicken.com/',
    'http://whatsmyip.net/',
    'http://www.ip-adress.com/',
    'http://checkmyip.com/',
    'http://www.tracemyip.org/',
    'http://www.lawrencegoetz.com/programs/ipinfo/',
    'http://www.findmyip.co/',
    'http://ip-lookup.net/',
    'http://www.dslreports.com/whois',
    'http://www.mon-ip.com/en/my-ip/',
    'http://www.myip.ru',
    'http://ipgoat.com/',
    'http://www.myipnumber.com/my-ip-address.asp',
    'http://www.whatsmyipaddress.net/',
    'http://formyip.com/',
    'http://www.displaymyip.com/',
    'http://www.bobborst.com/tools/whatsmyip/',
    'http://www.geoiptool.com/',
    'http://checkip.dyndns.com/',
    'http://myexternalip.com/',
    'http://www.ip-adress.eu/',
    'http://www.infosniper.net/',
    'http://wtfismyip.com/text',
    'http://ipinfo.io/',
    'http://httpbin.org/ip',
    'http://ip.ajn.me',
    'http://diagnostic.opendns.com/myip',
]

DISABLED_SERVERS = []


def myip():
    return IPgetter().get_externalip()


class IPgetter(object):

    '''
    This class is designed to fetch your external IP address from the internet.
    It is used mostly when behind a NAT.
    It picks your IP randomly from a serverlist to minimize request overhead
    on a single server
    '''

    def __init__(self):
        pass

    def get_externalip(self, samples=10):
        '''
        This function gets your IP from a random server
        '''
        for server in random.sample(set(SERVER_LIST) - set(DISABLED_SERVERS), samples):
            myip = self.fetch(server)
            if myip:
                return myip
            else:
                DISABLED_SERVERS.append(server)
        return ''


    def fetch(self, server):
        '''
        This function gets your IP from a specific server.
        '''
        try:
            with closing(URL_OPENER.open(server, timeout=2)) as resp:
                content = resp.read()

            # Didn't want to import chardet. Prefered to stick to stdlib
            if PY3K:
                try:
                    content = content.decode('UTF-8')
                except UnicodeDecodeError:
                    content = content.decode('ISO-8859-1')

            m = re.search(
                '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
                content)
            myip = m.group(0)
            return myip if myip else ''
        except Exception as e:
            print e
            return ''


    def test(self):
        '''
        This functions tests the consistency of the servers
        on the list when retrieving your IP.
        All results should be the same.
        '''
        resultdict = {}
        for server in self.server_list:
            resultdict.update(**{server: self.fetch(server)})

        ips = sorted(resultdict.values())
        ips_set = set(ips)
        print('\nNumber of servers: {}'.format(len(self.server_list)))
        print("IP's :")
        for ip, ocorrencia in zip(ips_set, map(lambda x: ips.count(x), ips_set)):
            print('{0} = {1} ocurrenc{2}'.format(ip if len(ip) > 0 else 'broken server', ocorrencia, 'y' if ocorrencia == 1 else 'ies'))
        print('\n')
        print(resultdict)


if __name__ == '__main__':
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    print(myip())
    