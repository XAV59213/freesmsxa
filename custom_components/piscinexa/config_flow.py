"""Flux de configuration pour Piscinexa."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN, POOL_TYPE_SQUARE, POOL_TYPE_ROUND

_LOGGER = logging.getLogger(__name__)

class PiscinexaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration pour Piscinexa."""
    VERSION = 1

    def __init__(self):
        self._data = {}
        self._ph_config_choice = None
        self._chlore_config_choice = None
        self._temperature_config_choice = None
        self._power_config_choice = None
        self._no_sensor_message = False
        self._translations = None

    async def async_step_user(self, user_input=None):
        """Step 1 : demander le nom et le type de piscine."""
        # Charger les traductions
        if not self._translations:
            self._translations = await async_get_translations(
                self.hass,
                self.hass.config.language,
                "config",
            )

        def get_translation(key: str, default: str = None) -> str:
            """Récupère une traduction avec une valeur par défaut."""
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            try:
                name = user_input["name"].strip().lower().replace(" ", "_")
                for entry in self._async_current_entries():
                    if entry.data.get("name") == name:
                        errors["name"] = "name_duplicate"
                        break
                if not name:
                    errors["name"] = "name_invalid"
                if not errors:
                    self._data["name"] = name
                    self._data["pool_type"] = user_input["pool_type"]
                    return await self.async_step_dimensions()
            except Exception as e:
                errors["base"] = f"unexpected_error: {str(e)}"

        # Traduire explicitement les options pour vol.In
        pool_type_options = {
            POOL_TYPE_SQUARE: get_translation("config.step.user.data.pool_type_square", default="Carrée"),
            POOL_TYPE_ROUND: get_translation("config.step.user.data.pool_type_round", default="Ronde"),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", default="piscine"): str,
                vol.Required("pool_type", default=POOL_TYPE_SQUARE): vol.In(pool_type_options),
            }),
            errors=errors,
        )

    async def async_step_dimensions(self, user_input=None):
        """Step 2 : demander les dimensions en fonction du type de piscine."""
        errors = {}
        pool_type = self._data["pool_type"]

        if user_input is not None:
            dimension_fields = []
            if pool_type == POOL_TYPE_SQUARE:
                dimension_fields = [
                    ("length", "dimensions_invalid", lambda x: x > 0),
                    ("width", "dimensions_invalid", lambda x: x > 0),
                    ("depth", "dimensions_invalid", lambda x: x > 0),
                ]
            else:
                dimension_fields = [
                    ("diameter", "dimensions_invalid", lambda x: x > 0),
                    ("depth", "dimensions_invalid", lambda x: x > 0),
                ]

            for field, error_key, validator in dimension_fields:
                try:
                    value = user_input.get(field)
                    if value is None or value == "":
                        errors[field] = "required_field"
                        continue
                    value = str(value).replace(",", ".").strip()
                    value = float(value)
                    if not validator(value):
                        errors[field] = error_key
                    self._data[field] = value
                except ValueError:
                    errors[field] = "invalid_number"

            if not errors:
                return await self.async_step_ph_config()

        schema = {}
        if pool_type == POOL_TYPE_SQUARE:
            schema.update({
                vol.Required("length", default=5.0): vol.Coerce(float),
                vol.Required("width", default=4.0): vol.Coerce(float),
                vol.Required("depth", default=1.5): vol.Coerce(float),
            })
        else:
            schema.update({
                vol.Required("diameter", default=4.0): vol.Coerce(float),
                vol.Required("depth", default=1.5): vol.Coerce(float),
            })

        return self.async_show_form(
            step_id="dimensions",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_ph_config(self, user_input=None):
        """Step 3 : configuration du pH (choix entre manuel et capteur)."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "ph_config_choice" in user_input:
                self._ph_config_choice = user_input["ph_config_choice"]
                if self._ph_config_choice == "manual":
                    self._no_sensor_message = False
                    return await self.async_step_ph_manual()
                else:
                    self._no_sensor_message = False
                    return await self.async_step_ph_sensor()
            else:
                errors["ph_config_choice"] = "required_field"

        ph_config_options = {
            "manual": get_translation("config.step.ph_config.data.manual", default="Saisie manuelle"),
            "sensor": get_translation("config.step.ph_config.data.sensor", default="Sélectionner un capteur"),
        }

        return self.async_show_form(
            step_id="ph_config",
            data_schema=vol.Schema({
                vol.Required("ph_config_choice"): vol.In(ph_config_options),
            }),
            errors=errors,
        )

    async def async_step_ph_manual(self, user_input=None):
        """Step 3 (sous-étape) : saisie manuelle des valeurs pH."""
        errors = {}
        if user_input is not None:
            numeric_fields = [
                ("ph_current", "ph_invalid", lambda x: 0 <= x <= 14, False),
                ("ph_target", "ph_invalid", lambda x: 0 <= x <= 14, True),
            ]
            for field, error_key, validator, required in numeric_fields:
                try:
                    value = user_input.get(field, "" if required else "7.0")
                    if required and (value is None or value == ""):
                        errors[field] = "required_field"
                        continue
                    if value is not None and value != "":
                        value = str(value).replace(",", ".").strip()
                        value = float(value)
                        if not validator(value):
                            errors[field] = error_key
                        self._data[field] = value
                except ValueError:
                    errors[field] = "invalid_number"

            if not errors:
                if "ph_current" not in self._data or self._data["ph_current"] is None:
                    self._data["ph_current"] = 7.0
                self._data["use_ph_sensor"] = False
                self._data["ph_sensor"] = ""
                return await self.async_step_chlore_config()

        description_key = "config.step.ph_manual.description"
        if self._no_sensor_message:
            description_key = "config.step.ph_manual.no_sensor_ph"

        return self.async_show_form(
            step_id="ph_manual",
            description_placeholders={"description": description_key},
            data_schema=vol.Schema({
                vol.Optional("ph_current", default=7.0): vol.Coerce(float),
                vol.Required("ph_target", default=7.4): vol.Coerce(float),
            }),
            errors=errors,
        )

    async def async_step_ph_sensor(self, user_input=None):
        """Step 3 (sous-étape) : sélection d'un capteur pH."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            ph_sensor = user_input.get("ph_sensor", "")
            try:
                ph_target = user_input.get("ph_target", "")
                if ph_target is None or ph_target == "":
                    errors["ph_target"] = "required_field"
                else:
                    ph_target = str(ph_target).replace(",", ".").strip()
                    ph_target = float(ph_target)
                    if not (0 <= ph_target <= 14):
                        errors["ph_target"] = "ph_invalid"
                    else:
                        self._data["ph_target"] = ph_target
            except ValueError:
                errors["ph_target"] = "invalid_number"

            if not ph_sensor and ("ph_current" not in self._data or self._data["ph_current"] is None):
                return await self.async_step_confirm_ph_sensor()

            if not errors:
                self._data["ph_sensor"] = ph_sensor if ph_sensor else ""
                self._data["use_ph_sensor"] = bool(ph_sensor)
                return await self.async_step_chlore_config()

        ph_sensors = [""]
        ph_sensors_dict = {
            "": get_translation("config.step.ph_sensor.data.no_sensor", default="Aucun capteur (saisie manuelle)"),
        }
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            if "ph_a_ajouter" in entity_id.lower() or "phaajouter" in entity_id.lower():
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            friendly_name = attributes.get("friendly_name", entity_id).lower()
            if unit == "ph" or "ph" in friendly_name or "ph" in entity_id.lower():
                friendly_name = attributes.get("friendly_name", entity_id)
                ph_sensors.append(entity_id)
                ph_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"

        _LOGGER.debug("Capteurs de pH trouvés : %s", ph_sensors)

        return self.async_show_form(
            step_id="ph_sensor",
            data_schema=vol.Schema({
                vol.Optional("ph_sensor", default=""): vol.In(ph_sensors_dict),
                vol.Required("ph_target", default=7.4): vol.Coerce(float),
            }),
            errors=errors,
        )

    async def async_step_confirm_ph_sensor(self, user_input=None):
        """Step 3 (sous-étape) : confirmation avant redirection pour pH."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "confirm_choice" in user_input:
                choice = user_input["confirm_choice"]
                if choice == "manual":
                    self._no_sensor_message = True
                    return await self.async_step_ph_manual()
                else:
                    return await self.async_step_ph_sensor()
            else:
                errors["confirm_choice"] = "required_field"

        confirm_options = {
            "manual": get_translation("config.step.confirm_ph_sensor.data.manual", default="Saisir manuellement"),
            "retry": get_translation("config.step.confirm_ph_sensor.data.retry", default="Réessayer la sélection du capteur"),
        }

        return self.async_show_form(
            step_id="confirm_ph_sensor",
            data_schema=vol.Schema({
                vol.Required("confirm_choice"): vol.In(confirm_options),
            }),
            errors=errors,
        )

    async def async_step_chlore_config(self, user_input=None):
        """Step 4 : configuration du chlore (choix entre manuel et capteur)."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "chlore_config_choice" in user_input:
                self._chlore_config_choice = user_input["chlore_config_choice"]
                if self._chlore_config_choice == "manual":
                    self._no_sensor_message = False
                    return await self.async_step_chlore_manual()
                else:
                    self._no_sensor_message = False
                    return await self.async_step_chlore_sensor()
            else:
                errors["chlore_config_choice"] = "required_field"

        chlore_config_options = {
            "manual": get_translation("config.step.chlore_config.data.manual", default="Saisie manuelle"),
            "sensor": get_translation("config.step.chlore_config.data.sensor", default="Sélectionner un capteur"),
        }

        return self.async_show_form(
            step_id="chlore_config",
            data_schema=vol.Schema({
                vol.Required("chlore_config_choice"): vol.In(chlore_config_options),
            }),
            errors=errors,
        )

    async def async_step_chlore_manual(self, user_input=None):
        """Step 4 (sous-étape) : saisie manuelle des valeurs chlore."""
        errors = {}
        if user_input is not None:
            numeric_fields = [
                ("chlore_current", "chlore_invalid", lambda x: x >= 0, False),
                ("chlore_target", "chlore_invalid", lambda x: x >= 0, True),
            ]
            for field, error_key, validator, required in numeric_fields:
                try:
                    value = user_input.get(field, "" if required else "1.0")
                    if required and (value is None or value == ""):
                        errors[field] = "required_field"
                        continue
                    if value is not None and value != "":
                        value = str(value).replace(",", ".").strip()
                        value = float(value)
                        if not validator(value):
                            errors[field] = error_key
                        self._data[field] = value
                except ValueError:
                    errors[field] = "invalid_number"

            if not errors:
                if "chlore_current" not in self._data or self._data["chlore_current"] is None:
                    self._data["chlore_current"] = 1.0
                self._data["use_chlore_sensor"] = False
                self._data["chlore_sensor"] = ""
                return await self.async_step_temperature_config()

        description_key = "config.step.chlore_manual.description"
        if self._no_sensor_message:
            description_key = "config.step.chlore_manual.no_sensor_chlore"

        return self.async_show_form(
            step_id="chlore_manual",
            description_placeholders={"description": description_key},
            data_schema=vol.Schema({
                vol.Optional("chlore_current", default=1.0): vol.Coerce(float),
                vol.Required("chlore_target", default=2.0): vol.Coerce(float),
            }),
            errors=errors,
        )

    async def async_step_chlore_sensor(self, user_input=None):
        """Step 4 (sous-étape) : sélection d'un capteur chlore."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            chlore_sensor = user_input.get("chlore_sensor", "")
            try:
                chlore_target = user_input.get("chlore_target", "")
                if chlore_target is None or chlore_target == "":
                    errors["chlore_target"] = "required_field"
                else:
                    chlore_target = str(chlore_target).replace(",", ".").strip()
                    chlore_target = float(chlore_target)
                    if not (chlore_target >= 0):
                        errors["chlore_target"] = "chlore_invalid"
                    else:
                        self._data["chlore_target"] = chlore_target
            except ValueError:
                errors["chlore_target"] = "invalid_number"

            if not chlore_sensor and ("chlore_current" not in self._data or self._data["chlore_current"] is None):
                return await self.async_step_confirm_chlore_sensor()

            if not errors:
                self._data["chlore_sensor"] = chlore_sensor if chlore_sensor else ""
                self._data["use_chlore_sensor"] = bool(chlore_sensor)
                return await self.async_step_temperature_config()

        chlore_sensors = [""]
        chlore_sensors_dict = {
            "": get_translation("config.step.chlore_sensor.data.no_sensor", default="Aucun capteur (saisie manuelle)"),
        }
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            if "chlore_a_ajouter" in entity_id.lower() or "chloreaajouter" in entity_id.lower():
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            if unit in ("mg/l", "ppm", "mg per liter", "parts per million"):
                friendly_name = attributes.get("friendly_name", entity_id)
                chlore_sensors.append(entity_id)
                chlore_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"

        _LOGGER.debug("Capteurs de chlore trouvés : %s", chlore_sensors)

        return self.async_show_form(
            step_id="chlore_sensor",
            data_schema=vol.Schema({
                vol.Optional("chlore_sensor", default=""): vol.In(chlore_sensors_dict),
                vol.Required("chlore_target", default=2.0): vol.Coerce(float),
            }),
            errors=errors,
        )

    async def async_step_confirm_chlore_sensor(self, user_input=None):
        """Step 4 (sous-étape) : confirmation avant redirection pour chlore."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "confirm_choice" in user_input:
                choice = user_input["confirm_choice"]
                if choice == "manual":
                    self._no_sensor_message = True
                    return await self.async_step_chlore_manual()
                else:
                    return await self.async_step_chlore_sensor()
            else:
                errors["confirm_choice"] = "required_field"

        confirm_options = {
            "manual": get_translation("config.step.confirm_chlore_sensor.data.manual", default="Saisir manuellement"),
            "retry": get_translation("config.step.confirm_chlore_sensor.data.retry", default="Réessayer la sélection du capteur"),
        }

        return self.async_show_form(
            step_id="confirm_chlore_sensor",
            data_schema=vol.Schema({
                vol.Required("confirm_choice"): vol.In(confirm_options),
            }),
            errors=errors,
        )

    async def async_step_temperature_config(self, user_input=None):
        """Step 5 : configuration de la température (choix entre manuel et capteur)."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "temperature_config_choice" in user_input:
                self._temperature_config_choice = user_input["temperature_config_choice"]
                if self._temperature_config_choice == "manual":
                    self._no_sensor_message = False
                    return await self.async_step_temperature_manual()
                else:
                    self._no_sensor_message = False
                    return await self.async_step_temperature_sensor()
            else:
                errors["temperature_config_choice"] = "required_field"

        temperature_config_options = {
            "manual": get_translation("config.step.temperature_config.data.manual", default="Saisie manuelle"),
            "sensor": get_translation("config.step.temperature_config.data.sensor", default="Sélectionner un capteur"),
        }

        return self.async_show_form(
            step_id="temperature_config",
            data_schema=vol.Schema({
                vol.Required("temperature_config_choice"): vol.In(temperature_config_options),
            }),
            errors=errors,
        )

    async def async_step_temperature_manual(self, user_input=None):
        """Step 5 (sous-étape) : saisie manuelle de la température."""
        errors = {}
        if user_input is not None:
            numeric_fields = [
                ("temperature", "temperature_invalid", lambda x: 0 <= x <= 50, False),
            ]
            for field, error_key, validator, required in numeric_fields:
                try:
                    value = user_input.get(field, "20.0")
                    if value is not None and value != "":
                        value = str(value).replace(",", ".").strip()
                        value = float(value)
                        if not validator(value):
                            errors[field] = "temperature_invalid"
                        self._data[field] = value
                except ValueError:
                    errors[field] = "invalid_number"

            if not errors:
                if "temperature" not in self._data or self._data["temperature"] is None:
                    self._data["temperature"] = 20.0
                self._data["use_temperature_sensor"] = False
                self._data["temperature_sensor"] = ""
                return await self.async_step_power_config()

        description_key = "config.step.temperature_manual.description"
        if self._no_sensor_message:
            description_key = "config.step.temperature_manual.no_sensor_temperature"

        return self.async_show_form(
            step_id="temperature_manual",
            description_placeholders={"description": description_key},
            data_schema=vol.Schema({
                vol.Optional("temperature", default=20.0): vol.Coerce(float),
            }),
            errors=errors,
        )

    async def async_step_temperature_sensor(self, user_input=None):
        """Step 5 (sous-étape) : sélection d'un capteur température."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            temperature_sensor = user_input.get("temperature_sensor", "")
            if not temperature_sensor and ("temperature" not in self._data or self._data["temperature"] is None):
                return await self.async_step_confirm_temperature_sensor()

            if not errors:
                self._data["temperature_sensor"] = temperature_sensor if temperature_sensor else ""
                self._data["use_temperature_sensor"] = bool(temperature_sensor)
                return await self.async_step_power_config()

        temp_sensors = [""]
        temp_sensors_dict = {
            "": get_translation("config.step.temperature_sensor.data.no_sensor", default="Aucun capteur (saisie manuelle)"),
        }
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            device_class = attributes.get("device_class", "")
            if (device_class == "temperature" or
                unit in ("°c", "°f", "c", "f", "celsius", "fahrenheit")):
                friendly_name = attributes.get("friendly_name", entity_id)
                temp_sensors.append(entity_id)
                temp_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"

        _LOGGER.debug("Capteurs de température trouvés : %s", temp_sensors)

        return self.async_show_form(
            step_id="temperature_sensor",
            data_schema=vol.Schema({
                vol.Optional("temperature_sensor", default=""): vol.In(temp_sensors_dict),
            }),
            errors=errors,
        )

    async def async_step_confirm_temperature_sensor(self, user_input=None):
        """Step 5 (sous-étape) : confirmation avant redirection pour température."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "confirm_choice" in user_input:
                choice = user_input["confirm_choice"]
                if choice == "manual":
                    self._no_sensor_message = True
                    return await self.async_step_temperature_manual()
                else:
                    return await self.async_step_temperature_sensor()
            else:
                errors["confirm_choice"] = "required_field"

        confirm_options = {
            "manual": get_translation("config.step.confirm_temperature_sensor.data.manual", default="Saisir manuellement"),
            "retry": get_translation("config.step.confirm_temperature_sensor.data.retry", default="Réessayer la sélection du capteur"),
        }

        return self.async_show_form(
            step_id="confirm_temperature_sensor",
            data_schema=vol.Schema({
                vol.Required("confirm_choice"): vol.In(confirm_options),
            }),
            errors=errors,
        )

    async def async_step_power_config(self, user_input=None):
        """Step 6 : configuration de la puissance (choix entre manuel et capteur)."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "power_config_choice" in user_input:
                self._power_config_choice = user_input["power_config_choice"]
                if self._power_config_choice == "manual":
                    self._no_sensor_message = False
                    return await self.async_step_power_manual()
                else:
                    self._no_sensor_message = False
                    return await self.async_step_power_sensor()
            else:
                errors["power_config_choice"] = "required_field"

        power_config_options = {
            "manual": get_translation("config.step.power_config.data.manual", default="Manuel (aucun capteur)"),
            "sensor": get_translation("config.step.power_config.data.sensor", default="Sélectionner un capteur"),
        }

        return self.async_show_form(
            step_id="power_config",
            data_schema=vol.Schema({
                vol.Required("power_config_choice"): vol.In(power_config_options),
            }),
            errors=errors,
        )

    async def async_step_power_manual(self, user_input=None):
        """Step 6 (sous-étape) : saisie manuelle pour la puissance (vide)."""
        description_key = "config.step.power_manual.description"
        if self._no_sensor_message:
            description_key = "config.step.power_manual.no_sensor_power"

        self._data["use_power_sensor"] = False
        self._data["power_sensor_entity_id"] = ""
        return await self.async_step_treatment_config()

    async def async_step_power_sensor(self, user_input=None):
        """Step 6 (sous-étape) : sélection d'un capteur puissance."""
        errors = {}
        if user_input is not None:
            power_sensor = user_input.get("power_sensor_entity_id", "")
            if not power_sensor:
                return await self.async_step_confirm_power_sensor()

            if not errors:
                self._data["power_sensor_entity_id"] = power_sensor if power_sensor else ""
                self._data["use_power_sensor"] = bool(power_sensor)
                return await self.async_step_treatment_config()

        return self.async_show_form(
            step_id="power_sensor",
            data_schema=vol.Schema({
                vol.Optional("power_sensor_entity_id", default=""): str,
            }),
            errors=errors,
        )

    async def async_step_confirm_power_sensor(self, user_input=None):
        """Step 6 (sous-étape) : confirmation avant redirection pour puissance."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            if "confirm_choice" in user_input:
                choice = user_input["confirm_choice"]
                if choice == "manual":
                    self._no_sensor_message = True
                    return await self.async_step_power_manual()
                else:
                    return await self.async_step_power_sensor()
            else:
                errors["confirm_choice"] = "required_field"

        confirm_options = {
            "manual": get_translation("config.step.confirm_power_sensor.data.manual", default="Poursuivre sans capteur"),
            "retry": get_translation("config.step.confirm_power_sensor.data.retry", default="Réessayer la sélection du capteur"),
        }

        return self.async_show_form(
            step_id="confirm_power_sensor",
            data_schema=vol.Schema({
                vol.Required("confirm_choice"): vol.In(confirm_options),
            }),
            errors=errors,
        )

    async def async_step_treatment_config(self, user_input=None):
        """Step 7 : configuration des types de traitements."""
        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        errors = {}
        if user_input is not None:
            self._data["ph_plus_treatment"] = user_input.get("ph_plus_treatment", "Liquide")
            self._data["ph_minus_treatment"] = user_input.get("ph_minus_treatment", "Liquide")
            self._data["chlore_treatment"] = user_input.get("chlore_treatment", "Chlore choc (poudre)")
            return await self.async_step_summary()

        ph_plus_options = {
            "Liquide": get_translation("config.step.treatment_config.data.ph_plus_treatment_liquid", default="Liquide"),
            "Granulés": get_translation("config.step.treatment_config.data.ph_plus_treatment_granules", default="Granulés"),
        }
        ph_minus_options = {
            "Liquide": get_translation("config.step.treatment_config.data.ph_minus_treatment_liquid", default="Liquide"),
            "Granulés": get_translation("config.step.treatment_config.data.ph_minus_treatment_granules", default="Granulés"),
        }
        chlore_options = {
            "Liquide": get_translation("config.step.treatment_config.data.chlore_treatment_liquid", default="Liquide"),
            "Chlore choc (poudre)": get_translation("config.step.treatment_config.data.chlore_treatment_shock", default="Chlore choc (poudre)"),
            "Pastille lente": get_translation("config.step.treatment_config.data.chlore_treatment_tablet", default="Pastille à dissolution lente"),
        }

        return self.async_show_form(
            step_id="treatment_config",
            data_schema=vol.Schema({
                vol.Required("ph_plus_treatment", default="Liquide"): vol.In(ph_plus_options),
                vol.Required("ph_minus_treatment", default="Liquide"): vol.In(ph_minus_options),
                vol.Required("chlore_treatment", default="Chlore choc (poudre)"): vol.In(chlore_options),
            }),
            errors=errors,
            description_placeholders={
                "description": "config.step.treatment_config.description"
            },
        )

    async def async_step_summary(self, user_input=None):
        """Step 8 : récapitulatif avant validation."""
        if user_input is not None:
            # Créer une copie de self._data avec toutes les valeurs numériques converties en chaînes
            data_to_save = {}
            for key, value in self._data.items():
                if isinstance(value, (float, int)):
                    data_to_save[key] = str(value)
                else:
                    data_to_save[key] = value
            return self.async_create_entry(title=f"Piscinexa {self._data['name']}", data=data_to_save)

        # Charger les traductions pour le récapitulatif
        if not self._translations:
            self._translations = await async_get_translations(
                self.hass,
                self.hass.config.language,
                "config",
            )

        def get_translation(key: str, placeholders: dict = None, default: str = None) -> str:
            translation_key = key
            translated = self._translations.get(translation_key, default or translation_key)
            if placeholders:
                try:
                    return translated.format(**placeholders)
                except (KeyError, ValueError):
                    return translated
            return translated

        pool_type_label = "config.step.summary.labels.pool_type_square" if self._data["pool_type"] == POOL_TYPE_SQUARE else "config.step.summary.labels.pool_type_round"
        ph_source = "config.step.summary.labels.sensor" if self._data.get("use_ph_sensor", False) else "config.step.summary.labels.manual"
        chlore_source = "config.step.summary.labels.sensor" if self._data.get("use_chlore_sensor", False) else "config.step.summary.labels.manual"
        temperature_source = "config.step.summary.labels.sensor" if self._data.get("use_temperature_sensor", False) else "config.step.summary.labels.manual"
        power_source = "config.step.summary.labels.sensor" if self._data.get("use_power_sensor", False) else "config.step.summary.labels.manual"

        summary = [
            f"{get_translation('config.step.summary.labels.pool_name', default='Nom de la piscine')}: {self._data['name']}",
            f"{get_translation('config.step.summary.labels.pool_type', default='Type de piscine')}: {get_translation(pool_type_label, default='Carrée' if self._data['pool_type'] == POOL_TYPE_SQUARE else 'Ronde')}",
            f"{get_translation('config.step.summary.labels.dimensions', default='Dimensions')}: {self._get_dimensions_summary()}",
            f"{get_translation('config.step.summary.labels.ph_current', default='pH actuel')}: {str(self._data.get('ph_current', get_translation('config.step.summary.labels.not_defined', default='Non défini')))}",
            f"{get_translation('config.step.summary.labels.ph_target', default='pH cible')}: {str(self._data['ph_target'])}",
            f"{get_translation('config.step.summary.labels.ph_source', default='Source pH')}: {get_translation(ph_source, default='Capteur' if self._data.get('use_ph_sensor', False) else 'Manuel')} ({self._data.get('ph_sensor', get_translation('config.step.summary.labels.no_selection', default='Non sélectionné'))})",
            f"{get_translation('config.step.summary.labels.ph_plus_treatment', default='Type de traitement pH+')}: {self._data.get('ph_plus_treatment', 'Liquide')}",
            f"{get_translation('config.step.summary.labels.ph_minus_treatment', default='Type de traitement pH-')}: {self._data.get('ph_minus_treatment', 'Liquide')}",
            f"{get_translation('config.step.summary.labels.chlore_current', default='Chlore actuel')}: {str(self._data.get('chlore_current', get_translation('config.step.summary.labels.not_defined', default='Non défini')))} {get_translation('config.step.summary.labels.unit_mg_per_liter', default='mg/L')}",
            f"{get_translation('config.step.summary.labels.chlore_target', default='Chlore cible')}: {str(self._data['chlore_target'])} {get_translation('config.step.summary.labels.unit_mg_per_liter', default='mg/L')}",
            f"{get_translation('config.step.summary.labels.chlore_source', default='Source chlore')}: {get_translation(chlore_source, default='Capteur' if self._data.get('use_chlore_sensor', False) else 'Manuel')} ({self._data.get('chlore_sensor', get_translation('config.step.summary.labels.no_selection', default='Non sélectionné'))})",
            f"{get_translation('config.step.summary.labels.chlore_treatment', default='Type de traitement chlore')}: {self._data.get('chlore_treatment', 'Chlore choc (poudre)')}",
            f"{get_translation('config.step.summary.labels.temperature', default='Température')}: {str(self._data.get('temperature', get_translation('config.step.summary.labels.not_defined', default='Non défini')))} {get_translation('config.step.summary.labels.unit_degrees_celsius', default='°C')}",
            f"{get_translation('config.step.summary.labels.temperature_source', default='Source température')}: {get_translation(temperature_source, default='Capteur' if self._data.get('use_temperature_sensor', False) else 'Manuel')} ({self._data.get('temperature_sensor', get_translation('config.step.summary.labels.no_selection', default='Non sélectionné'))})",
            f"{get_translation('config.step.summary.labels.power_source', default='Source puissance')}: {get_translation(power_source, default='Capteur' if self._data.get('use_power_sensor', False) else 'Manuel')} ({self._data.get('power_sensor_entity_id', get_translation('config.step.summary.labels.no_selection', default='Non sélectionné'))})",
        ]

        return self.async_show_form(
            step_id="summary",
            description_placeholders={"summary": "\n".join(summary)},
            data_schema=vol.Schema({}),
        )

    def _get_dimensions_summary(self):
        """Retourne un résumé des dimensions de la piscine."""
        if self._data["pool_type"] == POOL_TYPE_SQUARE:
            return f"Longueur: {self._data['length']} m, Largeur: {self._data['width']} m, Profondeur: {self._data['depth']} m"
        else:
            return f"Diamètre: {self._data['diameter']} m, Profondeur: {self._data['depth']} m"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PiscinexaOptionsFlowHandler()

class PiscinexaOptionsFlowHandler(config_entries.OptionsFlow):
    """Gestionnaire des options pour Piscinexa."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        def get_translation(key: str, default: str = None) -> str:
            return self._translations.get(key, default or key)

        self._translations = await async_get_translations(
            self.hass,
            self.hass.config.language,
            "config",
        )

        temp_sensors = [""]
        temp_sensors_dict = {
            "": get_translation("config.step.init.data.no_sensor_temperature", default="Aucun capteur température"),
        }
        temp_sensor_entities = []
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            device_class = attributes.get("device_class", "").lower()
            friendly_name = attributes.get("friendly_name", entity_id).lower()
            if (device_class == "temperature" or
                unit in ("°c", "°f", "c", "f", "celsius", "fahrenheit") or
                "temperature" in friendly_name or "temp" in friendly_name):
                friendly_name = attributes.get("friendly_name", entity_id)
                temp_sensors.append(entity_id)
                temp_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"
                temp_sensor_entities.append((entity_id, unit, device_class, friendly_name))

        if len(temp_sensors) == 1:
            temp_sensors.append("sensor.test_temperature")
            temp_sensors_dict["sensor.test_temperature"] = "Test Temperature Sensor (sensor.test_temperature)"
            temp_sensor_entities.append(("sensor.test_temperature", "°C", "temperature", "Test Temperature Sensor"))

        chlore_sensors = [""]
        chlore_sensors_dict = {
            "": get_translation("config.step.init.data.no_sensor_chlore", default="Aucun capteur chlore"),
        }
        chlore_sensor_entities = []
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            if "chlore_a_ajouter" in entity_id.lower() or "chloreaajouter" in entity_id.lower():
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            friendly_name = attributes.get("friendly_name", entity_id).lower()
            if unit in ("mg/l", "ppm", "mg per liter", "parts per million") or "chlorine" in friendly_name or "chlore" in friendly_name:
                friendly_name = attributes.get("friendly_name", entity_id)
                chlore_sensors.append(entity_id)
                chlore_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"
                chlore_sensor_entities.append((entity_id, unit, friendly_name))

        ph_sensors = [""]
        ph_sensors_dict = {
            "": get_translation("config.step.init.data.no_sensor_ph", default="Aucun capteur pH"),
        }
        ph_sensor_entities = []
        for state in self.hass.states.async_all("sensor"):
            entity_id = state.entity_id
            if entity_id.startswith(f"sensor.{DOMAIN}_"):
                continue
            if "ph_a_ajouter" in entity_id.lower() or "phaajouter" in entity_id.lower():
                continue
            attributes = state.attributes
            unit = attributes.get("unit_of_measurement", "").lower()
            friendly_name = attributes.get("friendly_name", entity_id).lower()
            if unit == "ph" or "ph" in friendly_name or "ph" in entity_id.lower():
                friendly_name = attributes.get("friendly_name", entity_id)
                ph_sensors.append(entity_id)
                ph_sensors_dict[entity_id] = f"{friendly_name} ({entity_id})"
                ph_sensor_entities.append((entity_id, unit, friendly_name))

        if len(ph_sensors) == 1:
            ph_sensors.append("sensor.test_ph")
            ph_sensors_dict["sensor.test_ph"] = "Test pH Sensor (sensor.test_ph)"
            ph_sensor_entities.append(("sensor.test_ph", "pH", "Test pH Sensor"))

        _LOGGER.debug("Capteurs de température trouvés dans les options : %s", temp_sensors)
        _LOGGER.debug("Détails des capteurs de température : %s", temp_sensor_entities)
        _LOGGER.debug("Capteurs de chlore trouvés dans les options : %s", chlore_sensors)
        _LOGGER.debug("Détails des capteurs de chlore : %s", chlore_sensor_entities)
        _LOGGER.debug("Capteurs de pH trouvés dans les options : %s", ph_sensors)
        _LOGGER.debug("Détails des capteurs de pH : %s", ph_sensor_entities)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("ph_target", default=current.get("ph_target", 7.4)): vol.Coerce(float),
                vol.Optional("chlore_target", default=current.get("chlore_target", 2.0)): vol.Coerce(float),
                vol.Optional("temperature_sensor", default=current.get("temperature_sensor", "")): vol.In(temp_sensors_dict),
                vol.Optional("chlore_sensor", default=current.get("chlore_sensor", "")): vol.In(chlore_sensors_dict),
                vol.Optional("ph_sensor", default=current.get("ph_sensor", "")): vol.In(ph_sensors_dict),
            }),
        )
