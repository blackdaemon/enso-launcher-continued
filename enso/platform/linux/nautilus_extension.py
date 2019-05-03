"""
This is a Nautilus Extension to provide file selection to Enso
"""

import gi
gi.require_version('GObject', '2.0')
from gi.repository import GObject
gi.require_version('Nautilus', '3.0')
from gi.repository import Nautilus

import dbus
from dbus.gobject_service import ExportedGObject
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)

SERVICE_NAME = "enso.nautilus_ext.FileSelection"
INTERFACE_NAME = "enso.nautilus_ext.FileSelection"
OBJECT_PATH = "/enso/nautilus_ext/FileSelection"


class Object (ExportedGObject):
    @dbus.service.signal(INTERFACE_NAME, signature="asi")
    def SelectionChanged(self, uris, window_id):
        """
        Nautilus selection changed.

        @uris: an array of URI strings.
        @window_id: An ID for the window where the selection happened
        """
        _ = window_id
        return uris


class EnsoFileSelectionProvider(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        self.cursel = None
        self.max_threshold = 500
        try:
            session_bus = dbus.Bus()
        except dbus.DBusException as e:
            print e
            self.service = None
        else:
            if False: #session_bus.name_has_owner(SERVICE_NAME):
                print "service is None"
                self.service = None
            else:
                bus_name = dbus.service.BusName(SERVICE_NAME, bus=session_bus)
                self.service = Object(bus_name, object_path=OBJECT_PATH)
                print self.service

    def get_file_items(self, window, files):
        """
        Get list of files selected in Nautilus window
        """
        if len(files) > self.max_threshold:
            return []
        window_id = window.get_window().get_xid() if window.get_window() else 0
        uris = [f.get_uri() for f in files]
        if self.cursel != (uris, window_id) and self.service:
            print "Calling service with ",uris, window_id
            self.service.SelectionChanged(uris, window_id)
        self.cursel = (uris, window_id)
        return []

    # Workaround following error:
    # ** (nautilus:22019): CRITICAL **: nautilus_menu_provider_get_background_items: assertion 'NAUTILUS_IS_MENU_PROVIDER (provider)' failed
    def get_background_items(self, window, file_):
        _ = window
        _ = file_
        return None
