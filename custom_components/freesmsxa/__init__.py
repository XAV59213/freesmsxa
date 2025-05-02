# Copyright (c) 2025 XAV59213
# This file is part of the Free Mobile SMS XA integration for Home Assistant.
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.

"""Support for Free Mobile SMS platform as a notification device in Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.components.notify import BaseNotificationService
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceEntryType, async_get as async_get_device_registry
from homeassistant.helpers.typing import ConfigType

from .notify import FreeSMSNotificationService

_LOGGER = logging.getLogger(__name__)

DOMAIN = "freesmsxa"
CONF_PHONE_NUMBER = "phone_number"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Free Mobile SMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data[CONF_USERNAME]
    access_token = entry.data[CONF_ACCESS_TOKEN]
    service_name = entry.data.get("name") or f"freesmsxa_{username.replace('.', '_').lower()}"

    # Crée un appareil dans le registre
    device_registry = async_get_device_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"freesmsxa_{username}")},
        name=f"Free Mobile SMS ({username})",
        manufacturer="Free Mobile",
        model="SMS Gateway",
        sw_version="1.0",
        entry_type=DeviceEntryType.SERVICE,
    )

    # Crée et enregistre le service de notification
    notification_service = FreeSMSNotificationService(hass, username, access_token)

    async def handle_send_message(service_call: ServiceCall) -> None:
        """Gère l'appel du service spécifique (notify.nom_service)."""
        data = dict(service_call.data)
        if "message" not in data:
            _LOGGER.error("Champ 'message' manquant dans les données du service")
            return
        message = data["message"]
        result = await notification_service.async_send_message(message)
        hass.bus.async_fire(f"{DOMAIN}_status_update", result)

    hass.services.async_register(
        "notify",
        service_name,
        handle_send_message,
    )
    _LOGGER.info("Service de notification enregistré : notify.%s", service_name)

    # Enregistre le service générique freesmsxa.send_sms
    async def handle_send_sms(call: ServiceCall) -> None:
        """Gère l'envoi de SMS via le service générique."""
        target = call.data.get("target")
        message = call.data.get("message")

        if not target or not message:
            _LOGGER.error("Paramètres manquants: target=%s, message=%s", target, message)
            return

        if not hass.services.has_service("notify", target):
            _LOGGER.error("Le service notify.%s n'existe pas", target)
            return

        await hass.services.async_call(
            "notify",
            target,
            {"message": message},
            blocking=True,
        )

    hass.services.async_register(
        DOMAIN,
        "send_sms",
        handle_send_sms
    )
    _LOGGER.info("Service générique freesmsxa.send_sms enregistré")

    # Stocke les données pour le déchargement
    hass.data[DOMAIN][entry.entry_id] = {
        "service_name": service_name,
    }

    # Active la plateforme capteur
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharge une entrée de configuration."""
    data = hass.data[DOMAIN].pop(entry.entry_id, {})
    service_name = data.get("service_name")
    if service_name:
        hass.services.async_remove("notify", service_name)
        _LOGGER.debug("Service notify.%s désenregistré", service_name)

    await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    return True
