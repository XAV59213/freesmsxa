"""Constants for Free Mobile SMS XA."""

DOMAIN = "freesmsxa"
CONF_PHONE_NUMBER = "phone_number"
CONF_TEST_MESSAGE = "test_message"
CONF_SEND_TEST_SMS = "send_test_sms"

DEFAULT_TEST_MESSAGE = "Test SMS envoyé depuis Home Assistant"

PLATFORMS = ["notify", "sensor", "button"]

MANUFACTURER = "Free Mobile"
MODEL = "SMS Gateway"
VERSION = "6.11.0"

SERVICE_SEND_SMS = "send_sms"
ATTR_TARGET = "target"
ATTR_MESSAGE = "message"

URL_BASE = "/freesmsxa"
JSMODULES = [
    {
        "name": "Envoyer un SMS",
        "filename": "freesmsxa-send-card.js",
        "version": VERSION,
    }
]
