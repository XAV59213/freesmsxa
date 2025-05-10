import logging
from datetime import datetime, timedelta
from collections import deque
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import CONF_NAME
from homeassistant.helpers.event import async_track_state_change_event
from .const import (
    DOMAIN,
    POOL_TYPE_SQUARE,
    POOL_TYPE_ROUND,
    PI,
    UNIT_CUBIC_METERS,
    UNIT_HOURS,
    UNIT_LITERS,
    UNIT_GRAMS,
    UNIT_MG_PER_LITER,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    log_sensor = PiscinexaLogSensor(hass, entry)
    hass.data[DOMAIN]["log"] = log_sensor
    name = entry.data["name"]
    sensors = [
        PiscinexaVolumeSensor(hass, entry, name),
        PiscinexaTempsFiltrationRecommandeSensor(hass, entry, name),
        PiscinexaTempsFiltrationEffectueSensor(hass, entry, name),
        PiscinexaTemperatureSensor(hass, entry, name),
        PiscinexaPhSensor(hass, entry, name),
        PiscinexaPhPlusAjouterSensor(hass, entry, name),
        PiscinexaPhMinusAjouterSensor(hass, entry, name),
        PiscinexaPhTargetSensor(hass, entry, name),
        PiscinexaChloreSensor(hass, entry, name),
        PiscinexaChloreTargetSensor(hass, entry, name),
        PiscinexaChloreAjouterSensor(hass, entry, name),
        PiscinexaChloreDifferenceSensor(hass, entry, name),
        PiscinexaPowerSensor(hass, entry, name),
        PiscinexaPoolStateSensor(hass, entry, name),
        log_sensor,
    ]
    async_add_entities(sensors, True)

class PiscinexaVolumeSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_volume_eau"
        self._attr_friendly_name = f"{name.capitalize()} Volume d'eau"
        self._attr_unique_id = f"{entry.entry_id}_volume_eau"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:pool"
        self._attr_native_unit_of_measurement = UNIT_CUBIC_METERS

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            pool_type = self._entry.data["pool_type"]
            depth = float(self._entry.data["depth"])
            if pool_type == POOL_TYPE_SQUARE:
                length = float(self._entry.data["length"])
                width = float(self._entry.data["width"])
                volume = length * width * depth
            else:
                diameter = float(self._entry.data["diameter"])
                radius = diameter / 2
                volume = PI * radius * radius * depth
            return round(volume, 2)
        except Exception as e:
            _LOGGER.error("Erreur calcul volume pour %s: %s", self._name, e)
            return None

class PiscinexaTempsFiltrationRecommandeSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_tempsfiltration_recommande"
        self._attr_friendly_name = f"{name.capitalize()} Temps de filtration recommandé"
        self._attr_unique_id = f"{entry.entry_id}_temps_filtration_recommande"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:clock"
        self._attr_native_unit_of_measurement = UNIT_HOURS
        self._subscriptions = []
        sensor_id = self._entry.data.get("temperature_sensor")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_sensor
                )
            )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensor(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        sensor_id = self._entry.data.get("temperature_sensor")
        if sensor_id:
            state = self._hass.states.get(sensor_id)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    return round(float(state.state) / 2, 1)
                except Exception as e:
                    _LOGGER.warning("Erreur de conversion température depuis %s : %s", sensor_id, e)
        try:
            return round(self._entry.data["temperature"] / 2, 1)
        except Exception as e:
            _LOGGER.error("Température par défaut invalide : %s", e)
            return None

class PiscinexaTempsFiltrationEffectueSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_tempsfiltration_effectue"
        self._attr_friendly_name = f"{name.capitalize()} Temps de filtration effectué"
        self._attr_unique_id = f"{entry.entry_id}_temps_filtration_effectue"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:clock-check"
        self._attr_native_unit_of_measurement = UNIT_HOURS
        self._subscriptions = []
        self._filtration_time = 0.0
        self._last_active_time = None
        sensor_id = self._entry.data.get("power_sensor_entity_id")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_power_sensor
                )
            )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_power_sensor(self, event):
        sensor_id = self._entry.data.get("power_sensor_entity_id")
        state = self._hass.states.get(sensor_id)
        current_time = datetime.now()

        if state and state.state not in ("unknown", "unavailable"):
            try:
                power = float(state.state)
                if power > 10:
                    if self._last_active_time is not None:
                        time_diff = (current_time - self._last_active_time).total_seconds() / 3600
                        self._filtration_time += time_diff
                    self._last_active_time = current_time
                else:
                    self._last_active_time = None
            except ValueError as e:
                _LOGGER.warning("Valeur non numérique pour capteur de puissance %s: %s", sensor_id, e)
        else:
            self._last_active_time = None

        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            return round(self._filtration_time, 1)
        except Exception as e:
            _LOGGER.error("Erreur lecture temps de filtration effectué: %s", e)
            return None

    @property
    def extra_state_attributes(self):
        attributes = {}
        try:
            attributes["last_active_time"] = (
                self._last_active_time.isoformat() if self._last_active_time else None
            )
            attributes["power_sensor"] = self._entry.data.get("power_sensor_entity_id", "N/A")
        except Exception as e:
            _LOGGER.error("Erreur récupération attributs temps filtration effectué: %s", e)
        return attributes

class PiscinexaTemperatureSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_temperature"
        self._attr_friendly_name = f"{name.capitalize()} Température"
        self._attr_unique_id = f"{entry.entry_id}_temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:thermometer"
        self._attr_native_unit_of_measurement = "°C"
        self._subscriptions = []
        sensor_id = self._entry.data.get("temperature_sensor")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_sensor
                )
            )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensor(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        sensor_id = self._entry.data.get("temperature_sensor")
        if sensor_id:
            state = self._hass.states.get(sensor_id)
            if state:
                if state.state in ("unknown", "unavailable"):
                    _LOGGER.warning("Capteur de température %s indisponible", sensor_id)
                    return None
                try:
                    value = float(state.state)
                    unit = state.attributes.get("unit_of_measurement", "").lower()
                    if unit in ("°f", "f", "fahrenheit"):
                        value = (value - 32) * 5 / 9
                    value = round(value, 1)
                    self._hass.data[DOMAIN][self._entry.entry_id]["temperature"] = value
                    return value
                except ValueError as e:
                    _LOGGER.error("Valeur non numérique pour capteur %s: %s", sensor_id, state.state)
                    return None
        try:
            return round(float(self._entry.data["temperature"]), 1)
        except Exception as e:
            _LOGGER.error("Température par défaut invalide : %s", e)
            return None

class PiscinexaPhSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._entry = entry
        self._name = name
        self._hass = hass
        self._attr_name = f"{DOMAIN}_{name}_ph"
        self._attr_friendly_name = f"{name.capitalize()} pH Actuel"
        self._attr_unique_id = f"{entry.entry_id}_ph"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:water"
        self._attr_native_unit_of_measurement = UNIT_MG_PER_LITER
        self._subscriptions = []
        sensor_id = self._entry.data.get("ph_sensor")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_sensor
                )
            )
        input_id = f"input_number.{name}_ph_current"
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [input_id], self._async_update_from_input
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensor(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_input(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        sensor_id = self._entry.data.get("ph_sensor")
        if sensor_id:
            state = self._hass.states.get(sensor_id)
            if state:
                if state.state in ("unknown", "unavailable"):
                    _LOGGER.warning("Capteur de pH %s indisponible", sensor_id)
                    return None
                try:
                    value = round(float(state.state), 1)
                    self._hass.data[DOMAIN][self._entry.entry_id]["ph_current"] = value
                    self._hass.states.async_set(
                        f"input_number.{self._name}_ph_current",
                        value,
                        {
                            "friendly_name": f"{self._name.capitalize()} pH Actuel",
                            "min": 0,
                            "max": 14,
                            "step": 0.1,
                            "unit_of_measurement": UNIT_MG_PER_LITER,
                        },
                    )
                    return value
                except ValueError as e:
                    _LOGGER.error("Valeur non numérique pour capteur %s: %s", sensor_id, state.state)
                    return None
        input_state = self._hass.states.get(f"input_number.{self._name}_ph_current")
        if input_state and input_state.state not in ("unknown", "unavailable"):
            try:
                value = round(float(input_state.state), 1)
                self._hass.data[DOMAIN][self._entry.entry_id]["ph_current"] = value
                return value
            except Exception as e:
                _LOGGER.warning("Erreur lecture pH depuis input_number : %s", e)
        try:
            return round(float(self._entry.data["ph_current"]), 1)
        except Exception as e:
            _LOGGER.error("Erreur lecture pH: %s", e)
            return None

class PiscinexaPhPlusAjouterSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_ph_plus_ajouter"
        self._attr_friendly_name = f"{name.capitalize()} pH+ à ajouter"
        self._attr_unique_id = f"{entry.entry_id}_ph_plus_ajouter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:bottle-tonic-plus"
        self._subscriptions = []
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_ph"], self._async_update_from_ph
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_volume_eau"], self._async_update_from_volume
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"input_select.{name}_ph_plus_treatment"], self._async_update_from_select
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_ph(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_volume(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_select(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_unit_of_measurement(self):
        try:
            select_state = self._hass.states.get(f"input_select.{self._name}_ph_plus_treatment")
            if select_state and select_state.state == "Liquide":
                return UNIT_LITERS
            return UNIT_GRAMS
        except Exception as e:
            _LOGGER.error("Erreur détermination unité pH+: %s", e)
            return UNIT_LITERS

    @property
    def native_value(self):
        try:
            ph_current = float(self._entry.data["ph_current"])
            ph_target = float(self._entry.data["ph_target"])
            if ph_current >= ph_target:
                return 0
            volume = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume and volume.state not in ("unknown", "unavailable"):
                volume_val = float(volume.state)
                ph_difference = ph_target - ph_current
                select_state = self._hass.states.get(f"input_select.{self._name}_ph_plus_treatment")
                treatment = select_state.state if select_state else "Liquide"
                if treatment == "Liquide":
                    dose = ph_difference * volume_val * 0.01
                else:
                    dose = ph_difference * volume_val * 1.0
                return round(dose, 2)
            return None
        except Exception as e:
            _LOGGER.error("Erreur calcul dose pH+ pour %s: %s", self._name, e)
            return None

    @property
    def extra_state_attributes(self):
        attributes = {}
        try:
            ph_current = float(self._entry.data["ph_current"])
            ph_target = float(self._entry.data["ph_target"])
            volume = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume:
                attributes["volume"] = float(volume.state)
            attributes["ph_current"] = ph_current
            attributes["ph_target"] = ph_target
        except Exception as e:
            _LOGGER.error("Erreur récupération attributs pH+: %s", e)
        return attributes

class PiscinexaPhMinusAjouterSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_ph_minus_ajouter"
        self._attr_friendly_name = f"{name.capitalize()} pH- à ajouter"
        self._attr_unique_id = f"{entry.entry_id}_ph_minus_ajouter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:water-minus"
        self._subscriptions = []
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_ph"], self._async_update_from_ph
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_volume_eau"], self._async_update_from_volume
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"input_select.{name}_ph_minus_treatment"], self._async_update_from_select
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_ph(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_volume(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_select(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_unit_of_measurement(self):
        try:
            select_state = self._hass.states.get(f"input_select.{self._name}_ph_minus_treatment")
            if select_state and select_state.state == "Liquide":
                return UNIT_LITERS
            return UNIT_GRAMS
        except Exception as e:
            _LOGGER.error("Erreur détermination unité pH-: %s", e)
            return UNIT_LITERS

    @property
    def native_value(self):
        try:
            ph_current = float(self._entry.data["ph_current"])
            ph_target = float(self._entry.data["ph_target"])
            if ph_current <= ph_target:
                return 0
            volume = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume and volume.state not in ("unknown", "unavailable"):
                volume_val = float(volume.state)
                ph_difference = ph_current - ph_target
                select_state = self._hass.states.get(f"input_select.{self._name}_ph_minus_treatment")
                treatment = select_state.state if select_state else "Liquide"
                if treatment == "Liquide":
                    dose = ph_difference * volume_val * 0.012
                else:
                    dose = ph_difference * volume_val * 1.2
                return round(dose, 2)
            return None
        except Exception as e:
            _LOGGER.error("Erreur calcul dose pH- pour %s: %s", self._name, e)
            return None

    @property
    def extra_state_attributes(self):
        attributes = {}
        try:
            ph_current = float(self._entry.data["ph_current"])
            ph_target = float(self._entry.data["ph_target"])
            volume = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume:
                attributes["volume"] = float(volume.state)
            attributes["ph_current"] = ph_current
            attributes["ph_target"] = ph_target
        except Exception as e:
            _LOGGER.error("Erreur récupération attributs pH-: %s", e)
        return attributes

class PiscinexaPhTargetSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._entry = entry
        self._name = name
        self._hass = hass
        self._attr_name = f"{DOMAIN}_{name}_ph_target"
        self._attr_friendly_name = f"{name.capitalize()} pH Cible"
        self._attr_unique_id = f"{entry.entry_id}_ph_target"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:target"
        self._attr_native_unit_of_measurement = UNIT_MG_PER_LITER
        self._subscriptions = []
        input_id = f"input_number.{name}_ph_target"
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [input_id], self._async_update_from_input
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_input(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            return round(float(self._entry.data["ph_target"]), 1)
        except Exception as e:
            _LOGGER.error("Erreur lecture pH cible: %s", e)
            return None

class PiscinexaChloreSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._entry = entry
        self._name = name
        self._hass = hass
        self._attr_name = f"{DOMAIN}_{name}_chlore"
        self._attr_friendly_name = f"{name.capitalize()} Chlore Actuel"
        self._attr_unique_id = f"{entry.entry_id}_chlore"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:water-check"
        self._attr_native_unit_of_measurement = UNIT_MG_PER_LITER
        self._subscriptions = []
        sensor_id = self._entry.data.get("chlore_sensor")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_sensor
                )
            )
        input_id = f"input_number.{name}_chlore_current"
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [input_id], self._async_update_from_input
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensor(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_input(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        sensor_id = self._entry.data.get("chlore_sensor")
        if sensor_id:
            state = self._hass.states.get(sensor_id)
            if state and state.state not in ("unknown", "unavailable"):
                try:
                    value = round(float(state.state), 1)
                    self._hass.data[DOMAIN][self._entry.entry_id]["chlore_current"] = value
                    self._hass.states.async_set(
                        f"input_number.{self._name}_chlore_current",
                        value,
                        {
                            "friendly_name": f"{self._name.capitalize()} Chlore Actuel",
                            "min": 0,
                            "max": 10,
                            "step": 0.1,
                            "unit_of_measurement": UNIT_MG_PER_LITER,
                        },
                    )
                    return value
                except Exception as e:
                    _LOGGER.warning("Erreur lecture chlore depuis capteur %s : %s", sensor_id, e)
        input_state = self._hass.states.get(f"input_number.{self._name}_chlore_current")
        if input_state and input_state.state not in ("unknown", "unavailable"):
            try:
                value = round(float(input_state.state), 1)
                self._hass.data[DOMAIN][self._entry.entry_id]["chlore_current"] = value
                return value
            except Exception as e:
                _LOGGER.warning("Erreur lecture chlore depuis input_number : %s", e)
        try:
            return round(float(self._entry.data["chlore_current"]), 1)
        except Exception as e:
            _LOGGER.error("Erreur lecture chlore: %s", e)
            return None

class PiscinexaChloreTargetSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._entry = entry
        self._name = name
        self._hass = hass
        self._attr_name = f"{DOMAIN}_{name}_chlore_target"
        self._attr_friendly_name = f"{name.capitalize()} Chlore Cible"
        self._attr_unique_id = f"{entry.entry_id}_chlore_target"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:target"
        self._attr_native_unit_of_measurement = UNIT_MG_PER_LITER
        self._subscriptions = []
        input_id = f"input_number.{name}_chlore_target"
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [input_id], self._async_update_from_input
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_input(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            return round(float(self._entry.data["chlore_target"]), 1)
        except Exception as e:
            _LOGGER.error("Erreur lecture chlore cible: %s", e)
            return None

class PiscinexaChloreAjouterSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_chloreaajouter"
        self._attr_friendly_name = f"{name.capitalize()} Chlore à Ajouter"
        self._attr_unique_id = f"{entry.entry_id}_chlore_a_ajouter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:bottle-tonic-plus"
        self._message = None
        self._subscriptions = []
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_chlore"], self._async_update_from_chlore
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_volume_eau"], self._async_update_from_volume
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_temperature"], self._async_update_from_temperature
            )
        )
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"input_select.{name}_chlore_treatment"], self._async_update_from_select
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_chlore(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_volume(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_temperature(self, event):
        self.async_schedule_update_ha_state(True)

    @callback
    def _async_update_from_select(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_unit_of_measurement(self):
        select_state = self._hass.states.get(f"input_select.{self._name}_chlore_treatment")
        if select_state:
            if select_state.state == "Liquide":
                return UNIT_LITERS
            elif select_state.state == "Pastille lente":
                return "unités"
            return UNIT_GRAMS
        return UNIT_GRAMS

    @property
    def native_value(self):
        try:
            chlore_current = float(self._entry.data["chlore_current"])
            chlore_target = float(self._entry.data["chlore_target"])
            volume_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume_entity and volume_entity.state not in ("unknown", "unavailable"):
                volume_val = float(volume_entity.state)
                temp_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_temperature")
                if temp_entity and temp_entity.state not in ("unknown", "unavailable"):
                    temperature = float(temp_entity.state)
                    temp_factor = max(1, 1 + (temperature - 20) * 0.02)
                    chlore_difference = chlore_target - chlore_current
                    select_state = self._hass.states.get(f"input_select.{self._name}_chlore_treatment")
                    treatment = select_state.state if select_state else "Chlore choc (poudre)"
                    if treatment == "Liquide":
                        dose = chlore_difference * volume_val * 0.1 * temp_factor
                    elif treatment == "Pastille lente":
                        dose = (chlore_difference * volume_val / 20) * temp_factor
                    else:
                        dose = chlore_difference * volume_val * 0.01 * temp_factor
                    if dose <= 0:
                        self._message = "Retirer le chlore, pas de besoin actuellement"
                        return 0
                    self._message = None
                    return round(dose, 2)
                self._message = "Température indisponible"
                return None
            self._message = "Volume indisponible"
            return None
        except Exception as e:
            _LOGGER.error("Erreur calcul dose chlore pour %s: %s", self._name, e)
            self._message = "Erreur de calcul"
            return None

    @property
    def extra_state_attributes(self):
        attributes = {}
        try:
            attributes["chlore_current"] = float(self._entry.data["chlore_current"])
            attributes["chlore_target"] = float(self._entry.data["chlore_target"])
            volume_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_volume_eau")
            if volume_entity:
                attributes["volume"] = float(volume_entity.state)
            temp_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_temperature")
            if temp_entity:
                attributes["temperature"] = float(temp_entity.state)
                attributes["temp_factor"] = max(1, 1 + (attributes["temperature"] - 20) * 0.02)
            if self._message:
                attributes["message"] = self._message
        except Exception as e:
            _LOGGER.error("Erreur récupération attributs supplémentaires: %s", e)
        return attributes

class PiscinexaChloreDifferenceSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_chloredifference"
        self._attr_friendly_name = f"{name.capitalize()} Chlore Différence"
        self._attr_unique_id = f"{entry.entry_id}_chlore_difference"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:delta"
        self._attr_native_unit_of_measurement = UNIT_MG_PER_LITER
        self._subscriptions = []
        self._subscriptions.append(
            async_track_state_change_event(
                hass, [f"sensor.{DOMAIN}_{name}_chlore"], self._async_update_from_chlore
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_chlore(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            chlore_current = float(self._entry.data["chlore_current"])
            chlore_target = float(self._entry.data["chlore_target"])
            difference = chlore_target - chlore_current
            return round(difference, 1)
        except Exception as e:
            _LOGGER.error("Erreur calcul différence chlore pour %s: %s", self._name, e)
            return None

class PiscinexaLogSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self._hass = hass
        self._entry = entry
        self._name = entry.data["name"]
        self._attr_name = f"{DOMAIN}_{self._name}_log"
        self._attr_friendly_name = f"{self._name.capitalize()} Journal"
        self._attr_unique_id = f"{entry.entry_id}_log"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{self._name}")},
            name=self._name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:book"
        self._attr_native_unit_of_measurement = None
        self._state = deque(maxlen=10)

    @property
    def name(self):
        return self._attr_friendly_name

    def log_action(self, action: str):
        self._state.append(f"{datetime.now()}: {action}")
        self.async_write_ha_state()

    @property
    def native_value(self):
        return "\n".join(self._state) if self._state else "Aucune action"

class PiscinexaPowerSensor(SensorEntity):
    def __init__(self, hass, entry, name):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_consopuissance"
        self._attr_friendly_name = f"{name.capitalize()} Consommation puissance"
        self._attr_unique_id = f"{entry.entry_id}_conso_puissance"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:flash"
        self._attr_native_unit_of_measurement = "W"
        self._subscriptions = []
        sensor_id = self._entry.data.get("power_sensor_entity_id")
        if sensor_id:
            self._subscriptions.append(
                async_track_state_change_event(
                    hass, [sensor_id], self._async_update_from_sensor
                )
            )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensor(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            sensor_id = self._entry.data.get("power_sensor_entity_id")
            if sensor_id:
                power_state = self._hass.states.get(sensor_id)
                if power_state and power_state.state not in ("unknown", "unavailable"):
                    value = round(float(power_state.state), 2)
                    log = self._hass.data[DOMAIN].get("log")
                    if log:
                        log.log_action(f"Conso {self._name} : {value} W")
                    return value
        except Exception as e:
            _LOGGER.warning("Erreur lecture capteur puissance : %s", e)
        return None

class PiscinexaPoolStateSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, name: str):
        self._hass = hass
        self._entry = entry
        self._name = name
        self._attr_name = f"{DOMAIN}_{name}_pool_state"
        self._attr_friendly_name = f"{name.capitalize()} État de la piscine"
        self._attr_unique_id = f"{entry.entry_id}_pool_state"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"piscinexa_{name}")},
            name=name.capitalize(),
            manufacturer="Piscinexa",
            model="Piscine",
            sw_version="1.0.2",
        )
        self._attr_icon = "mdi:pool"
        self._attr_native_unit_of_measurement = None
        self._subscriptions = []
        entities_to_track = [
            f"sensor.{DOMAIN}_{name}_temperature",
            f"sensor.{DOMAIN}_{name}_chlore",
            f"sensor.{DOMAIN}_{name}_ph",
            f"sensor.{DOMAIN}_{name}_tempsfiltration_recommande",
        ]
        self._subscriptions.append(
            async_track_state_change_event(
                hass, entities_to_track, self._async_update_from_sensors
            )
        )

    async def async_will_remove_from_hass(self):
        for subscription in self._subscriptions:
            subscription()
        self._subscriptions.clear()

    @callback
    def _async_update_from_sensors(self, event):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._attr_friendly_name

    @property
    def native_value(self):
        try:
            issues = []
            temp_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_temperature")
            if temp_entity and temp_entity.state not in ("unknown", "unavailable"):
                temperature = float(temp_entity.state)
                if temperature < 22:
                    issues.append("Température trop froide")
                elif temperature > 28:
                    issues.append("Température trop chaude")
                else:
                    issues.append("Température idéale")
            else:
                issues.append("Température indisponible")
            chlore_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_chlore")
            if chlore_entity and chlore_entity.state not in ("unknown", "unavailable"):
                chlore = float(chlore_entity.state)
                if chlore < 1:
                    issues.append("Chlore trop bas")
                elif chlore > 3:
                    issues.append("Chlore trop élevé")
                else:
                    issues.append("Chlore idéal")
            else:
                issues.append("Chlore indisponible")
            ph_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_ph")
            if ph_entity and ph_entity.state not in ("unknown", "unavailable"):
                ph = float(ph_entity.state)
                if ph < 7.2:
                    issues.append("pH trop bas")
                elif ph > 7.6:
                    issues.append("pH trop élevé")
                else:
                    issues.append("pH idéal")
            else:
                issues.append("pH indisponible")
            filtration_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_tempsfiltration_recommande")
            if filtration_entity and filtration_entity.state not in ("unknown", "unavailable") and temp_entity:
                filtration_time = float(filtration_entity.state)
                required_filtration = temperature / 2
                if filtration_time < required_filtration:
                    issues.append("Temps de filtration insuffisant")
                else:
                    issues.append("Temps de filtration idéal")
            else:
                issues.append("Temps de filtration indisponible")
            if all(issue in ["Température idéale", "Chlore idéal", "pH idéal", "Temps de filtration idéal"] for issue in issues):
                return "Baignade autorisée, profitez-en !"
            else:
                return ", ".join(issues)
        except Exception as e:
            _LOGGER.error("Erreur calcul état piscine pour %s: %s", self._name, e)
            return "Erreur d'évaluation"

    @property
    def extra_state_attributes(self):
        attributes = {}
        try:
            temp_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_temperature")
            if temp_entity:
                attributes["temperature"] = float(temp_entity.state)
            chlore_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_chlore")
            if chlore_entity:
                attributes["chlore"] = float(chlore_entity.state)
            ph_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_ph")
            if ph_entity:
                attributes["ph"] = float(ph_entity.state)
            filtration_entity = self._hass.states.get(f"sensor.{DOMAIN}_{self._name}_tempsfiltration_recommande")
            if filtration_entity:
                attributes["temps_filtration_recommande"] = float(filtration_entity.state)
        except Exception as e:
            _LOGGER.error("Erreur récupération attributs état piscine: %s", e)
        return attributes
