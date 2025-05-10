import logging
from homeassistant.components.input_select import InputSelect
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
        PiscinexaInputSelect(hass, entry, name, "ph_plus_treatment", ["Liquide", "Granulés"], "Liquide"),
        PiscinexaInputSelect(hass, entry, name, "ph_minus_treatment", ["Liquide", "Granulés"], "Liquide"),
        PiscinexaInputSelect(hass, entry, name, "chlore_treatment", ["Liquide", "Chlore choc (poudre)", "Pastille lente"], "Chlore choc (poudre)"),
    ]
    async_add_entities(entities, True)

class PiscinexaInputSelect(InputSelect):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, type_: str, options: list, default_option: str):
        super().__init__(options=options, initial_option=default_option, editable=True, icon="mdi:menu-down")
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
        self._translations = None

    async def async_added_to_hass(self):
        self._translations = await async_get_translations(
            self._hass,
            self._hass.config.language,
            "entity",
            integrations={DOMAIN},
        )
        self._attr_name = self._translations.get(
            f"entity.input_select.piscinexa_{self._type}.name",
            self._type.replace("_", " ").capitalize()
        )
        options_key = f"entity.input_select.piscinexa_{self._type}.options"
        translated_options = []
        for option in self._attr_options:
            option_key = f"{options_key}.{option.lower().replace(' ', '_')}"
            translated_option = self._translations.get(option_key, option)
            translated_options.append(translated_option)
        self._attr_options = translated_options
        _LOGGER.debug(f"Setting friendly_name for Input Select {self._type}: {self._attr_name}")
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
