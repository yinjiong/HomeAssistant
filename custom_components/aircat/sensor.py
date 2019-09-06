#!/usr/bin/env python
# encoding: utf-8
import json
import socket
import select
import logging
import time

_LOGGER = logging.getLogger(__name__)

class AirCatData():
    """Class for handling the data retrieval."""

    def __init__(self, hass, macs, brightness_force_update):
        """Initialize the data object."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.settimeout(1)
        self._socket.bind(('', 9000)) # aircat.phicomm.com
        self._socket.listen(5)
        self._rlist = [self._socket]
        self.devs = {}
        self._hass = hass
        self._macs = macs
        self._brightness_force_update = brightness_force_update
        self._last_brightness = {}
        for mac, brightness_selection in macs.items():
            self._last_brightness[mac] = ""
        self._last_brightness_last_updated = {}
        for mac, brightness_selection in macs.items():
            self._last_brightness_last_updated[mac] = 0.0
    def shutdown(self):
        """Shutdown."""
        if self._socket  is not None:
            #_LOGGER.debug("Socket shutdown")
            self._socket.close()
            self._socket = None

    def loop(self):
        while True:
            self.update(None) # None = wait forever

    def update(self, timeout=0): # 0 = return right now
        rfd,wfd,efd = select.select(self._rlist, [], [], timeout)
        for fd in rfd:
            try:
                if fd is self._socket:
                    conn, addr = self._socket.accept()
                    _LOGGER.debug('Connected %s', addr)
                    self._rlist.append(conn)
                    conn.settimeout(1)
                else:
                    self.handle(fd)
            except:
                import traceback
                _LOGGER.error('Exception: %s', traceback.format_exc())

    def handle(self, conn):
        """Handle connection."""
        data = conn.recv(4096) # If connection is closed, recv() will result a timeout exception and receive '' next time, so we can purge connection list
        if not data:
            _LOGGER.error('Closed %s', conn)
            self._rlist.remove(conn)
            conn.close()
            return

        if data.startswith(b'GET'):
            _LOGGER.debug('Request from HTTP -->\n%s', data)
            conn.sendall(b'HTTP/1.0 200 OK\nContent-Type: text/json\n\n' +
                json.dumps(self.devs, indent=2).encode('utf-8'))
            self._rlist.remove(conn)
            conn.close()
            return

        end = data.rfind(b'\xff#END#')
        payload = data.rfind(b'{', 0, end)
        if payload == -1:
            payload = end
        if payload < 28: # begin(17) + mac(6)+size(5) + payload(0~) + end(6)
            _LOGGER.error('Received invalid %s', data)
            return

        mac = ''
        if payload != end:
            try:
                mac = ''.join(['%02X' % (x if isinstance(x, int) else ord(x)) for x in data[payload-11:payload-5]])
                jsonStr = data[payload:end].decode('utf-8')
                attributes = json.loads(jsonStr)
                self.devs[mac] = attributes
                _LOGGER.debug('Received %s: %s', mac, attributes)
            except:
                _LOGGER.error('Received invalid JSON: %s', data)

        if len(mac) > 0 and len(self._macs.get(mac)):
            _LOGGER.debug('mac:%s, name:%s', mac, self._macs.get(mac))
            _LOGGER.debug('brightness %s, last %s, last force update %d', self._hass.states.get("input_select." + self._macs.get(mac)).state, self._last_brightness.get(mac),self._last_brightness_last_updated.get(mac))
            brightness = self._hass.states.get("input_select." + self._macs.get(mac)).state
            if self._last_brightness.get(mac).find(brightness) != -1 and not ( self._brightness_force_update and (time.time() - self._last_brightness_last_updated.get(mac) >= 300.0) ):
                response = data[payload-28:payload-5] + b'\x00\x18\x00\x00\x02{"type":5,"status":1}\xff#END#'
            else:
                _LOGGER.info('update brightness mac:%s, name:%s, brightness:%s', mac, self._macs.get(mac),brightness)
                self._last_brightness[mac] = brightness
                self._last_brightness_last_updated[mac] = time.time()
                if brightness.find("关闭") != -1:
                    response = data[payload-28:payload-5] + b'\x00\x18\x00\x00\x02{"brightness":"%b","type":2}\xff#END#' % str(round(float(0))).encode('utf8') 
                else:
                    if brightness.find("夜间") != -1:
                        response = data[payload-28:payload-5] + b'\x00\x18\x00\x00\x02{"brightness":"%b","type":2}\xff#END#' % str(round(float(25))).encode('utf8') 
                    else:
                        response = data[payload-28:payload-5] + b'\x00\x18\x00\x00\x02{"brightness":"%b","type":2}\xff#END#' % str(round(float(50))).encode('utf8') 
                _LOGGER.info('mac:%s, Response %s', mac, response)
        else:
            response = data[payload-28:payload-5] + b'\x00\x18\x00\x00\x02{"type":5,"status":1}\xff#END#'

        _LOGGER.debug('mac:%s, Response %s', mac, response)
        conn.sendall(response)

if __name__ == '__main__':
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.addHandler(logging.StreamHandler())
    aircat = AirCatData()
    try:
        aircat.loop()
    except KeyboardInterrupt:
        pass
    aircat.shutdown()
    exit(0)


"""
Support for AirCat air sensor.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.aircat/
"""

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_MAC, CONF_SENSORS, TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv

SENSOR_PM25 = 'value'
SENSOR_HCHO = 'hcho'
SENSOR_TEMPERATURE = 'temperature'
SENSOR_HUMIDITY = 'humidity'

CONF_BFU = "brightness_force_update"

DEFAULT_NAME = 'AirCat'
DEFAULT_SENSORS = [SENSOR_PM25, SENSOR_HCHO,
                   SENSOR_TEMPERATURE, SENSOR_HUMIDITY]

SENSOR_MAP = {
    SENSOR_PM25: ('PM2.5', 'μg/m³', 'blur'),
    SENSOR_HCHO: ('HCHO', 'mg/m³', 'biohazard'),
    SENSOR_TEMPERATURE: ('Temperature', TEMP_CELSIUS, 'thermometer'),
    SENSOR_HUMIDITY: ('Humidity', '%', 'water-percent')
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MAC): dict,
    vol.Optional(CONF_BFU, default=False): cv.boolean,
    vol.Optional(CONF_SENSORS, default=DEFAULT_SENSORS):
        vol.All(cv.ensure_list, vol.Length(min=1), [vol.In(SENSOR_MAP)]),
})

AIRCAT_SENSOR_THREAD_MODE = True # True: Thread mode, False: HomeAssistant update/poll mode

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the AirCat sensor."""
    name = config[CONF_NAME]
    macs = config[CONF_MAC]
    sensors = config[CONF_SENSORS]
    brightness_force_update = config[CONF_BFU]

    aircat = AirCatData(hass, macs, brightness_force_update)
    count = len(macs)

    if AIRCAT_SENSOR_THREAD_MODE:
        import threading
        threading.Thread(target=aircat.loop).start()
    else:
        AirCatSensor.times = 0
        AirCatSensor.interval = 60

    devices = []
    index = 0
    for mac, brightness in macs.items():
        for sensor_type in sensors:
            _LOGGER.debug("add sensor for mac:%s", mac)
            devices.append(AirCatSensor(aircat,
                name + str(index + 1) if index else name,
                mac, sensor_type))
        index += 1

    add_devices(devices)

class AirCatSensor(Entity):
    """Implementation of a AirCat sensor."""

    def __init__(self, aircat, name, mac, sensor_type):
        """Initialize the AirCat sensor."""
        sensor_name, unit, icon = SENSOR_MAP[sensor_type]
        self._name = name + ' ' + sensor_name
        self._mac = mac
        self._sensor_type = sensor_type
        self._unit = unit
        self._icon = 'mdi:' + icon
        self._aircat = aircat

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self.attributes is not None

    @property
    def state(self):
        """Return the state of the device."""
        attributes = self.attributes
        if attributes is None:
            return None
        state = attributes[self._sensor_type]
        if self._sensor_type == SENSOR_PM25:
            return state
        elif self._sensor_type == SENSOR_HCHO:
            return float(state) / 1000
        else:
            return round(float(state), 1)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self.attributes if self._sensor_type == SENSOR_PM25 else None

    @property
    def attributes(self):
        """Return the attributes of the device."""
        if self._mac:
            return self._aircat.devs.get(self._mac)
        for mac in self._aircat.devs:
            return self._aircat.devs[mac]
        return None

    def update(self):
        """Update state."""
        if AIRCAT_SENSOR_THREAD_MODE:
            #_LOGGER.debug("Running in thread mode")
            return

        if AirCatSensor.times % AirCatSensor.interval == 0:
            _LOGGER.debug("Begin update %d: %s %s", AirCatSensor.times,
                self._mac, self._sensor_type)
            self._aircat.update()
            _LOGGER.debug("Ended update %d: %s %s", AirCatSensor.times,
                self._mac, self._sensor_type)
        AirCatSensor.times += 1

    def shutdown(self, event):
        """Signal shutdown."""
        #_LOGGER.debug('Shutdown')
        self._aircat.shutdown()