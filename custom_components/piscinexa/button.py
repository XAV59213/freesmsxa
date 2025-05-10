import logging
from homeassistant.components.button import ButtonEntity
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
        PiscinexaButton(hass, entry, name, "test"),
        PiscinexaButton(hass, entry, name, "reset"),
    ]
    async_add_entities(entities, True)

class PiscinexaButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str, action: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._action = action
        self._attr_unique_id = f"{entry.entry_id}_{action}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:cog"
        self._attr_name = "Tester" if action == "test" else "Réinitialiser"
        self._translations = None

    async def async_added_to_hass(self):
        self._translations = await async_get_translations(
            self._hass,
            self._hass.config.language,
            "entity",
            integrations={DOMAIN},
        )
        translation_key = f"entity.button.piscinexa_{self._action}.name"
        default_name = "Tester" if self._action == "test" else "Réinitialiser"
        if self._hass.config.language != "fr":
            default_name = "Test" if self._action == "test" else "Reset"
        
        self._attr_name = self._translations.get(translation_key, default_name)
        
        if self._attr_name.lower() == self._name.lower():
            _LOGGER.warning(
                f"Nom du bouton {self._action} incorrect ({self._attr_name}), "
                f"utilisation de la valeur par défaut : {default_name}"
            )
            self._attr_name = default_name
            
        _LOGGER.debug(
            f"Configuration du friendly_name pour le bouton {self._action}: "
            f"{self._attr_name} (clé de traduction : {translation_key})"
        )
        self.async_write_ha_state()

    async def async_press(self):
        service_name = f"{self._action}_calcul" if self._action == "test" else f"{self._action}_valeurs"
        await self._hass.services.async_call(
            DOMAIN,
            service_name,
            {"name": self._name},
        )
