import logging
import socket
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.light import PLATFORM_SCHEMA, SUPPORT_EFFECT, ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_RGB_COLOR, LightEntity, LightEntityFeature, ColorMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([GyverLampGunner(config)], True)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    entity = GyverLampGunner(entry.options, entry.entry_id)
    async_add_entities([entity], True)

    hass.data[DOMAIN][entry.entry_id] = entity

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

def getSocketData(address, request):
    BUFF_SIZE = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    sock.sendto(request.encode(), address)

    data = sock.recv(4096).decode('utf-8')
    _LOGGER.error(f"SEND: {request}, RECEIVED: {data}")

    sock.close()
    return data

def loadEffects(address):
    effects = []
    for i in range(1, 10):
        req = "LIST " + str(i)
        data = getSocketData(address, req)

        if data != None and ';' in data:
          data = data.split(';')
          for part in data:
            if part.find(u". ") > -1:
              tmp = part.split('. ')
              if len(tmp) > 1:
                tmp = tmp[1]
                if tmp.find(u",") > -1:
                  tmp = tmp.split(',')[0]
                  effects.append(tmp)

    return effects

def loadUdpParams(address):
    data = []

    data = getSocketData(address, "GET")
    if u"CURR" in data:
        data = data.split(' ')

    return data


class GyverLampGunner(LightEntity):
    _available = False
    _brightness = None
    _effect = None
    _effects = None
    _host = None
    _is_on = None
    _rgb_color = None

    def __init__(self, config: dict, unique_id=None):
        self._name = config.get(CONF_NAME, "Gyver Lamp")
        self._unique_id = config[CONF_HOST] + "_gvr_lmp"
        self.update_config(config)

    @property
    def should_poll(self):
        return True

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return self._name

    @property
    def brightness(self):
        return self._brightness

    @property
    def effect_list(self):
        return self._effects

    @property
    def effect(self):
        return self._effect

    @property
    def supported_features(self):
        return SUPPORT_EFFECT

    @property
    def supported_color_modes(self):
        return [ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.RGB]

    @property
    def is_on(self):
        return self._is_on

    @property
    def available(self):
        return self._available

    @property
    def rgb_color(self) -> tuple:
        return self._rgb_color

    @property
    def address(self) -> tuple:
        return self._host, 8888

    def debug(self, message):
        _LOGGER.error(f"{self._host} | {message}")

    def update_config(self, config: dict):
        self._host = config[CONF_HOST]
        self._effects = loadEffects(self.address)

        if self.hass:
            self._async_write_ha_state()

    def turn_on(self, **kwargs):
        payload = []

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            try:
                payload.append('EFF %d' % self._effects.index(effect))
            except ValueError:
                payload.append(effect)

        if ATTR_BRIGHTNESS in kwargs:
            payload.append('BRI %d' % kwargs[ATTR_BRIGHTNESS])

        if ATTR_RGB_COLOR in kwargs:
            speed = kwargs[ATTR_RGB_COLOR][0]
            payload.append('SPD%d' % speed)
            scale = kwargs[ATTR_RGB_COLOR][1]
            payload.append('SCA%d' % scale)

        if not self.is_on:
            payload.append('P_ON')

        self.debug(kwargs)
        self.debug(f"SEND {payload}")

        for data in payload:
            getSocketData(self.address, data)

    def turn_off(self, **kwargs):
        getSocketData(self.address, "P_OFF")

    def update(self):
        try:
            data = loadUdpParams(self.address)
            if len(data) >= 5:
                # bri eff spd sca pow
                i = int(data[1])
                self._effect = self._effects[i] if i < len(self._effects) else None
                self._brightness = int(data[2])
                self._rgb_color = (int(data[3]), int(data[4]), 0)
                self._is_on = data[5] == '1'
                self._available = True

        except Exception as e:
            self.debug(f"Can't update: {e}")
            self._available = False
