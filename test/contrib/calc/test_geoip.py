import socket
from enso.contrib.calc import geoip

IP_ADDRESS_PRAGUE_CZ = socket.gethostbyname("www.tiscali.cz")


def test_lookup_country_code():
    assert geoip.lookup_country_code(IP_ADDRESS_PRAGUE_CZ) == "CZ"


def test_lookup_city():
    assert geoip.lookup_city(IP_ADDRESS_PRAGUE_CZ) == "Prague"
    return True


if __name__ == '__main__':
    pass
