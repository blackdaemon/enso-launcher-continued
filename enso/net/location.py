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

#==============================================================================
# Imports
#==============================================================================

import time
import threading
import re
import os
import xml.sax.saxutils
from iniparse import SafeConfigParser
from operator import itemgetter

from enso.commands import CommandManager, CommandObject
from enso.commands.factories import ArbitraryPostfixFactory
from enso import selection
from enso.messages import displayMessage
from enso.messages import Message, MessageManager
from enso.contrib.scriptotron import ensoapi
import enso.config
import enso.net

#import win32con
#import win32inet
import ctypes
import socket
import struct
import subprocess
import sqlite3

from enso.contrib.scriptotron.ensoapi import EnsoApi

LOCATION_CONFIG_FILENAME = os.path.join(
    EnsoApi().get_enso_commands_folder(), "locations.sqlite")


def get_local_ip():
    return enso.net.get_local_ip()


def get_external_ip():
    return enso.net.get_external_ip()
    """
    s = None
    ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("google.com", 0))
        ip = s.getsockname()[0]
    finally:
        if s:
            s.close()
    return ip
    """

def get_default_gateway():
    return enso.net.get_default_gateway()


def get_default_interface():
    interface = None
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


def get_mac_address(host):
    return enso.net.get_mac_address(host)

def get_current_location():
    return LocationManager.get().get_current_location()


class Location(object):

    def __init__(self, name=None, local_ip=None, external_ip=None,
        default_gateway=None, default_gateway_mac=None):
        self.name = name
        self.local_ip = local_ip
        self.external_ip = external_ip
        self.default_gateway = default_gateway
        self.default_gateway_mac = default_gateway_mac

    def __repr__(self):
        mac = ":".join(
            self.default_gateway_mac[i:i+2]
            for i in range(0, len(self.default_gateway_mac), 2)
        )
        return u"%s at %s/%s; gateway %s/%s" % (
            self.name,
            self.local_ip,
            self.external_ip,
            self.default_gateway,
            mac)

    def refresh(self):
        self.local_ip = get_local_ip()
        self.external_ip = get_external_ip()
        self.default_gateway = get_default_gateway()
        self.default_gateway_mac = get_mac_address(self.default_gateway)

    def get_name(self):
        return self.__name

    def set_name(self, name):
        self.__name = name

    name = property(get_name, set_name)

    def get_id(self):
        return self.default_gateway_mac

    id = property(get_id)

#    def __conform__(self, protocol):
#        if protocol is sqlite3.PrepareProtocol:
#            return "%s;%s;%s;%s;%s" % (
#                self.name, self.local_ip, self.external_ip,
#                self.default_gateway, self.default_gateway_mac)


def adapt_location(loc):
    return "%s;%s;%s;%s;%s" % (
        loc.name, loc.local_ip, loc.external_ip,
        loc.default_gateway, loc.default_gateway_mac)


def convert_location(loc):
    (name, lip, eip, gateway, gateway_mac) = loc.split(";")
    return Location(name, lip, eip, gateway, gateway_mac)


# Register the adapter
sqlite3.register_adapter(Location, adapt_location)

# Register the converter
sqlite3.register_converter("location", convert_location)



class LocationManager(object):

    @classmethod
    def get(cls):
        if not hasattr(enso.config, "LOCATION_MANAGER"):
            enso.config.LOCATION_MANAGER = LocationManager()
        return enso.config.LOCATION_MANAGER

    def __init__(self):
        self._create_db_if_needed()
        self._load()

    def _save(self):
        try:
            conn = sqlite3.connect(LOCATION_CONFIG_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.executemany("replace into locations(id, location) values(?,?)",
                ((l.id, l) for l in self.locations.values())
            )
            c.close()
            conn.commit()
        except sqlite3.OperationalError, e:
            pass
        finally:
            if conn:
                conn.close()
        #lc = shelve.open(LOCATION_CONFIG_FILENAME)
        #lc['locations'] = self.locations
        #lc.close()

    def _load(self):
        self.locations = {}
        try:
            conn = sqlite3.connect(LOCATION_CONFIG_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("select id,location from locations")
            for row in c.fetchall():
                print row
                self.locations[row['id']] = row['location']
            c.close()
        except sqlite3.OperationalError, e:
            pass
        finally:
            if conn:
                conn.close()
        #lc = shelve.open(LOCATION_CONFIG_FILENAME)
        #self.locations = lc.get('locations', {})
        #lc.close()

    def get_current_location(self, default_loc=None):
        gateway = get_default_gateway()
        macaddress = get_mac_address(gateway)
        loc = self.locations.get(macaddress, None)
        if not loc:
            loc = Location()
            loc.refresh()
            self.add_location(loc)
        return loc

    def get_location_by_name(self, name):
        for loc in self.locations:
            if loc.name == name:
                return loc

    def add_location(self, location):
        self.locations[location.default_gateway_mac] = location

    def delete_location(self, location_name):
        pass

    def _create_db_if_needed(self):
        try:
            conn = sqlite3.connect(LOCATION_CONFIG_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES)
            c = conn.cursor()
            c.execute("select version from config")
        except sqlite3.OperationalError, e:
            try:
                c = conn.cursor()
                c.execute('''
                create table config (version real)
                ''')
                c.execute('''
                insert into config(version) values(1)
                ''')
                c.execute('''
                create table locations(id text primary key, location location)
                ''')
            except Exception, e:
                print e
            else:
                c.close()
                conn.commit()
        finally:
            if conn:
                conn.close()
