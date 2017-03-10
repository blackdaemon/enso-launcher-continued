import re
import urllib2
import logging

from contextlib import closing

from enso.contrib.calc import currconv
from enso.net import get_external_ip

RE_IP_ADDRESS = re.compile("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$")

MY_IP = get_external_ip()
HOME_CURRENCY = None

assert RE_IP_ADDRESS.match(MY_IP)

try:
    with closing(urllib2.urlopen(
            "http://getcitydetails.geobytes.com/GetCityDetails?fqcn=%s"
            % MY_IP, None, 5)) as resp:
        meta = resp.read()
    r = re.search(r"\"geobytescurrencycode\"\s*:\s*\"([A-Z]{3})\"", meta)
    if r:
        HOME_CURRENCY = r.group(1)
except Exception, e:
    logging.error(e)

assert HOME_CURRENCY


def test_guess_home_currency():
    assert currconv.guess_home_currency() == HOME_CURRENCY


def test_get_home_currency():
    assert currconv.get_home_currency() == HOME_CURRENCY
