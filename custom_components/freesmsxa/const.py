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
VERSION = "6.12.2"

SERVICE_SEND_SMS = "send_sms"
ATTR_TARGET = "target"
ATTR_MESSAGE = "message"

URL_BASE = "/freesmsxa"
LOCAL_CARD_PATH = "/local/freesmsxa-send-card.js"
CARD_FILENAME = "freesmsxa-send-card.js"
JSMODULES = [
    {
        "name": "Envoyer un SMS",
        "filename": CARD_FILENAME,
        "version": VERSION,
    }
]

SMS_LOG_MAX = 50
SMS_MAX_LENGTH = 1000
EVENT_SMS_SENT = f"{DOMAIN}_sms_sent"
EVENT_SMS_FAILED = f"{DOMAIN}_sms_failed"
LOGGER_NAME = f"custom_components.{DOMAIN}"

API_STATUS_OK = 200
API_STATUS_BAD_REQUEST = 400
API_STATUS_QUOTA = 402
API_STATUS_FORBIDDEN = 403
API_STATUS_SERVER = 500
API_RETRY_STATUSES = frozenset({API_STATUS_SERVER})
API_RETRY_DELAY = 2

API_STATUS_ERRORS = {
    API_STATUS_BAD_REQUEST: "invalid_message",
    API_STATUS_QUOTA: "quota_exceeded",
    API_STATUS_FORBIDDEN: "invalid_auth",
    API_STATUS_SERVER: "server_error",
}
