# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:
import shutil
from six import BytesIO

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
# 1.0    [pavelvitis] Initial version
#==============================================================================

__author__ = "pavelvitis@gmail.com"
__module_version__ = __version__ = "1.0"
__updated__ = "2018-06-21"

#==============================================================================
# Imports
#==============================================================================

import sys
import os
import urllib2
import logging
import ujson
import urllib
import struct
import time

from urllib2 import URLError, HTTPError
from httplib import HTTPException
from socket import error as SocketError
from contextlib import closing

try:
    from io import BytesIO as _StringIO
except ImportError as e:
    try:
        from cStringIO import StringIO as _StringIO
    except ImportError:
        from StringIO import StringIO as _StringIO

try:
    import gzip
except ImportError as e:
    logging.error(e)
    gzip = None

try:
    import zlib
except ImportError as e:
    logging.error(e)
    zlib = None

try:
    import regex as re
except ImportError as e:
    import re

try:
    from iniparse import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser

from enso.utils.decorators import suppress


#==============================================================================
# Constants
#==============================================================================

CACHED_RATES_TIMEOUT = 60 * 60  # 1 hour

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.12) Gecko/20101028 Firefox/3.6.12',
    'Accept-Charset': 'utf-8;q=0.7,*;q=0.7',
    #    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    #    'Accept-Language': 'en-us,en;q=0.5',
    #    'Cache-Control': 'no-cache, no-store, must-revalidate',
    #    'Pragma': 'no-cache',
    #    'Expires': '0',
}

# FIXME: This needs to work on all platforms
# FIXME: Read this from shared configuration
CACHE_DIR = os.path.expanduser(u"~/.cache/enso/cmd_calculate")
if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)
RATES_FILE = os.path.join(CACHE_DIR, "rates.csv")
CURRENCIES_FILE = os.path.join(CACHE_DIR, "currencies.json")


#==============================================================================
# Classes & Functions
#==============================================================================

# Force no-proxy
# TODO: Setup proxy in configuration
urllib2.install_opener(
    urllib2.build_opener(
        urllib2.ProxyHandler({})
    )
)

DEFAULT_CURRENCY_LIST = {
    "AED": {"name": "United Arab Emirates Dirham", "rate": None, "updated": None},
    "AFN": {"name": "Afghanistan Afghani", "rate": None, "updated": None},
    "ALL": {"name": "Albanian Lek", "rate": None, "updated": None},
    "AMD": {"name": "Armenian Dram", "rate": None, "updated": None},
    "ANG": {"name": "Netherlands Antilles Guilder (Florin)",
            "rate": None, "updated": None},
    "AOA": {"name": "Angola Kwanza", "rate": None, "updated": None},
    "ARS": {"name": "Argentinian Peso", "rate": None, "updated": None},
    "AUD": {"name": "Australian Dollar", "rate": None, "updated": None},
    "AWG": {"name": "Aruban Guilder (Florin)", "rate": None, "updated": None},
    "AZN": {"name": "Azerbaijan New Manat", "rate": None, "updated": None},
    "BAM": {"name": "Bosnia and Herzegovina Convertible Marka",
            "rate": None, "updated": None},
    "BBD": {"name": "Barbados Dollar", "rate": None, "updated": None},
    "BDT": {"name": "Bangladesh Taka", "rate": None, "updated": None},
    "BGN": {"name": "Bulgarian Lev", "rate": None, "updated": None},
    "BHD": {"name": "Bahraini Dinar", "rate": None, "updated": None},
    "BIF": {"name": "Burundi Franc", "rate": None, "updated": None},
    "BMD": {"name": "Bermuda Dollar", "rate": None, "updated": None},
    "BND": {"name": "Brunei Darussalam Dollar", "rate": None, "updated": None},
    "BOB": {"name": "Bolivian Boliviano", "rate": None, "updated": None},
    "BRL": {"name": "Brazilian Real", "rate": None, "updated": None},
    "BSD": {"name": "Bahamas Dollar", "rate": None, "updated": None},
    "BTN": {"name": "Bhutan Ngultrum", "rate": None, "updated": None},
    "BWP": {"name": "Botswana Pula", "rate": None, "updated": None},
    "BYR": {"name": "Belarussian Ruble", "rate": None, "updated": None},
    "BZD": {"name": "Belize Dollar", "rate": None, "updated": None},
    "CAD": {"name": "Canadian Dollar", "rate": None, "updated": None},
    "CDF": {"name": "Congo/Kinshasa Congolese Franc",
            "rate": None, "updated": None},
    "CHF": {"name": "Swiss Franc", "rate": None, "updated": None},
    "CLP": {"name": "Chilean Peso", "rate": None, "updated": None},
    "CNY": {"name": "Chinese Yuan Renminbi", "rate": None, "updated": None},
    "COP": {"name": "Colombian Peso", "rate": None, "updated": None},
    "CRC": {"name": "Costa Rican Colon", "rate": None, "updated": None},
    "CUP": {"name": "Cuban Peso", "rate": None, "updated": None},
    "CVE": {"name": "Cape Verde Escudo", "rate": None, "updated": None},
    "CZK": {"name": "Czech Koruna", "rate": None, "updated": None},
    "DJF": {"name": "Djibouti Franc", "rate": None, "updated": None},
    "DKK": {"name": "Danish Krone", "rate": None, "updated": None},
    "DOP": {"name": "Dominican Peso", "rate": None, "updated": None},
    "DZD": {"name": "Algerian Dinar", "rate": None, "updated": None},
    "EEK": {"name": "Estonian Kroon", "rate": None, "updated": None},
    "EGP": {"name": "Egyptian Pound", "rate": None, "updated": None},
    "ERN": {"name": "Eritrea Nakfa", "rate": None, "updated": None},
    "ETB": {"name": "Ethiopian Birr", "rate": None, "updated": None},
    "EUR": {"name": "Euro", "rate": None, "updated": None},
    "FJD": {"name": "Fiji Dollar", "rate": None, "updated": None},
    "FKP": {"name": "Falkland Islands (Malvinas) Pounds",
            "rate": None, "updated": None},
    "GBP": {"name": "British Pound", "rate": None, "updated": None},
    "GEL": {"name": "Georgia Lari", "rate": None, "updated": None},
    "GGP": {"name": "Guernsey Pound", "rate": None, "updated": None},
    "GHC": {"name": "Ghanian Cedi", "rate": None, "updated": None},
    "GIP": {"name": "Gibraltar Pound", "rate": None, "updated": None},
    "GMD": {"name": "Gambia Dalasi", "rate": None, "updated": None},
    "GNF": {"name": "Guinea Franc", "rate": None, "updated": None},
    "GTQ": {"name": "Guatemala Quetzal", "rate": None, "updated": None},
    "GYD": {"name": "Guyana Dollar", "rate": None, "updated": None},
    "HKD": {"name": "Hong Kong Dollar", "rate": None, "updated": None},
    "HNL": {"name": "Honduras Lempira", "rate": None, "updated": None},
    "HRK": {"name": "Croatian Kuna", "rate": None, "updated": None},
    "HTG": {"name": "Haitian Gourde", "rate": None, "updated": None},
    "HUF": {"name": "Hungarian Forint", "rate": None, "updated": None},
    "IDR": {"name": "Indonesian Rupiah", "rate": None, "updated": None},
    "ILS": {"name": "Israel New Shekel", "rate": None, "updated": None},
    "IMP": {"name": "Isle of Man Pound", "rate": None, "updated": None},
    "INR": {"name": "Indian Rupee", "rate": None, "updated": None},
    "IQD": {"name": "Iraq Dinar", "rate": None, "updated": None},
    "IRR": {"name": "Iran Rial", "rate": None, "updated": None},
    "ISK": {"name": "Iceland Krona", "rate": None, "updated": None},
    "JEP": {"name": "Jersey Pound", "rate": None, "updated": None},
    "JMD": {"name": "Jamaican Dollar", "rate": None, "updated": None},
    "JOD": {"name": "Jordanian Dinar", "rate": None, "updated": None},
    "JPY": {"name": "Japanese Yen", "rate": None, "updated": None},
    "KES": {"name": "Kenyan Shilling", "rate": None, "updated": None},
    "KGS": {"name": "Kyrgyzstan Som", "rate": None, "updated": None},
    "KHR": {"name": "Cambodian Riel", "rate": None, "updated": None},
    "KMF": {"name": "Comoros Franc", "rate": None, "updated": None},
    "KPW": {"name": "North Korean Won", "rate": None, "updated": None},
    "KRW": {"name": "South Korean Won", "rate": None, "updated": None},
    "KWD": {"name": "Kuwait Dinar", "rate": None, "updated": None},
    "KYD": {"name": "Cayman Islands Dollar", "rate": None, "updated": None},
    "KZT": {"name": "Kazakhstan Tenge", "rate": None, "updated": None},
    "LAK": {"name": "Laos Kip", "rate": None, "updated": None},
    "LBP": {"name": "Lebanese Pound", "rate": None, "updated": None},
    "LKR": {"name": "Sri Lanka Rupee", "rate": None, "updated": None},
    "LRD": {"name": "Liberian Dollar", "rate": None, "updated": None},
    "LSL": {"name": "Lesotho Maloti", "rate": None, "updated": None},
    "LTL": {"name": "Lithuanian Lita", "rate": None, "updated": None},
    "LVL": {"name": "Latvian Lat", "rate": None, "updated": None},
    "LYD": {"name": "Libya Dinars", "rate": None, "updated": None},
    "MAD": {"name": "Moroccan Dirham", "rate": None, "updated": None},
    "MDL": {"name": "Moldova Lei", "rate": None, "updated": None},
    "MGA": {"name": "Madagascar Ariary", "rate": None, "updated": None},
    "MKD": {"name": "Macedonia Denars", "rate": None, "updated": None},
    "MMK": {"name": "Myanmar Kyat", "rate": None, "updated": None},
    "MNT": {"name": "Mongolian Tugrik", "rate": None, "updated": None},
    "MOP": {"name": "Macau Pataca", "rate": None, "updated": None},
    "MRO": {"name": "Mauritania Ouguiya", "rate": None, "updated": None},
    "MUR": {"name": "Mauritius Rupee", "rate": None, "updated": None},
    "MVR": {"name": "Maldives Rufiyan", "rate": None, "updated": None},
    "MWK": {"name": "Malawi Kwacha", "rate": None, "updated": None},
    "MXN": {"name": "Mexican Peso", "rate": None, "updated": None},
    "MYR": {"name": "Malaysian Ringgit", "rate": None, "updated": None},
    "MZN": {"name": "Mozambique Metical", "rate": None, "updated": None},
    "NAD": {"name": "Namibian Dollar", "rate": None, "updated": None},
    "NGN": {"name": "Nigerian Naira", "rate": None, "updated": None},
    "NIO": {"name": "Nicaraguan Cordoba", "rate": None, "updated": None},
    "NOK": {"name": "Norwegian Krone", "rate": None, "updated": None},
    "NPR": {"name": "Nepal Rupee", "rate": None, "updated": None},
    "NZD": {"name": "New Zealand Dollar", "rate": None, "updated": None},
    "OMR": {"name": "Oman Rial", "rate": None, "updated": None},
    "PAB": {"name": "Panama Balboa", "rate": None, "updated": None},
    "PEN": {"name": "Peruvian Nuevo Sol", "rate": None, "updated": None},
    "PGK": {"name": "Papua New Guinea Kina", "rate": None, "updated": None},
    "PHP": {"name": "Philippines Peso", "rate": None, "updated": None},
    "PKR": {"name": "Pakistani Rupee", "rate": None, "updated": None},
    "PLN": {"name": "Polish Zloty", "rate": None, "updated": None},
    "PYG": {"name": "Paraguay Guarani", "rate": None, "updated": None},
    "QAR": {"name": "Qatari Rial", "rate": None, "updated": None},
    "RON": {"name": "Romania New Lei", "rate": None, "updated": None},
    "RSD": {"name": "Serbia Dinars", "rate": None, "updated": None},
    "RUB": {"name": "Russian Ruble", "rate": None, "updated": None},
    "RWF": {"name": "Rwanda Franc", "rate": None, "updated": None},
    "SAR": {"name": "Saudi Arabian Riyal", "rate": None, "updated": None},
    "SBD": {"name": "Solomon Islands Dollar", "rate": None, "updated": None},
    "SCR": {"name": "Seychelles Rupee", "rate": None, "updated": None},
    "SDG": {"name": "Sudan Pound", "rate": None, "updated": None},
    "SEK": {"name": "Swedish Krona", "rate": None, "updated": None},
    "SGD": {"name": "Singapore Dollar", "rate": None, "updated": None},
    "SHP": {"name": "St. Helena Pound", "rate": None, "updated": None},
    "SLL": {"name": "Sierra Leone Leone", "rate": None, "updated": None},
    "SOS": {"name": "Somalia Shillings", "rate": None, "updated": None},
    "SPL": {"name": "Seborga Luigini", "rate": None, "updated": None},
    "SRD": {"name": "Suriname Dollars", "rate": None, "updated": None},
    "STD": {"name": u"S\u00E3o Tome and Principe Dobra",
            "rate": None, "updated": None},
    "SVC": {"name": "El Salvador Colon", "rate": None, "updated": None},
    "SYP": {"name": "Syria Pound", "rate": None, "updated": None},
    "SZL": {"name": "Swaziland Emalangeni", "rate": None, "updated": None},
    "THB": {"name": "Thai Baht", "rate": None, "updated": None},
    "TJS": {"name": "Tajikistan Somoni", "rate": None, "updated": None},
    "TMM": {"name": "Turkmenistan Manat", "rate": None, "updated": None},
    "TND": {"name": "Tunisian Dinar", "rate": None, "updated": None},
    "TOP": {"name": "Tonga Pa'anga", "rate": None, "updated": None},
    "TRY": {"name": "Turkey New Lira", "rate": None, "updated": None},
    "TTD": {"name": "Trinidad Dollar", "rate": None, "updated": None},
    "TWD": {"name": "Taiwan New Dollar", "rate": None, "updated": None},
    "TZS": {"name": "Tanzanian Shilling", "rate": None, "updated": None},
    "UAH": {"name": "Ukrainian Hryvnia", "rate": None, "updated": None},
    "UGX": {"name": "Ugandan Shilling", "rate": None, "updated": None},
    "USD": {"name": "US Dollar", "rate": None, "updated": None},
    "UYU": {"name": "Uruguay Peso", "rate": None, "updated": None},
    "UZS": {"name": "Uzbekistan Sum", "rate": None, "updated": None},
    "VEF": {"name": "Venezuelan Bolivar", "rate": None, "updated": None},
    "VND": {"name": "Vietnam Dong", "rate": None, "updated": None},
    "VUV": {"name": "Vanuatu Vatu", "rate": None, "updated": None},
    "WST": {"name": "Samoa Tala", "rate": None, "updated": None},
    "XAF": {"name": "CFA Franc (BEAC)", "rate": None, "updated": None},
    "XAG": {"name": "Silver Ounces", "rate": None, "updated": None},
    "XAU": {"name": "Gold Ounces", "rate": None, "updated": None},
    "XCD": {"name": "East Caribbean Dollar", "rate": None, "updated": None},
    "XDR": {"name": "International Monetary Fund (IMF) Special Drawing Rights",
            "rate": None, "updated": None},
    "XOF": {"name": "CFA Franc (BCEAO)", "rate": None, "updated": None},
    "XPD": {"name": "Palladium Ounces", "rate": None, "updated": None},
    "XPF": {"name": "CFP Franc", "rate": None, "updated": None},
    "XPT": {"name": "Platinum Ounces", "rate": None, "updated": None},
    "YER": {"name": "Yemen Rials", "rate": None, "updated": None},
    "ZAR": {"name": "South African Rand", "rate": None, "updated": None},
    "ZMK": {"name": "Zambia Kwacha", "rate": None, "updated": None},
    "ZWD": {"name": "Zimbabwean Dollar", "rate": None, "updated": None},
}


class NotModifiedSince(Exception):
    pass


def _decompress_response(resp):
    # FIXME: This code should go to a library, it is repeated too many times
    assert isinstance(resp, urllib.addinfourl)
    content_encoding = resp.info().get(
        "Content-Encoding",
        resp.info().get("content-encoding", None)
    )
    result_html = None
    data = resp.read()
    if data and 'gzip' == content_encoding:
        try:
            result_html = gzip.GzipFile(fileobj=BytesIO(data)).read()
        except (EOFError, IOError, struct.error) as e:
            logging.error(e)
            # IOError can occur if the gzip header is bad.
            # struct.error can occur if the data is damaged.
            if isinstance(e, struct.error):
                # A gzip header was found but the data is corrupt.
                # Ideally, we should re-request the feed without the
                # 'Accept-encoding: gzip' header, but we don't.
                result_html = None
        else:
            assert logging.debug("currency updater decompressing gzipped response %d->%d" % (len(data), len(result_html))) or True
    elif data and 'deflate' == content_encoding:
        try:
            result_html = zlib.decompress(data)
        except zlib.error as e:
            try:
                # The data may have no headers and no checksum.
                result_html = zlib.decompress(data, -15)
            except zlib.error as e:
                logging.error(e)
        else:
            assert logging.debug("bmw.py decompressing deflated response %d->%d" %
                                 (len(data), len(result_html))) or True
    else:
        result_html = data
    return result_html


def _download_data(url, modifiedsince=None):
    data = None
    try:
        if modifiedsince:
            HTTP_HEADERS['If-Modified-Since'] = time.strftime(
                '%a, %d %b %Y %H:%M:%S GMT', time.gmtime(modifiedsince))
        request = urllib2.Request(url, None, HTTP_HEADERS)
        with closing(urllib2.urlopen(request, None, 5)) as resp:
            print resp.headers
            if resp.code == 304:
                raise NotModifiedSince()
            # This should avoid blocking the main thread
            # For details see:
            # http://bugs.python.org/issue14562#msg165927
            resp.fp._rbufsize = 0
            data = _decompress_response(resp)
            """
            charset = "utf-8"
            with suppress(Exception):
                content_type = resp.headers.get(
                    "Content-Type", resp.headers.get("content-type", "")).lower()
                if content_type and "charset=" in content_type:
                    charset = content_type.split("charset=")[-1]
            try:
                decoded = data.decode(charset)
            except Exception as e:
                logging.error(
                    "currency updater unicode decoding failed: %s", e)
            """
    except (URLError, HTTPException, SocketError), e:
        logging.error(e)
        raise
    return data


def download_actual_rates():
    """ Download current exchange rates table for predefined currenct symbols
    from finance.yahoo.com
    """
    if not os.path.isdir(os.path.dirname(RATES_FILE)):
        os.makedirs(os.path.dirname(RATES_FILE))

    mtime = os.path.getmtime(RATES_FILE) if os.path.isfile(RATES_FILE) else 0
    # Skip bothering the web service if latest download is not older than 1 hour
    if ((time.time() - mtime) / 60 < 60):
        logging.warning("Skipping the rates download for now due to exceeded limit (maximum of 100 queries per hour)")
        return

    currencies = {}
    if (not os.path.isfile(CURRENCIES_FILE) or
        os.path.getsize(CURRENCIES_FILE) == 0 or
        (time.time() - os.path.getmtime(CURRENCIES_FILE)) / 60 / 60 > 24
        ):
        currencies_url = "http://free.currencyconverterapi.com/api/v5/currencies"
        try:
            mtime = os.path.getmtime(CURRENCIES_FILE) if os.path.isfile(CURRENCIES_FILE) else 0
            currencies_json = _download_data(currencies_url, mtime).decode("utf-8")
            currencies = ujson.loads(currencies_json)
            if currencies and currencies.get('results', None):
                currencies = currencies['results']
            else:
                logging.warning("Service returned 0 currencies.")
                return
        except HTTPError as e:
            if e.code == 403:
                # Exceeded limit
                raise Exception("Currency converter service free limit exceeded (100 queries per hour)")
        except Exception as e:
            logging.error(e)
        else:
            try:
                with open("%s.new" % CURRENCIES_FILE, "wb") as fd:
                    fd.write(currencies_json.encode("utf-8", "ignore"))
            except Exception as e:
                raise
            else:
                shutil.move("%s.new" % CURRENCIES_FILE, CURRENCIES_FILE)
    else:
        with open(CURRENCIES_FILE, "rb") as fd:
            currencies_json = ujson.load(fd)
            if currencies_json:
                currencies = currencies_json.get('results', [])

    mtime = os.path.getmtime(RATES_FILE) if os.path.isfile(RATES_FILE) else 0
    currency_symbols = currencies.keys()

    if not currency_symbols:
        currency_symbols = DEFAULT_CURRENCY_LIST.keys()

    if "USD" not in currency_symbols:
        currency_symbols.append("USD")

    symbols = []
    # Limit one query to 2 items
    max_rates_per_request = 2
    url = "https://free.currencyconverterapi.com/api/v5/convert?compact=ultra&q=%(params)s"
    csv = ""

    for symbol in currency_symbols:
        symbols.append("EUR_%s" % symbol)
        if len(symbols) == max_rates_per_request:
            try:
                data = _download_data(url % {"params": ",".join(symbols)}, mtime)
                rd = eval(data.strip(), {}, {})
                csv = ("" if not csv or csv.endswith("\n") else "\n").join(
                    [csv,] + ["%s,%f\n" % (r[0].split("_")[1], r[1]) for r in rd.items()]
                )
            except HTTPError as e:
                if e.code == 403:
                    # Exceeded limit
                    raise Exception("Currency converter service free limit exceeded (100 queries per hour)")
            except Exception as e:
                logging.error("Error downloading rates file: %s", e)
                raise
            del symbols[:]
    else:
        if len(symbols) > 0:
            try:
                data = _download_data(url % {"params": ",".join(symbols)}, mtime)
                rd = eval(data.strip(), {}, {})
                csv = ("" if not csv or csv.endswith("\n") else "\n").join(
                    [csv,] + ["%s,%f\n" % (r[0].split("_")[1], r[1]) for r in rd.items()]
                )
            except HTTPError as e:
                if e.code == 403:
                    # Exceeded limit
                    raise Exception("Currency converter service free limit exceeded (100 queries per hour)")
            except Exception as e:
                logging.error("Error downloading rates file: %s", e)
                raise
            del symbols[:]

    if not csv:
        return 0

    try:
        with open("%s.new" % RATES_FILE, "wb") as fd:
            fd.write(csv.encode("utf-8"))
    except Exception as e:
        raise
    else:
        shutil.move("%s.new" % RATES_FILE, RATES_FILE)
        os.utime(RATES_FILE)

    return len(currency_symbols)


def main(argv=None):
    try:
        count = download_actual_rates()
        logging.info("Updated %d currencies", count)
        return 0
    except Exception as e:
        logging.error(e)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
