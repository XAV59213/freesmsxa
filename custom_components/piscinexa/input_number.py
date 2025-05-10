import logging
from homeassistant.components.input_number import InputNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    name = entry.data["name"]
    entities = [
        PiscinexaInputNumber(hass, entry, name, "ph_current", 0, 14, 7.0),
        PiscinexaInputNumber(hass, entry, name, "chlore_current", 0, 10, 1.0),
    ]
    async_add_entities(entities, True)

class PiscinexaInputNumber(InputNumber):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, type_: str, min_val: float, max_val: float, default_val: float):
        super().__init__(min_val, max_val, default_val, step=0.1, icon="mdi:numeric")
        self._hass = hass
        self._entry = entry
        self._name = name
        self._type = type_
        self._attr_unique_id = f"{entry.entry_id}_{type_}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_value = default_val
        self._translations = None

    async def async_added_to_hass(self):
        self._translations = await async_get_translations(
            self._hass,
            self._hass.config.language,
            "entity",
            integrations={DOMAIN},
        )
        self._attr_name = self._translations.get(
            f"entity.input_number.piscinexa_{self._type}.name",
            self._type.replace("_", " ").capitalize()
        )
        _LOGGER.debug(f"Setting friendly_name for Input Number {self._type}: {self._attr_name}")
        self.async_write_ha_state()

    async def async_set_value(self, value: float) -> None:
        self._attr_value = value
        self.async_write_ha_state()
        await self._hass.config_entries.async_reload(self._entry.entry_id)
