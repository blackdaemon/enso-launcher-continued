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
import urllib
import urllib2
import gzip
import string
import StringIO
import threading
import logging

from contextlib import closing

from enso.net import inetcache

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.7) Gecko/20100720 Firefox/3.6.7',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}

class urlopen:
    def __init__(self, url, data=None, timeout=None):
        self.url = url
        self.data = data
        self.timeout = timeout

    def __enter__(self):
        self.resp = urllib2.urlopen(self.url, self.data, self.timeout)
        return self.resp

    def __exit__(self, type, value, traceback):
        try:
            self.resp.close()
        except Exception, e:
            pass


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
    geoip_file = os.path.normpath(os.path.expanduser(u"~/GeoIP.dat"))
    geoipcity_file = os.path.normpath(os.path.expanduser(u"~/GeoIPCity.dat"))
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
        try:
            print "GeoIP download thread started"
            req = urllib2.Request(cls.geoip_url, None, HTTP_HEADERS)
            with closing(urllib2.urlopen(req, None, 5)) as resp:
                content_length = resp.info().get("Content-Length", "0")
                last_modified = resp.info().get("Last-Modified", "0")
                info_file = "%s.info" % os.path.splitext(cls.geoip_file)[0]
                if os.path.isfile(cls.geoip_file):
                    if os.path.isfile(info_file):
                        try:
                            old_last_modified, old_content_length = map(string.strip, open(info_file, "r"))
                            if old_content_length == content_length and old_last_modified == last_modified:
                                return
                        except:
                            pass
                if resp.info().get('Content-Encoding') in ('gzip', 'x-gzip'):
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(resp.read())).read()
                else:
                    data = resp.read()
            with open(cls.geoip_file, "wb") as fp:
                fp.write(data)
            with open(info_file, "w") as fp:
                fp.writelines((last_modified, "\n", content_length))
        except Exception, e:
            logging.error("Error opening connection to %s: %s", cls.geoip_url, e)
        print "GeoIP download thread finished"

    @classmethod
    def _download_geoipcity_file(cls):
        print "GeoIPCity download thread started"
        try:
            try:
                req = urllib2.Request(cls.geoipcity_url, None, HTTP_HEADERS)
                resp = urllib2.urlopen(req, None, 5)
            except Exception, e:
                logging.error("Error opening connection to %s: %s", cls.geoipcity_url, e)
                return
            content_length = resp.info().get("Content-Length", "0")
            last_modified = resp.info().get("Last-Modified", "0")
            info_file = "%s.info" % os.path.splitext(cls.geoipcity_file)[0]
            if os.path.isfile(cls.geoipcity_file):
                if os.path.isfile(info_file):
                    try:
                        old_last_modified, old_content_length = map(string.strip, open(info_file, "r"))
                        if old_content_length == content_length and old_last_modified == last_modified:
                            return
                    except:
                        pass

            try:
                resp = urllib.urlretrieve(cls.geoipcity_url, cls.geoipcity_file + ".gz")
            except Exception, e:
                logging.error("Error opening connection to %s: %s", cls.geoipcity_url, e)
                return

            f_in = None
            try:
                f_in = gzip.open(cls.geoipcity_file + ".gz", 'rb')
            except Exception, e:
                logging.error("Error opening gzipped file %s: %s", cls.geoipcity_file + ".gz", e)
                return
            else:
                with open(cls.geoipcity_file, 'wb', 512*1024) as f_out:
                    f_out.writelines(f_in)
            finally:
                if f_in:
                    f_in.close()
            """
            resp = urllib2.urlopen(cls.geoipcity_url)
            if resp.info().get('Content-Encoding') in ('gzip', 'x-gzip'):
                data = gzip.GzipFile(fileobj=StringIO.StringIO(resp.read())).read()
            else:
                data = resp.read()
            with open(cls.geoipcity_file, "wb") as fp:
                fp.write(data)
            """
            with open(info_file, "w") as fp:
                fp.writelines((last_modified, "\n", content_length))
        except Exception, e:
            logging.error(e)
        finally:
            try:
                resp.close()
            except Exception, e:
                pass
            print "GeoIPCity download thread finished"


    @classmethod
    def get_geoip_file(cls, wait=True):
        if cls._download_geoip_thread and cls._download_geoip_thread.isAlive():
            if wait:
                cls._download_geoip_thread.join()
                cls._download_geoip_thread = None
        else:
            if ((not os.path.isfile(cls.geoip_file)
                or time.time() - os.path.getmtime(cls.geoip_file) > 60*60*24)
                and inetcache.isonline):
                print "Downloading GeoIP file in separate thread"
                cls._download_geoip_thread = threading.Thread(target=cls._download_geoip_file)
                cls._download_geoip_thread.setDaemon(True)
                cls._download_geoip_thread.start()
                if wait:
                    cls._download_geoip_thread.join()
                    cls._download_geoip_thread = None
                    print "Downloaded GeoIP file"
        #print "File %s CRC: %08X" % (cls.geoip_file, compute_file_crc32(cls.geoip_file) & 0xffffffff)
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
                print "Downloading GeoIPCity file in separate thread"
                cls._download_geoipcity_thread = threading.Thread(target=cls._download_geoipcity_file)
                cls._download_geoipcity_thread.setDaemon(True)
                cls._download_geoipcity_thread.start()
                if wait:
                    cls._download_geoipcity_thread.join()
                    cls._download_geoipcity_thread = None
                    print "Downloaded GeoIPCity file"
        #print "File %s CRC: %08X" % (cls.geoipcity_file, compute_file_crc32(cls.geoipcity_file) & 0xffffffff)
        if os.path.isfile(cls.geoipcity_file):
            return cls.geoipcity_file
        else:
            return None

Globals.__init__()



def lookup_country(ip_address):
    try:
        import pygeoip
        gif = Globals.get_geoip_file(wait=False)
        if gif:
            return pygeoip.GeoIP(gif).country_code_by_addr(ip_address)
    except ImportError:
        pass
    except Exception, e:
        logging.error(e)
    
    if inetcache.isonline:
        try:
            with closing(urllib2.urlopen(
                "http://www.geobytes.com/IpLocator.htm?GetLocation&template=php3.txt&IpAddress=%s"
                % ip_address, None, 5)) as resp:
                meta = resp.read()
            r = re.findall(r"<meta name=\"iso2\" content=\"(.*?)\">", meta)
            if r:
                return r[0]
        except Exception, e:
            logging.error(e)

    return None


def lookup_city(ip_address):
    try:
        import pygeoip

        # Download geoipcity.dat file in background
        gicf = Globals.get_geoipcity_file(wait=False)

        # If downloaded, use geoip API to get the city
        if gicf:
            r = pygeoip.GeoIP(gicf).record_by_addr(ip_address)
            if r and 'city' in r:
                return r['city']
    except ImportError:
        pass

    # If geoipcity file not present (not yet downloaded), use web API to get the city
    resp = None
    try:
        with closing(urllib2.urlopen(
            "http://www.geobytes.com/IpLocator.htm?GetLocation&template=php3.txt&IpAddress=%s"
            % ip_address, None, 5)) as resp:
            meta = resp.read()
        r = re.findall(r"<meta name=\"city\" content=\"(.*?)\">", meta)
        if r:
            return r[0]
    except Exception, e:
        logging.error(e)

    return None

