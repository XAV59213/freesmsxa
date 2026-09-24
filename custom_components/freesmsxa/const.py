"""Constants for Free Mobile SMS XA."""

DOMAIN = "freesmsxa"
CONF_PHONE_NUMBER = "phone_number"
CONF_TEST_MESSAGE = "test_message"
CONF_SEND_TEST_SMS = "send_test_sms"
CONF_DEBUG = "debug"

DEFAULT_TEST_MESSAGE = "Test SMS envoyé depuis Home Assistant"

PLATFORMS = ["notify", "sensor", "button"]

MANUFACTURER = "Free Mobile"
MODEL = "SMS Gateway"
VERSION = "6.12.0"

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

SMS_LOG_MAX = 50
EVENT_SMS_SENT = f"{DOMAIN}_sms_sent"
EVENT_SMS_FAILED = f"{DOMAIN}_sms_failed"
LOGGER_NAME = f"custom_components.{DOMAIN}"
