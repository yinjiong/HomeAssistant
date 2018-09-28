"""
Support for Phicomm DC1 switch.
Developer by NETYJ
version 2.0 server
"""

import logging
import time
import datetime
import json
import re
import select
import voluptuous as vol
from socket import socket, AF_INET, SOCK_STREAM

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import (CONF_NAME, CONF_MAC)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)
_INTERVAL = 1

SCAN_INTERVAL = datetime.timedelta(seconds=_INTERVAL)
DEFAULT_NAME = 'dc1'
CONF_PORTS = 'ports'
CONF_IP = 'ip'

ATTR_STATE = "switchstate"
ATTR_NAME = "switchname"
ATTR_I = "i"
ATTR_V = "v"
ATTR_P = "p"
ATTR_TOTALELECT = "totalelect"

CONNECTION_LISTS = []

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_IP): cv.string,
   vol.Required(CONF_PORTS): dict
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Phicomm DC1 switch."""

    name = config.get(CONF_NAME)
    ports = config.get(CONF_PORTS)
    ip = config.get(CONF_IP)
    dc1sock = socket(AF_INET, SOCK_STREAM)
    dc1sock.settimeout(1)
    try:
        dc1sock.bind(("0.0.0.0", 8000))
        dc1sock.listen(5)
        PhicommDC1Switch.connection_list.append(dc1sock)
        _LOGGER.warning("PhicommDC1Switch server started on port 8000")
    except OSError as e:
        _LOGGER.warning("PhicommDC1Switch server got %s", e)
        time.sleep(0.1)
        pass


    devs = []
    portls = []
    i = 1
    for item1, item2 in ports.items():
        portls.append(PhicommDC1Port(hass, item2, i))
        i += 1

    devs.append(PhicommDC1Switch(hass, ip, PhicommDC1Switch.connection_list, name, portls))
    devs.append(portls[0])
    devs.append(portls[1])
    devs.append(portls[2])

    add_devices(devs)


class PhicommDC1Port(SwitchDevice):
    """Representation of a port of DC1 Smart Plug switch."""

    def __init__(self, hass, name, iport):
        """Initialize the switch."""
        self._hass = hass
        self._name = name
        self._iport = iport
        self.sw = None
        self._state = False
        self._state_attrs = {
            ATTR_STATE: False,
            ATTR_NAME: None,
        }

    @property
    def name(self):
        """Return the name of the Smart Plug, if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def current_power_watt(self):
        """Return the current power usage in Watt."""
        # try:
        #    return float(self.data.current_consumption)
        # except ValueError:
        return None

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state_attrs[ATTR_STATE]

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        if self.sw is None:
            _LOGGER.debug('sw is none')
            return None
        # elif self.sw._state is False:
        #     _LOGGER.debug('self st is false')
        #     return None
        elif self.sw._state_attrs[ATTR_STATE] is False:
            _LOGGER.debug('sw ATTR_STATE is false')
            return None

        self._state_attrs[ATTR_STATE] = True
        self._state_attrs[ATTR_STATE] = self.sw.pressPlug(self._iport, True)
        _LOGGER.debug(
            'after set, self._state_attrs[ATTR_STATE] is %s', self._state_attrs[ATTR_STATE])

    def turn_off(self):
        """Turn the switch off."""
        if self.sw is None:
            _LOGGER.debug('sw is none')
            return None
        # elif self.sw._state is False:
        #     _LOGGER.debug('self st is false')
        #     return None
        elif self.sw._state_attrs[ATTR_STATE] is False:
            _LOGGER.debug('sw ATTR_STATE is false')
            return None

        self._state_attrs[ATTR_STATE] = False
        self._state_attrs[ATTR_STATE] = self.sw.pressPlug(self._iport, False)
        _LOGGER.debug(
            'after set, self._state_attrs[ATTR_STATE] is %s', self._state_attrs[ATTR_STATE])

    def setSwitch(self, switchDC1):
        self.sw = switchDC1
        return None


class PhicommDC1Switch(SwitchDevice):
    """Representation of a DC1 Smart Plug switch."""
    connection_list = []

    def __init__(self, hass, ip, connection_list, name, ports):
        """Initialize the switch."""
        self._hass = hass
        self._name = name
        self._ip = ip
        self._connection_list = connection_list
        self.sock = PhicommDC1Switch.connection_list[0]
        self.data = []
        self.iClientEmptyLogCount = 0
        self._ports = ports
        self._ports[0].setSwitch(self)
        self._ports[1].setSwitch(self)
        self._ports[2].setSwitch(self)
        self._state = False
        self.data = []
        self.control_payload = ""

        self._state_attrs = {
            ATTR_STATE: False,
            ATTR_NAME: None,
            ATTR_I: None,
            ATTR_V: None,
            ATTR_P: None,
            ATTR_TOTALELECT: None,
        }

    @property
    def name(self):
        """Return the name of the Smart Plug, if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return False

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def current_power_watt(self):
        """Return the current power usage in Watt."""
        # try:
        #    return float(self.data.current_consumption)
        # except ValueError:
        return None

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state_attrs[ATTR_STATE]

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        # if self._state is False:
        #     return None
        self._state_attrs[ATTR_STATE] = True
        self._state_attrs[ATTR_STATE] = self.pressPlug(0, True)

    def turn_off(self):
        """Turn the switch off."""
        # if self._state is False:
        #     return None
        self._state_attrs[ATTR_STATE] = False
        self._state_attrs[ATTR_STATE] = self.pressPlug(0, False)

    def pressPlug(self, iport, fOn):
        # if self._state is False:
        #     return False

        try:
            uuid = int(round(time.time() * 1000))
            i = 0
            if self._ports[2]._state_attrs[ATTR_STATE] is True:
                i |= 0b1000
            if self._ports[1]._state_attrs[ATTR_STATE] is True:
                i |= 0b100
            if self._ports[0]._state_attrs[ATTR_STATE] is True:
                i |= 0b10
            if self._state_attrs[ATTR_STATE] is True:
                i |= 0b1

            if fOn is False:
                i &= ~(1 << iport)
            else:
                i |= 1 << iport
            strT = bin(int(i))
            _LOGGER.debug('strT:%s, i:%d', strT, i)
            strT = strT[2:len(strT)]
            payload = bytes(
                '{"action":"datapoint=","params":{"status":' + str(strT) + '},"uuid":"' + str(uuid) + '","auth":""}\n',
                encoding="utf8")
            _LOGGER.debug('payload:%s', payload)

            self.control_payload = payload
            return fOn

        except OSError as e:
            _LOGGER.error("pressPlug OSError: %s", e)
            return not fOn

    def shutdown(self, event):
        """Signal shutdown."""
        _LOGGER.warning('Shutdown')
        try:
            for sock in self._connection_list:
                if sock is not self.sock:
                    sock.shutdown(2)
                    sock.close()
            self.sock.close()
        except OSError as e:
            pass
 
    def update(self):
        """Get the latest data from the smart plug and updates the states."""
        try:
            uuid = str(int(round(time.time() * 1000)))

            heart_msg = bytes('{"uuid":"T' + uuid + '","params":{},"auth":"","action":"datapoint"}\n', encoding="utf8")

            fNeedBreak = False

            for sockA in self._connection_list:
                try:
                    _LOGGER.debug("PhicommDC1Switch find sockA %s, self.sock %s" , sockA, self.sock)
                    if sockA is self.sock:
                        continue
                    elif sockA.getpeername() is None:
                        _LOGGER.debug("PhicommDC1Switch find wrong sockA %s" , sockA)
                    elif sockA.getpeername()[0].find(self._ip) == -1:
                        _LOGGER.debug("PhicommDC1Switch find other sockA %s" , sockA.getpeername())
                        continue
                    else:
                        _LOGGER.debug("PhicommDC1Switch find this sockA %s" , sockA.getpeername())
                        try:
                            if not self.control_payload:
                                sockA.sendall(heart_msg)
                            else:
                                sockA.sendall(self.control_payload)
                                self.control_payload = ""
                                fNeedBreak = True

                            self.iCount = 0
                            _LOGGER.debug('PhicommDC1Switch Force send a heartbeat to %s', sockA.getpeername())
                            break
                        except OSError as e:
                            _LOGGER.warning(
                                "PhicommDC1Switch Force send a heartbeat got %s. Closing socket", e)
                            try:
                                sockA.shutdown(2)
                                sockA.close()
                            except OSError:
                                pass
                            self._connection_list.remove(sockA)
                            continue
                except OSError as e:
                    _LOGGER.error(
                        'sock except:%s sock:%s', e, sockA)
                    self._connection_list.remove(sockA)
                    #sockA.shutdown(2)
                    sockA.close()
                    continue

            if fNeedBreak is True:
                return None

            read_sockets, write_sockets, error_sockets = select.select(
                self._connection_list, [], self._connection_list, 0)
            if len(self._connection_list) is 1:
                self.iClientEmptyLogCount += 1
                if self.iClientEmptyLogCount is 13:
                    _LOGGER.warning("PhicommDC1Switch Client list is empty")
                    self.iClientEmptyLogCount = 0
                    return None
            else:
                self.iClientEmptyLogCount = 0

            for sockE in error_sockets:
                if sockE in self._connection_list:
                    _LOGGER.warning("PhicommDC1Switch (%s) disconnected" , sockE)
                    self._connection_list.remove(sockE)
                    sockE.close()

            for sock in read_sockets:
                _LOGGER.debug(
                    "PhicommDC1Switch find read socket %s", sock)
                try:
                    if sock is self.sock:
                        _LOGGER.warning(
                            "PhicommDC1Switch going to accept new connection")
                        try:
                            sockfd, addr = self.sock.accept()
                            sockfd.settimeout(1)
                            self._connection_list.append(sockfd)
                            _LOGGER.warning(
                                "PhicommDC1Switch Client (%s, %s) connected" % addr)
                            try:
                                # sockfd.sendall(heart_msg)
                                if not self.control_payload:
                                    sockfd.sendall(heart_msg)
                                else:
                                    sockfd.sendall(self.control_payload)
                                    self.control_payload = ""
                                _LOGGER.warning(
                                    "PhicommDC1Switch Force send a heartbeat:%s", heart_msg)
                            except OSError as e:
                                _LOGGER.warning(
                                    "PhicommDC1Switch Client error %s", e)
                                sock.shutdown(2)
                                sock.close()
                                self._connection_list.remove(sockfd)
                                continue
                        except OSError:
                            _LOGGER.warning(
                                "PhicommDC1Switch Client accept failed")
                            continue
                    elif sock.getpeername()[0].find(self._ip) != -1:
                        data = None
                        try:
                            _LOGGER.debug(
                                "PhicommDC1Switch Processing Client %s", sock.getpeername())
                            data = sock.recv(1024)
                        except OSError as e:
                            _LOGGER.warning("PhicommDC1Switch Processing Client error %s", e)
                            try:
                                sock.shutdown(2)
                                sock.close()
                            except OSError:
                                pass
                            self._connection_list.remove(sock)
                            break
                        if data:
                            data = str(data, encoding="utf8")
                            _LOGGER.debug("data: %s", data)
                            jsonData = self.parseJsonData(data)
                            _LOGGER.debug("jsondata: %s", jsonData)
                            if jsonData is not None:
                                # 状态包
                                try:
                                    if str(jsonData['msg']) == 'set datapoint success':
                                        _LOGGER.debug("set datapoint success")
    
                                    if str(jsonData['status']) == '200':
                                        i = int(
                                            str(jsonData['result']['status']), base=2)
                                        _LOGGER.debug('switch state i %d', i)
                                        if i & 0b1 == 0:
                                            self._state_attrs[ATTR_STATE] = False
                                        else:
                                            self._state_attrs[ATTR_STATE] = True
                                        if i & 0b10 == 0 or self._state_attrs[ATTR_STATE] is False:
                                            self._ports[0]._state_attrs[ATTR_STATE] = False
                                        else:
                                            self._ports[0]._state_attrs[ATTR_STATE] = True
                                        if i & 0b100 == 0 or self._state_attrs[ATTR_STATE] is False:
                                            self._ports[1]._state_attrs[ATTR_STATE] = False
                                        else:
                                            self._ports[1]._state_attrs[ATTR_STATE] = True
                                        if i & 0b1000 == 0 or self._state_attrs[ATTR_STATE] is False:
                                            self._ports[2]._state_attrs[ATTR_STATE] = False
                                        else:
                                            self._ports[2]._state_attrs[ATTR_STATE] = True
                                        _LOGGER.debug('switch state is %s, 1:%s, 2:%s, 3:%s v:%sv, p:%sw',
                                                    self._state_attrs[ATTR_STATE],
                                                    self._ports[0]._state_attrs[ATTR_STATE], self._ports[
                                                        1]._state_attrs[ATTR_STATE],
                                                    self._ports[2]._state_attrs[ATTR_STATE], self._state_attrs[ATTR_V],
                                                    self._state_attrs[ATTR_P])
    
                                        self._state_attrs.update(
                                            {ATTR_I: str(jsonData['result']['I'])})
                                        self._state_attrs.update(
                                            {ATTR_V: str(jsonData['result']['V'])})
                                        self._state_attrs.update(
                                            {ATTR_P: str(jsonData['result']['P'])})
    
                                except KeyError as e:
                                    _LOGGER.warning(e)
                                    pass
                            else:
                                _LOGGER.error(
                                    'get switch plugs state error, %s, payload:%s', jsonData, heart_msg)
                                return None
                                break
                        else:
                            _LOGGER.error(
                                'get deviceid plugs state error, payload:%s', heart_msg)
                            return None
                            break
                except OSError as e:
                    _LOGGER.error(
                        'sock except:%s sock:%s', e, sock)
                    self._connection_list.remove(sock)
                    #sock.shutdown(2)
                    sock.close()
                    continue

        except KeyError as e:
        #except OSError as e:
            _LOGGER.error("update OSError: %s", e)

    def parseJsonData(self, data):
        pattern = r"(\{.*?\})(?=\n)"
        jsonStr = re.findall(pattern, str(data), re.M)
        l = len(jsonStr)
        if l > 0:
            return json.loads(jsonStr[l - 1])
        else:
            return None
