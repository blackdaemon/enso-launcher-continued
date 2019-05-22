# vim:set ff=unix tabstop=4 shiftwidth=4 expandtab:

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
__updated__ = "2019-03-08"

#==============================================================================
# Imports
#==============================================================================

import logging
import ujson
import urllib2

from calendar import monthrange
from contextlib import closing
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from urllib2 import URLError
from httplib import HTTPException
from socket import error as SocketError


#==============================================================================
# Constants
#==============================================================================

INFLATION_TABLE = {
}

CURRENCY_TO_AREA = {
    #belarus, brazil,
    "CAD": "canada",
    "EUR": "european-union", # or eurozone?
    "FRF": "france",
    "DEM": "germany",
    #, greece, india,
    "YEN": "japan",
    #, kazakhstan, mexico,
    "RUR": "russia",
    #, spain, turkey, ukraine,
    "GBP": "united-kingdom",
    "USD": "united-states",
}

#==============================================================================
# Classes & Functions
#==============================================================================


class InflationComputationException(Exception):
    pass


def get_inflation(currency, amount, year_in_past):
    global INFLATION_TABLE, CURRENCY_TO_AREA

    assert currency and len(currency) == 3
    assert amount >= 0

    currency = currency.upper()
    if currency not in CURRENCY_TO_AREA:
        raise InflationComputationException("No inflation data for currency %s" % currency)

    today = date.today()
    if amount == 0 or year_in_past == today.year:
        return amount
    if year_in_past > today.year:
        raise InflationComputationException("Can't compute inflation for future dates")

    # Last day of the year
    start_date = date(year_in_past, 12, monthrange(year_in_past, 12)[1])
    # End of the last month
    end_date = date(today.year, today.month, 1) - relativedelta(days=1)
    # The key is YYYY-YYYYMM
    inflation_table_key = "%s%04d-%04d%02d" % (
        currency,
        start_date.year,
        end_date.year,
        end_date.month
    )
    try:
        return round(INFLATION_TABLE[inflation_table_key] * amount, 2)
    except KeyError:
        pass

    url = "https://www.statbureau.org/calculate-inflation-price-json?country=%(area)s&start=%(start)s&end=%(end)s&amount=%(amount)d&format=false" % {
            "area": CURRENCY_TO_AREA[currency],
            "start": start_date.strftime('%Y/%m/%d'),
            "end": end_date.strftime('%Y/%m/%d'),
            "amount": amount
        }
    try:
        request = urllib2.Request(url, None)
        with closing(urllib2.urlopen(request, None, 5)) as resp:
            # This should avoid blocking the main thread
            # For details see:
            # http://bugs.python.org/issue14562#msg165927
            resp.fp._rbufsize = 0
            data = resp.read()
    except (URLError, HTTPException, SocketError), e:
        logging.error(e)
        raise
    except Exception as e:
        logging.error(e)
        raise
    else:
        try:
            price = ujson.loads(data.decode("utf-8"))
            price = float(price)
        except Exception as e:
            logging.error(e)
        else:
            INFLATION_TABLE[inflation_table_key] = price / amount
            return round(price, 2)
