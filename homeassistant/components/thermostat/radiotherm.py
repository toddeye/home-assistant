"""
homeassistant.components.thermostat.radiotherm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Adds support for Radio Thermostat wifi-enabled home thermostats

Config:
thermostat:
    platform: radiotherm
    hold_temp: boolean to control if hass temp adjustments hold(True) or are
        temporary(False) (default: False)
    away_delta: number of degrees to change target temperature  when 'away'
        (default: 10)
    host: list of thermostat host/ips to control

Example:
thermostat:
    platform: radiotherm
    hold_temp: True
    away_delta: 5
    host:
        - 192.168.99.137
        - 192.168.99.202

Configure two thermostats via the configuration.yaml.  Temperature settings
sent from hass will be sent to thermostat and then hold at that temp.  Set
to False if you set a thermostat schedule on the tstat itself and just want
hass to send temporary temp changes.  If Away mode is triggered, change target
temp by 5 degrees.

"""
import logging
import datetime
from urllib.error import URLError

from homeassistant.components.thermostat import (ThermostatDevice, STATE_COOL,
                                                 STATE_IDLE, STATE_HEAT)
from homeassistant.const import (CONF_HOST, TEMP_FAHRENHEIT)

REQUIREMENTS = ['radiotherm==1.2']

HOLD_TEMP = 'hold_temp'
AWAY_DELTA = 'away_delta'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the Radio Thermostat. """
    import radiotherm

    logger = logging.getLogger(__name__)

    hosts = []
    if CONF_HOST in config:
        hosts = config[CONF_HOST]
    else:
        hosts.append(radiotherm.discover.discover_address())

    if hosts is None:
        logger.error("no radiotherm thermostats detected")
        return

    hold_temp = config.get(HOLD_TEMP, False)
    away_delta = config.get(AWAY_DELTA, 10)
    tstats = []

    for host in hosts:
        try:
            tstat = radiotherm.get_thermostat(host)
            tstats.append(RadioThermostat(tstat, hold_temp, away_delta))
        except (URLError, OSError):
            logger.exception(
                "Unable to connect to Radio Thermostat: %s", host)

    add_devices(tstats)


class RadioThermostat(ThermostatDevice):
    """ Represent a Radio Thermostat. """

    def __init__(self, device, hold_temp, away_delta):
        self.device = device
        self.set_time()
        self._target_temperature = None
        self._current_temperature = None
        self._operation = STATE_IDLE
        self._name = None
        self.hold_temp = hold_temp
        self.away = False
        self.away_delta = away_delta
        self.update()
        self.old_temp = self.target_temperature

    @property
    def name(self):
        """ Returns the name of the Radio Thermostat. """
        return self._name

    @property
    def unit_of_measurement(self):
        """ Unit of measurement this thermostat expresses itself in. """
        return TEMP_FAHRENHEIT

    @property
    def device_state_attributes(self):
        """ Returns device specific state attributes. """
        return {
            "fan": self.device.fmode['human'],
            "mode": self.device.tmode['human']
        }

    @property
    def current_temperature(self):
        """ Returns the current temperature. """
        return round(self._current_temperature, 1)

    @property
    def operation(self):
        """ Returns current operation. head, cool idle """
        return self._operation

    @property
    def target_temperature(self):
        """ Returns the temperature we try to reach. """

        return round(self._target_temperature, 1)

    @property
    def is_away_mode_on(self):
        """ Returns if away mode is on. """
        return self.away

    def turn_away_mode_on(self):
        """ Turns away on. """
        self.away = True
        self.old_temp = self.target_temperature
        if self._operation == STATE_COOL:
            self.set_temperature(self.old_temp + self.away_delta)
        if self._operation == STATE_HEAT:
            self.set_temperature(self.old_temp - self.away_delta)

    def turn_away_mode_off(self):
        """ Turns away off. """
        self.away = False
        self.set_temperature(self.old_temp)

    def update(self):
        self._current_temperature = self.device.temp['raw']
        self._name = self.device.name['raw']
        if self.device.tmode['human'] == 'Cool':
            self._target_temperature = self.device.t_cool['raw']
            self._operation = STATE_COOL
        elif self.device.tmode['human'] == 'Heat':
            self._target_temperature = self.device.t_heat['raw']
            self._operation = STATE_HEAT
        else:
            self._operation = STATE_IDLE

    def set_temperature(self, temperature):
        """ Set new target temperature """
        if self._operation == STATE_COOL:
            self.device.t_cool = temperature
        elif self._operation == STATE_HEAT:
            self.device.t_heat = temperature
        if self.hold_temp:
            self.device.hold = 1
        else:
            self.device.hold = 0

    def set_time(self):
        """ Set device time """
        now = datetime.datetime.now()
        self.device.time = {'day': now.weekday(),
                            'hour': now.hour, 'minute': now.minute}
