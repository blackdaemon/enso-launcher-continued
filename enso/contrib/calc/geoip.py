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

import re
import time
import os
import zlib
import urllib2
import gzip
import string
import StringIO
import threading
import logging

from contextlib import closing

from enso.net import inetcache

import socket
socket.setdefaulttimeout(5.0)


HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.7) Gecko/20100720 Firefox/3.6.7',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}



def compute_file_crc32(filename):
    try:
        if isinstance(filename, file):
            f = filename
        elif isinstance(filename, basestring):
            f = file(filename, 'rb')
        value = zlib.crc32("")
        while True:
            x = f.read(65536)
            if not x:
                f.close()
                return value & 0xFFFFFFFF
            value = zlib.crc32(x, value)
    except (IOError, OSError):
        return 0

class Globals(object):
    geoip_file = os.path.normpath(os.path.expanduser(u"~/GeoLite-Country.dat"))
    geoipcity_file = os.path.normpath(os.path.expanduser(u"~/GeoLite-City.dat"))
    geoip_url = "http://geolite.maxmind.com/download/geoip/database/GeoLiteCountry/GeoIP.dat.gz"
    geoipcity_url = "http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz"
    _download_geoip_thread = None
    _download_geoipcity_thread = None

    @classmethod
    def __init__(cls):
        # Cache file
        cls.get_geoip_file(wait=False)
        #cls.get_geoipcity_file(wait=False)

    @classmethod
    def _download_geoip_file(cls):
        assert logging.info("GeoIP download thread started") or True
        try:
            req = urllib2.Request(cls.geoip_url, None, HTTP_HEADERS)

            assert logging.info("Checking if GeoIP file has been updated on the server...") or True
            with closing(urllib2.urlopen(req, None, 5)) as resp:
                content_length = resp.info().get("Content-Length", "0")
                last_modified = resp.info().get("Last-Modified", "0")
                info_file = "%s.info" % os.path.splitext(cls.geoip_file)[0]
                if os.path.isfile(cls.geoip_file) and os.path.getsize(cls.geoip_file) > 0:
                    if os.path.isfile(info_file):
                        try:
                            old_last_modified, old_content_length = map(string.strip, open(info_file, "r"))
                            if old_content_length == content_length and old_last_modified == last_modified:
                                assert logging.info("Content is not newer, skipping") or True
                                return
                        except:
                            pass
                #print resp.info()
                """
                if resp.info().get('Content-Encoding') in ('gzip', 'x-gzip'):
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(resp.read())).read()
                else:
                    data = resp.read()
                """
                # This should avoid blocking the main thread
                # For details see:
                # http://bugs.python.org/issue14562#msg165927
                resp.fp._rbufsize = 0
                try:
                    assert logging.info("Downloading the contents...") or True
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(resp.read())).read()
                except:
                    data = resp.read()
            with open(cls.geoip_file, "wb") as fp:
                fp.write(data)
            with open(info_file, "w") as fp:
                fp.writelines((last_modified, "\n", content_length))
        except Exception, e:
            logging.error("Error opening connection to %s: %s", cls.geoip_url, e)
        finally:
            assert logging.info("GeoIP download thread finished") or True

    @classmethod
    def _download_geoipcity_file(cls):
        assert logging.info("Checking if GeoIPCity file has been updated online...") or True
        try:
            req = urllib2.Request(cls.geoipcity_url, None, HTTP_HEADERS)

            assert logging.info("Checking if GeoIPCity file has been updated on the server...") or True
            with closing(urllib2.urlopen(req, None, 5)) as resp:
                content_length = resp.info().get("Content-Length", "0")
                last_modified = resp.info().get("Last-Modified", "0")
                info_file = "%s.info" % os.path.splitext(cls.geoipcity_file)[0]
                if os.path.isfile(cls.geoipcity_file) and os.path.getsize(cls.geoipcity_file) > 0:
                    if os.path.isfile(info_file):
                        try:
                            old_last_modified, old_content_length = map(string.strip, open(info_file, "r"))
                            if old_content_length == content_length and old_last_modified == last_modified:
                                assert logging.info("Content is not newer, skipping") or True
                                return
                        except:
                            pass
    
                # This should avoid blocking the main thread
                # For details see:
                # http://bugs.python.org/issue14562#msg165927
                resp.fp._rbufsize = 0
                try:
                    assert logging.info("Downloading the contents...") or True
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(resp.read())).read()
                except:
                    data = resp.read()
            with open(cls.geoipcity_file, "wb", 512*1024) as fp:
                fp.write(data)
            with open(info_file, "w") as fp:
                fp.writelines((last_modified, "\n", content_length))
        except Exception, e:
            logging.error(e)
        finally:
            assert logging.info("GeoIPCity download thread finished") or True


    @classmethod
    def get_geoip_file(cls, wait=True):
        if cls._download_geoip_thread and cls._download_geoip_thread.isAlive():
            if wait:
                cls._download_geoip_thread.join(5)
                print "ISALIVE?", cls._download_geoip_thread.isAlive()
                cls._download_geoip_thread = None
        else:
            print cls.geoip_file, time.time() - os.path.getmtime(cls.geoip_file), 60*60*24
            if ((not os.path.isfile(cls.geoip_file)
                or time.time() - os.path.getmtime(cls.geoip_file) > 60*60*24)
                and inetcache.isonline):
                assert logging.info("Downloading GeoIP file in separate thread") or True
                cls._download_geoip_thread = threading.Thread(target=cls._download_geoip_file)
                cls._download_geoip_thread.setDaemon(True)
                cls._download_geoip_thread.start()
                if wait:
                    assert logging.info("waiting") or True
                    cls._download_geoip_thread.join()
                    cls._download_geoip_thread = None
                    assert logging.info("Downloaded GeoIP file") or True
        assert logging.info("File %s CRC: %08X" % (cls.geoip_file, compute_file_crc32(cls.geoip_file) & 0xffffffff)) or True
        if os.path.isfile(cls.geoip_file):
            return cls.geoip_file
        else:
            return None

    @classmethod
    def get_geoipcity_file(cls, wait=True):
        if cls._download_geoipcity_thread and cls._download_geoipcity_thread.isAlive():
            if wait:
                cls._download_geoipcity_thread.join()
                cls._download_geoipcity_thread = None
        else:
            if ((not os.path.isfile(cls.geoipcity_file) or time.time() - os.path.getmtime(cls.geoipcity_file) > 60*60*24)
                and inetcache.isonline):
                assert logging.info("Downloading GeoIPCity file in separate thread") or True
                cls._download_geoipcity_thread = threading.Thread(target=cls._download_geoipcity_file)
                cls._download_geoipcity_thread.setDaemon(True)
                cls._download_geoipcity_thread.start()
                if wait:
                    cls._download_geoipcity_thread.join()
                    cls._download_geoipcity_thread = None
                    assert logging.info("Downloaded GeoIPCity file") or True
        assert logging.info("File %s CRC: %08X" % (cls.geoipcity_file, compute_file_crc32(cls.geoipcity_file) & 0xffffffff)) or True
        if os.path.isfile(cls.geoipcity_file):
            return cls.geoipcity_file
        else:
            return None

Globals.__init__()



def lookup_country_code(ip_address):
    country_code = None
    try:
        import pygeoip

        # Download geoip data file in background (non blocking, not wait for result)
        gif = Globals.get_geoip_file(wait=False)

        # If downloaded, use geoip API to get the country
        if gif:
            country_code = pygeoip.GeoIP(gif).country_code_by_addr(ip_address)
    except ImportError:
        pass
    except Exception, e:
        logging.error(e)
    
    if  not country_code:
        # If geoip file not present (not yet downloaded) or it did not find the IP, 
        # use web API to get the country code
        if inetcache.isonline:
            try:
                with closing(urllib2.urlopen(
                    "http://getcitydetails.geobytes.com/GetCityDetails?fqcn=%s"
                    % ip_address, None, 5)) as resp:
                    meta = resp.read()
                r = re.search(r"\"geobytesinternet\"\s*:\s*\"(.*?)\"", meta)
                if r:
                    country_code = r.group(1)
            except Exception, e:
                logging.error(e)

    return country_code


def lookup_city(ip_address):
    city = None
    try:
        import pygeoip

        # Download geoipcity data file in background (non blocking, not wait for result)
        gicf = Globals.get_geoipcity_file(wait=False)

        # If downloaded, use geoip API to get the city
        if gicf:
            r = pygeoip.GeoIP(gicf).record_by_addr(ip_address)
            if r and 'city' in r:
                city = r['city']
    except ImportError:
        pass

    if not city:
        # If geoipcity file not present (not yet downloaded) or it did not find the IP, 
        # use web API to get the city
        if inetcache.isonline:
            try:
                with closing(urllib2.urlopen(
                    "http://getcitydetails.geobytes.com/GetCityDetails?fqcn=%s"
                    % ip_address, None, 5)) as resp:
                    meta = resp.read()
                r = re.search(r"\"geobytescity\"\s*:\s*\"(.*?)\"", meta)
                if r:
                    city = r.group(1)
            except Exception, e:
                logging.error(e)

    return city

