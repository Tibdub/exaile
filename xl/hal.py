# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import dbus

from xl import common

import logging
logger = logging.getLogger(__name__)


class HAL(object):
    """
        HAL interface
    """
    def __init__(self, devicemanager):
        self.devicemanager = devicemanager
        
        self.bus = None
        self.hal = None

        self.handlers = {}
        self.hal_devices = {}

    def connect(self):
        try:
            self.bus = dbus.SystemBus()
            hal_obj = self.bus.get_object('org.freedesktop.Hal', 
                '/org/freedesktop/Hal/Manager')
            self.hal = dbus.Interface(hal_obj, 'org.freedesktop.Hal.Manager')
            logger.debug("Connected to HAL")
            return True
        except:
            logger.warning("Failed to connect to HAL, autodetection of devices will be disabled.")
            return False

    def add_handler(self, handler):
        self.handlers[handler.name] = handler
        udis = handler.get_udis(self)
        for udi in udis:
            self.add_device(udi)

    def remove_handler(self, name):
        del self.handlers[name]

    def get_handler(self, udi):
        dev_obj = self.bus.get_object("org.freedesktop.Hal", udi)
        device = dbus.Interface(dev_obj, "org.freedesktop.Hal.Device")
        capabilities = device.GetProperty("info.capabilities")
        for handler in self.handlers.itervalues():
            if handler.is_type(device, capabilities):
                return handler
        return None

    @common.threaded
    def add_device(self, device_udi):
        handler = self.get_handler(device_udi)
        if handler is None:
            logger.debug("Found no HAL device handler for %s"%device_udi)
            return

        dev = handler.device_from_udi(self, device_udi)
        if not dev: return
        dev.connect()

        self.devicemanager.add_device(dev)
        self.hal_devices[device_udi] = dev

    def remove_device(self, device_udi):
        try:
            self.devicemanager.remove_device(self.hal_devices[device_udi])
            del self.hal_devices[device_udi]
        except KeyError:
            pass

    def setup_device_events(self):
        self.bus.add_signal_receiver(self.add_device,
                "DeviceAdded")
        self.bus.add_signal_receiver(self.remove_device,
                "DeviceRemoved")


class Handler(object):
    name = 'base'
    def __init__(self):
        pass

    def is_type(self, device, capabilities):
        return False
    
    def get_udis(self, hal):
        return []

    def device_from_udi(self, hal, udi):
        pass


# vim: et sts=4 sw=4

