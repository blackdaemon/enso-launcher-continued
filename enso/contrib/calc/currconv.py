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
import re
import datetime
import urllib
import urllib2
import logging

import geoip
from enso.net import inetcache

from urllib2 import URLError
from httplib import HTTPException
from socket import error as SocketError
from contextlib import closing

import enso.net
from enso.contrib.scriptotron.ensoapi import EnsoApi
from enso.quasimode import Quasimode

try:
    from iniparse import SafeConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser


#==============================================================================
# Constants
#==============================================================================

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.12) Gecko/20101028 Firefox/3.6.12',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-us,en;q=0.5',
}

class Globals(object):
    INI_FILE = os.path.expanduser(u"~/enso_calc.ini")
    HOME_CURRENCY = None


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


class ExchangeRates( object ):
    # Following will be filled with actual currency exchange rates data
    # in _get_exchange_rates():
    exchange_rates = {
        "AED":{"name":"United Arab Emirates Dirham", "rate":None, "updated":None},
        "AFN":{"name":"Afghanistan Afghani", "rate":None, "updated":None},
        "ALL":{"name":"Albanian Lek", "rate":None, "updated":None},
        "AMD":{"name":"Armenian Dram", "rate":None, "updated":None},
        "ANG":{"name":"Netherlands Antilles Guilder (Florin)",
            "rate":None, "updated":None},
        "AOA":{"name":"Angola Kwanza", "rate":None, "updated":None},
        "ARS":{"name":"Argentinian Peso", "rate":None, "updated":None},
        "AUD":{"name":"Australian Dollar", "rate":None, "updated":None},
        "AWG":{"name":"Aruban Guilder (Florin)", "rate":None, "updated":None},
        "AZN":{"name":"Azerbaijan New Manat", "rate":None, "updated":None},
        "BAM":{"name":"Bosnia and Herzegovina Convertible Marka",
            "rate":None, "updated":None},
        "BBD":{"name":"Barbados Dollar", "rate":None, "updated":None},
        "BDT":{"name":"Bangladesh Taka", "rate":None, "updated":None},
        "BGN":{"name":"Bulgarian Lev", "rate":None, "updated":None},
        "BHD":{"name":"Bahraini Dinar", "rate":None, "updated":None},
        "BIF":{"name":"Burundi Franc", "rate":None, "updated":None},
        "BMD":{"name":"Bermuda Dollar", "rate":None, "updated":None},
        "BND":{"name":"Brunei Darussalam Dollar", "rate":None, "updated":None},
        "BOB":{"name":"Bolivian Boliviano", "rate":None, "updated":None},
        "BRL":{"name":"Brazilian Real", "rate":None, "updated":None},
        "BSD":{"name":"Bahamas Dollar", "rate":None, "updated":None},
        "BTN":{"name":"Bhutan Ngultrum", "rate":None, "updated":None},
        "BWP":{"name":"Botswana Pula", "rate":None, "updated":None},
        "BYR":{"name":"Belarussian Ruble", "rate":None, "updated":None},
        "BZD":{"name":"Belize Dollar", "rate":None, "updated":None},
        "CAD":{"name":"Canadian Dollar", "rate":None, "updated":None},
        "CDF":{"name":"Congo/Kinshasa Congolese Franc",
            "rate":None, "updated":None},
        "CHF":{"name":"Swiss Franc", "rate":None, "updated":None},
        "CLP":{"name":"Chilean Peso", "rate":None, "updated":None},
        "CNY":{"name":"Chinese Yuan Renminbi", "rate":None, "updated":None},
        "COP":{"name":"Colombian Peso", "rate":None, "updated":None},
        "CRC":{"name":"Costa Rican Colon", "rate":None, "updated":None},
        "CUP":{"name":"Cuban Peso", "rate":None, "updated":None},
        "CVE":{"name":"Cape Verde Escudo", "rate":None, "updated":None},
        "CZK":{"name":"Czech Koruna", "rate":None, "updated":None},
        "DJF":{"name":"Djibouti Franc", "rate":None, "updated":None},
        "DKK":{"name":"Danish Krone", "rate":None, "updated":None},
        "DOP":{"name":"Dominican Peso", "rate":None, "updated":None},
        "DZD":{"name":"Algerian Dinar", "rate":None, "updated":None},
        "EEK":{"name":"Estonian Kroon", "rate":None, "updated":None},
        "EGP":{"name":"Egyptian Pound", "rate":None, "updated":None},
        "ERN":{"name":"Eritrea Nakfa", "rate":None, "updated":None},
        "ETB":{"name":"Ethiopian Birr", "rate":None, "updated":None},
        "EUR":{"name":"Euro", "rate":None, "updated":None},
        "FJD":{"name":"Fiji Dollar", "rate":None, "updated":None},
        "FKP":{"name":"Falkland Islands (Malvinas) Pounds",
            "rate":None, "updated":None},
        "GBP":{"name":"British Pound", "rate":None, "updated":None},
        "GEL":{"name":"Georgia Lari", "rate":None, "updated":None},
        "GGP":{"name":"Guernsey Pound", "rate":None, "updated":None},
        "GHC":{"name":"Ghanian Cedi", "rate":None, "updated":None},
        "GIP":{"name":"Gibraltar Pound", "rate":None, "updated":None},
        "GMD":{"name":"Gambia Dalasi", "rate":None, "updated":None},
        "GNF":{"name":"Guinea Franc", "rate":None, "updated":None},
        "GTQ":{"name":"Guatemala Quetzal", "rate":None, "updated":None},
        "GYD":{"name":"Guyana Dollar", "rate":None, "updated":None},
        "HKD":{"name":"Hong Kong Dollar", "rate":None, "updated":None},
        "HNL":{"name":"Honduras Lempira", "rate":None, "updated":None},
        "HRK":{"name":"Croatian Kuna", "rate":None, "updated":None},
        "HTG":{"name":"Haitian Gourde", "rate":None, "updated":None},
        "HUF":{"name":"Hungarian Forint", "rate":None, "updated":None},
        "IDR":{"name":"Indonesian Rupiah", "rate":None, "updated":None},
        "ILS":{"name":"Israel New Shekel", "rate":None, "updated":None},
        "IMP":{"name":"Isle of Man Pound", "rate":None, "updated":None},
        "INR":{"name":"Indian Rupee", "rate":None, "updated":None},
        "IQD":{"name":"Iraq Dinar", "rate":None, "updated":None},
        "IRR":{"name":"Iran Rial", "rate":None, "updated":None},
        "ISK":{"name":"Iceland Krona", "rate":None, "updated":None},
        "JEP":{"name":"Jersey Pound", "rate":None, "updated":None},
        "JMD":{"name":"Jamaican Dollar", "rate":None, "updated":None},
        "JOD":{"name":"Jordanian Dinar", "rate":None, "updated":None},
        "JPY":{"name":"Japanese Yen", "rate":None, "updated":None},
        "KES":{"name":"Kenyan Shilling", "rate":None, "updated":None},
        "KGS":{"name":"Kyrgyzstan Som", "rate":None, "updated":None},
        "KHR":{"name":"Cambodian Riel", "rate":None, "updated":None},
        "KMF":{"name":"Comoros Franc", "rate":None, "updated":None},
        "KPW":{"name":"North Korean Won", "rate":None, "updated":None},
        "KRW":{"name":"South Korean Won", "rate":None, "updated":None},
        "KWD":{"name":"Kuwait Dinar", "rate":None, "updated":None},
        "KYD":{"name":"Cayman Islands Dollar", "rate":None, "updated":None},
        "KZT":{"name":"Kazakhstan Tenge", "rate":None, "updated":None},
        "LAK":{"name":"Laos Kip", "rate":None, "updated":None},
        "LBP":{"name":"Lebanese Pound", "rate":None, "updated":None},
        "LKR":{"name":"Sri Lanka Rupee", "rate":None, "updated":None},
        "LRD":{"name":"Liberian Dollar", "rate":None, "updated":None},
        "LSL":{"name":"Lesotho Maloti", "rate":None, "updated":None},
        "LTL":{"name":"Lithuanian Lita", "rate":None, "updated":None},
        "LVL":{"name":"Latvian Lat", "rate":None, "updated":None},
        "LYD":{"name":"Libya Dinars", "rate":None, "updated":None},
        "MAD":{"name":"Moroccan Dirham", "rate":None, "updated":None},
        "MDL":{"name":"Moldova Lei", "rate":None, "updated":None},
        "MGA":{"name":"Madagascar Ariary", "rate":None, "updated":None},
        "MKD":{"name":"Macedonia Denars", "rate":None, "updated":None},
        "MMK":{"name":"Myanmar Kyat", "rate":None, "updated":None},
        "MNT":{"name":"Mongolian Tugrik", "rate":None, "updated":None},
        "MOP":{"name":"Macau Pataca", "rate":None, "updated":None},
        "MRO":{"name":"Mauritania Ouguiya", "rate":None, "updated":None},
        "MUR":{"name":"Mauritius Rupee", "rate":None, "updated":None},
        "MVR":{"name":"Maldives Rufiyan", "rate":None, "updated":None},
        "MWK":{"name":"Malawi Kwacha", "rate":None, "updated":None},
        "MXN":{"name":"Mexican Peso", "rate":None, "updated":None},
        "MYR":{"name":"Malaysian Ringgit", "rate":None, "updated":None},
        "MZN":{"name":"Mozambique Metical", "rate":None, "updated":None},
        "NAD":{"name":"Namibian Dollar", "rate":None, "updated":None},
        "NGN":{"name":"Nigerian Naira", "rate":None, "updated":None},
        "NIO":{"name":"Nicaraguan Cordoba", "rate":None, "updated":None},
        "NOK":{"name":"Norwegian Krone", "rate":None, "updated":None},
        "NPR":{"name":"Nepal Rupee", "rate":None, "updated":None},
        "NZD":{"name":"New Zealand Dollar", "rate":None, "updated":None},
        "OMR":{"name":"Oman Rial", "rate":None, "updated":None},
        "PAB":{"name":"Panama Balboa", "rate":None, "updated":None},
        "PEN":{"name":"Peruvian Nuevo Sol", "rate":None, "updated":None},
        "PGK":{"name":"Papua New Guinea Kina", "rate":None, "updated":None},
        "PHP":{"name":"Philippines Peso", "rate":None, "updated":None},
        "PKR":{"name":"Pakistani Rupee", "rate":None, "updated":None},
        "PLN":{"name":"Polish Zloty", "rate":None, "updated":None},
        "PYG":{"name":"Paraguay Guarani", "rate":None, "updated":None},
        "QAR":{"name":"Qatari Rial", "rate":None, "updated":None},
        "RON":{"name":"Romania New Lei", "rate":None, "updated":None},
        "RSD":{"name":"Serbia Dinars", "rate":None, "updated":None},
        "RUB":{"name":"Russian Ruble", "rate":None, "updated":None},
        "RWF":{"name":"Rwanda Franc", "rate":None, "updated":None},
        "SAR":{"name":"Saudi Arabian Riyal", "rate":None, "updated":None},
        "SBD":{"name":"Solomon Islands Dollar", "rate":None, "updated":None},
        "SCR":{"name":"Seychelles Rupee", "rate":None, "updated":None},
        "SDG":{"name":"Sudan Pound", "rate":None, "updated":None},
        "SEK":{"name":"Swedish Krona", "rate":None, "updated":None},
        "SGD":{"name":"Singapore Dollar", "rate":None, "updated":None},
        "SHP":{"name":"St. Helena Pound", "rate":None, "updated":None},
        "SLL":{"name":"Sierra Leone Leone", "rate":None, "updated":None},
        "SOS":{"name":"Somalia Shillings", "rate":None, "updated":None},
        "SPL":{"name":"Seborga Luigini", "rate":None, "updated":None},
        "SRD":{"name":"Suriname Dollars", "rate":None, "updated":None},
        "STD":{"name":u"S\u00E3o Tome and Principe Dobra",
            "rate":None, "updated":None},
        "SVC":{"name":"El Salvador Colon", "rate":None, "updated":None},
        "SYP":{"name":"Syria Pound", "rate":None, "updated":None},
        "SZL":{"name":"Swaziland Emalangeni", "rate":None, "updated":None},
        "THB":{"name":"Thai Baht", "rate":None, "updated":None},
        "TJS":{"name":"Tajikistan Somoni", "rate":None, "updated":None},
        "TMM":{"name":"Turkmenistan Manat", "rate":None, "updated":None},
        "TND":{"name":"Tunisian Dinar", "rate":None, "updated":None},
        "TOP":{"name":"Tonga Pa'anga", "rate":None, "updated":None},
        "TRY":{"name":"Turkey New Lira", "rate":None, "updated":None},
        "TTD":{"name":"Trinidad Dollar", "rate":None, "updated":None},
        "TWD":{"name":"Taiwan New Dollar", "rate":None, "updated":None},
        "TZS":{"name":"Tanzanian Shilling", "rate":None, "updated":None},
        "UAH":{"name":"Ukrainian Hryvnia", "rate":None, "updated":None},
        "UGX":{"name":"Ugandan Shilling", "rate":None, "updated":None},
        "USD":{"name":"US Dollar", "rate":None, "updated":None},
        "UYU":{"name":"Uruguay Peso", "rate":None, "updated":None},
        "UZS":{"name":"Uzbekistan Sum", "rate":None, "updated":None},
        "VEF":{"name":"Venezuelan Bolivar", "rate":None, "updated":None},
        "VND":{"name":"Vietnam Dong", "rate":None, "updated":None},
        "VUV":{"name":"Vanuatu Vatu", "rate":None, "updated":None},
        "WST":{"name":"Samoa Tala", "rate":None, "updated":None},
        "XAF":{"name":"CFA Franc (BEAC)", "rate":None, "updated":None},
        "XAG":{"name":"Silver Ounces", "rate":None, "updated":None},
        "XAU":{"name":"Gold Ounces", "rate":None, "updated":None},
        "XCD":{"name":"East Caribbean Dollar", "rate":None, "updated":None},
        "XDR":{"name":"International Monetary Fund (IMF) Special Drawing Rights",
            "rate":None, "updated":None},
        "XOF":{"name":"CFA Franc (BCEAO)", "rate":None, "updated":None},
        "XPD":{"name":"Palladium Ounces", "rate":None, "updated":None},
        "XPF":{"name":"CFP Franc", "rate":None, "updated":None},
        "XPT":{"name":"Platinum Ounces", "rate":None, "updated":None},
        "YER":{"name":"Yemen Rials", "rate":None, "updated":None},
        "ZAR":{"name":"South African Rand", "rate":None, "updated":None},
        "ZMK":{"name":"Zambia Kwacha", "rate":None, "updated":None},
        "ZWD":{"name":"Zimbabwean Dollar", "rate":None, "updated":None},
    }

    RATES_FILENAME = os.path.join(
        EnsoApi().get_enso_commands_folder(), "exchange_rates.db")

    def __init__(self):
        self.exchange_rates.update(self._load_rates())
        actual_rates = self._download_actual_rates()
        if actual_rates:
            self.exchange_rates.update(actual_rates)
            self._save_rates(self.exchange_rates)

    def _load_rates(self):
        if not os.path.isfile(self.RATES_FILENAME):
            return {}
        rates = {}
        for line in file(self.RATES_FILENAME).readlines():
            symbol, name, rate, updated = line.strip().split("|")
            try:
                updated = datetime.datetime.strptime(updated, "%Y-%m-%d %H:%M:%S")
            except:
                updated = None
            rates[symbol] = {
                "name": name,
                "rate": float(rate),
                "updated": updated
                }
        return rates

    def _save_rates(self, rates):
        file(self.RATES_FILENAME, "w").writelines(
            ("%s|%s|%s|%s\n" %
                (symbol,
                data["name"],
                data["rate"],
                data["updated"].strftime("%Y-%m-%d %H:%M:%S")
                    if data["updated"]
                    else "")
            )
            for (symbol, data)
            in self.exchange_rates.iteritems()
        )

    def _download_csv(self, url):
        csv = None
        try:
            request = urllib2.Request(url, None, HTTP_HEADERS)
            with closing(urllib2.urlopen(request, None, 10)) as resp:
                csv = resp.read()
        except (URLError, HTTPException, SocketError), e:
            logging.error(e)
            raise
        return csv

    def _download_actual_rates(self):
        """ Download current exchange rates table for predefined currenct symbols
        from finance.yahoo.com
        """
        #TODO: Download also user's home currency rates for more precise results

        def parse_rates(csv):
            rates = {}
            for line in csv.splitlines():
                code = None
                try:
                    code, rate_s, bid, offer, last_date, last_time = line.split(",")
                    symbol = code.strip("\"")[3:6].upper()
                    try:
                        rate = float(rate_s)
                    except ValueError, e:
                        logging.warn(
                            "Currency exchange rate returned for code '%s' is not parseable: %s",
                            str(code), rate_s)
                        rate = float(0)
                    last_date = last_date.strip("\"")
                    updated = None
                    if last_date != "N/A":
                        #last_datetime = "%s %s" % (last_date, last_time)
                        #updated = datetime.datetime.strptime(last_datetime, "%m/%d/%Y %I:%M%p")

                        month, day, year = map(int, last_date.split("/"))
                        last_time = last_time.strip("\"")
                        if last_time != "N/A":
                            hour, minute = last_time.split(":")
                            hour = int(hour)
                            if minute.endswith("pm"):
                                if hour < 12:
                                    hour += 12
                            minute = int(minute[:-2])
                        updated = datetime.datetime(year, month, day, hour, minute)
                    name = self.exchange_rates.get(symbol, {"name":None})["name"]
                    rates[symbol] = {
                        "name":name,
                        "rate":rate,
                        "updated":updated
                    }
                    if rate == 0.0:
                        logging.warning(
                            "Currency exchange data returned for code '%s' unhandled; empty data received.",
                            code
                            )
                except Exception, e:
                    logging.error(
                        "Currency exchange data returned for code '%s' are not parseable: %s",
                        str(code), e)
            return rates

        rates = {}
        symbols = []
        max_rates_per_request = 200 # Limit one query to 200 items
        url = "http://download.finance.yahoo.com/d/quotes.csv?f=sl1bad1t1&e=.csv&s=%(params)s"
        for symbol in self.exchange_rates.iterkeys():
            symbols.append("EUR%s=X" % symbol)
            if len(symbols) == max_rates_per_request:
                try:
                    csv = self._download_csv(url % {"params": "+".join(symbols)})
                except Exception, e:
                    break
                else:
                    if csv:
                        rates.update(parse_rates(csv))
                symbols = []
        else:
            if len(symbols) > 0:
                try:
                    csv = self._download_csv(url % {"params": "+".join(symbols)})
                except Exception, e:
                    pass
                else:
                    if csv:
                        rates.update(parse_rates(csv))
                symbols = []

        return rates


RATES = ExchangeRates()

"""
def _cache_currencies():
    html = _get_html("http://www.google.com/finance/converter")

    if html is None:
        logging.error("Error caching currencies, no HTML data returned.")
        return

    sel_start = html.find("<select name=\"from\"")
    if sel_start == -1:
        sel_start = html.find("<select name=from")
    if sel_start > -1:
        sel_end = html.find("</select>", sel_start)
        r = re.compile(r"<option .*value=\"(.*)\".*>(.*)</option>", re.IGNORECASE)
        for item in r.finditer(html, sel_start, sel_end):
            currency, currency_desc = item.groups()
            _from_currencies[currency] = currency_desc

    sel_start = html.find("<select name=\"to\"")
    if sel_start == -1:
        sel_start = html.find("<select name=to")
    if sel_start > -1:
        sel_end = html.find("</select>", sel_start)
        r = re.compile(r"<option .*value=\"(.*)\".*>(.*)</option>", re.IGNORECASE)
        for item in r.finditer(html, sel_start, sel_end):
            currency, currency_desc = item.groups()
            _to_currencies[currency] = currency_desc

    logging.info("Cached currency symbols: %i" % len(_to_currencies))
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug(_to_currencies)
"""

complete_currency_re = re.compile(
    r"(.*)(" +
    "|".join(RATES.exchange_rates.keys()) +
    ") (in|to) (" +
    "|".join(RATES.exchange_rates.keys()) +
    ")(.*)",
    re.IGNORECASE)


partial_currency_re = re.compile(
    r"(in|to) (" +
    "|".join(RATES.exchange_rates.keys()) +
    ")(.*)",
    re.IGNORECASE)


def is_supported_currency(iso):
    if not iso:
        return False
    return iso.upper() in RATES.exchange_rates


def urlopen(url, timeout=None):
    fp = None
    if timeout is not None:
        try:
            proxy_support = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_support)
            # Use urllib2 with timeout on Python >= 2.6
            fp = opener.open(url, timeout=timeout)
        except (TypeError, ImportError), e:
            fp = urllib.urlopen(url)
    else:
        fp = urllib.urlopen(url)
    return fp

def guess_home_currency():
    logging.info("Guessing user's local currency")

    conn = None
    ext_ip = None
    try:
        logging.info("Getting external IP address...")
        ext_ip = enso.net.get_external_ip()
        logging.info("External IP address: %s", ext_ip)
    except Exception, e:
        logging.error("Error getting external IP address: %s", e)
    else:
        logging.info("Lookup country by IP address...")
        try:
            import ccy
        except ImportError:
            logging.warning("Python-package 'ccy' is not installed. Currency lookup-by-country will not be available.")
        else:
            try:
                import geoip
            except ImportError:
                logging.warning("Python-package 'pygeoip' is not installed. Currency lookup-by-country will not be available.")
            else:
                try:
                    # TODO: Reasonably cache this
                    c = geoip.lookup_country(ext_ip)
                    if c:
                        logging.info("Country by IP: %s", c)
                        logging.info("Lookup currency by country...")
                        curr = ccy.countryccy(c)
                        logging.info("Local currency: %s", curr)
                        return curr
                except Exception, e:
                    logging.error(e)
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

    # If all above failed, try t query geobytes directly for curency code
    # TODO: Reasonably cache this
    if ext_ip and inetcache.isonline:
        try:
            with closing(urllib2.urlopen(
                "http://getcitydetails.geobytes.com/GetCityDetails?fqcn=%s"
                % ext_ip, None, 5)) as resp:
                meta = resp.read()
            r = re.search(r"\"geobytescurrencycode\"\s*:\s*\"([A-Z]{3})\"", meta)
            if r:
                return r.group(1)
        except Exception, e:
            logging.error(e)
            
    #import ip2country
    #print ip2country.IP2Country(verbose=True).lookup(ext_ip)

    #import whois
    #nic_client = whois.NICClient()
    #flags = whois.NICClient.WHOIS_QUICK
    #print nic_client.whois_lookup({}, ext_ip, flags)

    #import pycountry
    #country = pycountry.countries.get(alpha2=c)
    #print dir(country)

    logging.info("Reading local currency from locale settings...")
    import locale
    locale.setlocale(locale.LC_ALL, '')
    curr = locale.localeconv()['int_curr_symbol']
    if curr:
        logging.info("Local currency: %s", curr)
    else:
        curr = 'EUR'
        logging.info("Setting local currency to default: %s", curr)
    return curr


def get_home_currency():
    if Globals.HOME_CURRENCY is None:
        config = SafeConfigParser()
        config.read(Globals.INI_FILE)
        if config.has_section("defaults") and config.has_option("defaults", "home_currency"):
            hc = config.get("defaults", "home_currency")
        else:
            hc = guess_home_currency()
        Globals.HOME_CURRENCY = hc
    return Globals.HOME_CURRENCY

get_home_currency()


def set_home_currency(curr):
    Globals.HOME_CURRENCY = curr
    config = SafeConfigParser()
    config.read(Globals.INI_FILE)
    if not config.has_section("defaults"):
        config.add_section("defaults")
    config.set("defaults", "home_currency", curr)
    with open(Globals.INI_FILE, "w") as fp:
        config.write(fp)


quasimode = Quasimode.get()

def currency(amount, from_curr, to_curr):
    #TODO: Convert following assertions into custom exceptions
    assert from_curr in RATES.exchange_rates.keys(), "Unknown source currency code: %s" % from_curr
    assert to_curr in RATES.exchange_rates.keys(), "Unknown target currency code: %s" % to_curr

    unknown_rates = []
    result = None
    rate = None
    rate_updated = None

    if from_curr == "EUR":
        if RATES.exchange_rates[to_curr]["rate"] == 0:
            unknown_rates.append(to_curr)
        else:
            rate = RATES.exchange_rates[to_curr]["rate"]
            rate_updated = RATES.exchange_rates[to_curr]["updated"]
            result = rate * amount
    elif to_curr == "EUR":
        if RATES.exchange_rates[from_curr]["rate"] == 0:
            unknown_rates.append(from_curr)
        else:
            rate = 1 / RATES.exchange_rates[from_curr]["rate"]
            rate_updated = RATES.exchange_rates[to_curr]["updated"]
            result = rate * amount
    else:
        # How to correctly calculate this?
        if RATES.exchange_rates[from_curr]["rate"] == 0:
            unknown_rates.append(from_curr)
        if RATES.exchange_rates[to_curr]["rate"] == 0:
            unknown_rates.append(to_curr)
        if not unknown_rates:
            in_eur = round(amount / RATES.exchange_rates[from_curr]["rate"], 4)
            result = RATES.exchange_rates[to_curr]["rate"] * in_eur

    if unknown_rates:
        quasimode.setDidyoumeanHint(
            u"Unknown exchange rate for currency %s"
            % ",".join(unknown_rates))
    #result2 = currency1(amount, from_curr, to_curr)
    #if result2 != result:
    #    print "Currency computed: %f; currency Google: %f" % (result, result2)
    expr = "%s %s in %s" % ( # (rate %s from %s)
        ("%.4f" % amount).rstrip("0").rstrip("."),
        from_curr, #exchange_rates[from_curr][0],
        to_curr, #exchange_rates[to_curr][0]
        #("%.4f" % rate).rstrip("0").rstrip("."),
        #rate_updated
        )
    """
    suggestions = set(symbol for symbol in RATES.exchange_rates.keys() if symbol.startswith((from_curr[0], to_curr[0])))
    suggestions = suggestions - set((from_curr, to_curr))
    if suggestions:
        quasimode.setDidyoumeanHint(" or ".join(suggestions))
    else:
        quasimode.setDidyoumeanHint(None)
    """
    return result, expr, rate, rate_updated

"""
def currency1(amount, from_curr, to_curr):
    result = 1.0 * int(amount)
    url = "http://www.google.com/finance/converter?a=%d&from=%s&to=%s" % (
        amount, from_curr.upper(), to_curr.upper())
    print url
    html = _get_html(url)
    #print html
    r = re.compile(r"<div id=\"?currency_converter_result\"?[^>]*>(.*?)</div>", re.IGNORECASE | re.DOTALL)
    m = r.search(html)
    if m:
        result_text = re.sub(r'<[^>]*?>', '', m.group(1).strip()).replace("&nbsp;", " ")
        m = re.search(r"\= ([0-9\.]+) [A-Z]{3}", result_text)
        if m:
            result = 1.0 * float(m.group(1))
            print result
    return result
"""

def _handle_currency_symbols(expression):
    logging.info(expression)
    symbol_table = [
        (u"\u20ac([0-9\\.]+)", "EUR"),
        (u"\u00a3([0-9\\.]+)", "GBP"),
        (u"\\$([0-9\\.]+)", "USD"),
        (u"\u00a5([0-9\.]+)", "JPY"),
        (u"([0-9\\.]+)(,-)?K\u010d", "CZK")
    ]
    fixed_expression = expression
    currency = None
    amount = None
    for r, symbol in symbol_table:
        m = re.search(r, expression, re.IGNORECASE | re.UNICODE)
        if m:
            fixed_expression = "%s%s" % (m.group(1), symbol)
            currency = symbol
            amount = m.group(1)
            break

    return fixed_expression, currency, amount


def convert_expression(expression):
    currconv_match = complete_currency_re.search(expression)
    if currconv_match:
        #print "currconv match"
        if currconv_match.group(1):
            amount = currconv_match.group(1)
            print amount
        else:
            amount = 1
        expression = "currency(%s, '%s', '%s') %s" % (
            amount,
            currconv_match.group(3).upper(),
            currconv_match.group(4).upper(),
            currconv_match.group(5))
        #print expression
    else:
        currconv_match = partial_currency_re.match(expression.strip())
        if currconv_match:
            #print "partial match"
            amount_str, from_currency, amount = _handle_currency_symbols(
                "1".replace(" ", ""))
            #print amount_str, from_currency, amount
            #print currconv_match.groups()
            expression = "currency(%s, '%s', '%s') %s" % (
                amount,
                from_currency,
                currconv_match.group(2).upper(),
                currconv_match.group(3)
            )
    return expression


# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab: