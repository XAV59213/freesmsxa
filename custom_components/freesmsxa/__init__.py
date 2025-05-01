# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification service in Home Assistant."""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
import logging

from freesms import FreeClient

from homeassistant.components.notify import BaseNotificationService
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")

    # Create and register the notification service
    hass.services.async_register(
        "notify",
        service_name,
        FreeSMSNotificationService(hass, username, access_token, service_name).async_send_message,
        schema=None,
    )

    # Store the service name for unloading
    hass.data[DOMAIN][entry.entry_id] = service_name

    # Add sensor entity
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    service_name = hass.data[DOMAIN].pop(entry.entry_id, None)
    if service_name:
        hass.services.async_remove("notify", service_name)
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    return True

async def async_setup_entry_sensors(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get(CONF_NAME, f"freesmsxa_{username.replace('.', '_').lower()}")
    sensor = FreeSMSStatusSensor(hass, username, access_token, service_name, entry.entry_id)
    async_add_entities([sensor])
    hass.data[DOMAIN].setdefault("sensors", []).append(sensor)

class FreeSMSNotificationService(BaseNotificationService):
    """Implement a notification service for the Free Mobile SMS service."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str) -> None:
        """Initialize the service."""
        self.hass = hass
        self.free_client = FreeClient(username, access_token)
        self.service_name = service_name

    async def async_send_message(self, message: str, **kwargs: any) -> None:
        """Send a message to the Free Mobile user cell."""
        try:
            resp = await self.hass.async_add_executor_job(
                self.free_client.send_sms, message
            )

            status = "OK"
            if resp.status_code == HTTPStatus.BAD_REQUEST:
                status = "Erreur : Paramètre manquant"
                _LOGGER.error("At least one parameter is missing")
            elif resp.status_code == HTTPStatus.PAYMENT_REQUIRED:
                status = "Erreur : Limite d'envoi atteinte"
                _LOGGER.error("Too many SMS sent in a short time")
            elif resp.status_code == HTTPStatus.FORBIDDEN:
                status = "Erreur : Identifiants incorrects"
                _LOGGER.error("Wrong username or password")
            elif resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
                status = "Erreur : Serveur indisponible"
                _LOGGER.error("Server error, try later")

            # Update sensor state
            sensor = next(
                (entity for entity in self.hass.data[DOMAIN].get("sensors", [])
                 if entity.service_name == self.service_name), None
            )
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())

        except Exception as exc:
            status = f"Erreur : {str(exc)}"
            _LOGGER.error("Failed to send SMS: %s", exc)
            if sensor:
                sensor.update_state(status, datetime.now().isoformat())

class FreeSMSStatusSensor(SensorEntity):
    """Sensor to display the status of the Free Mobile SMS API."""

    def __init__(self, hass: HomeAssistant, username: str, access_token: str, service_name: str, entry_id: str) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._username = username
        self._access_token = access_token
        self.service_name = service_name
        self._state = "Inconnu"
        self._sms_count = 0
        self._last_sent = None
        self._attr_unique_id = f"freesmsxa_{entry_id}_status"
        self._attr_name = f"Free Mobile SMS {username} Status"
        self._attr_icon = "mdi:cellphone-message"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_extra_state_attributes = {
            "last_sent": None,
            "sms_count": 0
        }

    def update_state(self, status: str, last_sent: str | None = None) -> None:
        """Update the sensor state and attributes."""
        self._state = status
        if last_sent:
            self._last_sent = last_sent
            self._sms_count += 1
            self._attr_extra_state_attributes = {
                "last_sent": self._last_sent,
                "sms_count": self._sms_count
            }
        self.async_write_ha_state()

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self._state
