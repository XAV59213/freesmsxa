# Changelog

All notable changes to the Free Mobile SMS XA Home Assistant integration will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [6.10.0] - 2026-09-24

### Fixed

- RuntimeError `Cannot be called from within the event loop` when calling `freesmsxa.send_sms` (`hass.services.services` is not event-loop safe).
- Test SMS button ignored option changes until a full restart.
- Notify / button / sensor used inconsistent device names.
- Failed SMS sends were logged but treated as success by Home Assistant.
- SMS counter and history were lost on restart.

### Changed

- Device name no longer embeds a token prefix or phone number.
- Shared `FreeClient` stored on `entry.runtime_data` instead of duplicating credentials on every entity.
- Status sensor uses `RestoreEntity`, `dt_util` and `_attr_native_value`.
- `send_sms` validates input with a schema and raises `ServiceValidationError` on an unknown target.
- Config entries use `async_set_unique_id` to prevent duplicate accounts.
- `iot_class` set to `cloud_polling`.

### Added

- Options reload listener so the test message is applied immediately.
- Reconfigure flow to update API key, alias and phone number without deleting the entry.
- Optional validation SMS checkbox during initial setup.
- French phone number format check.
- Translated entity names, exceptions and service descriptions.

## [6.9.2] - 2026-09-24

### Fixed

- Replaced `hass.services.services` with `hass.services.has_service()` in `send_sms`.
- Accept both `papa` and `notify.papa` as target.
- Fall back to `notify.send_message` when only a notify entity exists.

## [6.9.1] - 2025-12-07

### Changed

- Maintenance release of the Free Mobile SMS XA integration.
