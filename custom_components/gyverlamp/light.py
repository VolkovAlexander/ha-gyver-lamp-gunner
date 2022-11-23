import logging
import socket

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.light import PLATFORM_SCHEMA, LightEntity, \
    SUPPORT_BRIGHTNESS, SUPPORT_EFFECT, SUPPORT_COLOR, SUPPORT_COLOR_TEMP, \
    ATTR_BRIGHTNESS, ATTR_EFFECT, ATTR_HS_COLOR, ATTR_COLOR_TEMP
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_EFFECTS = 'effects'

EFFECTS = ["Бeлый cвeт", "Цвeт", "Cмeнa цвeтa", "Бeзyмиe", "Oблaкa",
          	   "Лaвa", "Плaзмa", "Paдyгa 3D", "Пaвлин", "3eбpa", "Лec", "Oкeaн",
          	   "Mячики", "Mячики бeз гpaниц", "Пoпкopн",
          	   "Cпиpaли", "Пpизмaтa", "Дымовые шашки", "Тихий океан", "Тени", "ДHK", "Cтaя", "Cтaя и xищник",
          	   "Moтыльки", "Лaмпa c мoтылькaми", "3мeйки", "Nexus", "Шары", "Cинycoид", "Meтaбoлз", "Северное сияние",
          	   "Плазменная лампа", "Лaвoвaя лaмпa", "Жидкaя лaмпa", "Жидкaя лaмпa (auto)", "Капли на стекле", "Maтpицa",
          	   "Oгoнь 2012", "Oгoнь 2018", "Oгoнь 2020", "Oгoнь", "Bиxpи плaмeни", "Paзнoцвeтныe виxpи",
          	   "Магма", "Кипение", "Boдoпaд", "Boдoпaд 4 в 1", "Бacceйн", "Пyльc", "Paдyжный пyльc",
          	   "Бeлый пyльc", "Ocциллятop", "Источник", "Фея",
          	   "Koмeтa", "Oднoцвeтнaя кoмeтa", "Двe кoмeты",
          	   "Тpи кoмeты", "Притяжение", "Пapящий oгoнь", "Bepxoвoй oгoнь", "Paдyжный змeй",
          	   "Koнфeтти", "Mepцaниe", "Дым", "Paзнoцвeтный дым", "Пикacco",
          	   "Пикacco 2", "Kpyги Пикacco", "Boлны", "Цветные драже", "Koдoвый зaмoк", "Kyбик Pyбикa",
          	   "Tyчкa в бaнкe", "Гроза в банке", "Ocaдки", "Paзнoцвeтный дoждь",
          	   "Cнeгoпaд", "Meтeль", "Пpыгyны", "Cвeтлячки",
          	   "Cвeтлячки co шлeйфoм", "Пeйнтбoл", "Paдyгa", "Чacы", "Бeгyщaя cтpoкa"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_EFFECTS): cv.ensure_list
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([GyverLamp(config)], True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities):
    entity = GyverLamp(entry.options, entry.entry_id)
    async_add_entities([entity], True)

    hass.data[DOMAIN][entry.entry_id] = entity


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


class GyverLamp(LightEntity):
    _available = False
    _brightness = None
    _effect = None
    _effects = None
    _host = None
    _color_temp = None
    _is_on = None

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
    def color_temp(self):
        return self._color_temp

    @property
    def effect_list(self):
        return self._effects

    @property
    def effect(self):
        return self._effect

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_EFFECT | SUPPORT_COLOR_TEMP

    @property
    def is_on(self):
        return self._is_on

    @property
    def available(self):
        return self._available

    @property
    def max_mireds(self):
        return 255

    @property
    def min_mireds(self):
        return 1

    @property
    def device_info(self):
        """
        https://developers.home-assistant.io/docs/device_registry_index/
        """
        return {
            'identifiers': {(DOMAIN, self._unique_id)},
            'manufacturer': "@AlexGyver",
            'model': "GyverLamp"
        }

    @property
    def address(self) -> tuple:
        return self._host, 8888

    def debug(self, message):
        _LOGGER.error(f"{self._host} | {message}")

    def update_config(self, config: dict):
        self._effects = config.get(CONF_EFFECTS, EFFECTS)
        self._host = config[CONF_HOST]

        if self.hass:
            self._async_write_ha_state()

    def turn_on(self, **kwargs):
        payload = []
        if ATTR_BRIGHTNESS in kwargs:
            payload.append('BRI%d' % kwargs[ATTR_BRIGHTNESS])

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            try:
                payload.append('EFF%d' % self._effects.index(effect))
            except ValueError:
                payload.append(effect)

        if ATTR_COLOR_TEMP in kwargs:
            payload.append('SPD%d' % kwargs[ATTR_COLOR_TEMP])

        if not self.is_on:
            payload.append('P_ON')

        self.debug(f"SEND {payload}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)

        for data in payload:
            sock.sendto(data.encode(), self.address)

        sock.close()

    def turn_off(self, **kwargs):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(b'P_OFF', self.address)
        sock.close()

    def update(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)

            effects = []
            for i in range(1, 5):
                req = "LIST " + str(i)
                sock.sendto(req.encode(), self.address)
                data = sock.recv(2048).decode()
                self.debug(data)
                if data != None and ';' in data:
                    data = data.split(';')
                    for part in data:
                        if '. ' in data:
                            tmp = part.split('. ')[1]
                            tmp = tmp.split(',')[0]
                            effects.append(tmp)

            self._effects = effects

            sock.sendto(b'GET', self.address)
            data = sock.recv(1024).decode().split(' ')
            self.debug(f"UPDATE {data}")
            # bri eff spd sca pow
            i = int(data[1])
            self._effect = self._effects[i] if i < len(self._effects) else None
            self._brightness = int(data[2])
            self._color_temp = int(data[3])
            self._is_on = data[5] == '1'
            self._available = True
            sock.close()

        except Exception as e:
            self.debug(f"Can't update: {e}")
            self._available = False
