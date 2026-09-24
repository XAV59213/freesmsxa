# Changelog

All notable changes to the Free Mobile SMS XA Home Assistant integration will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [6.12.0] - 2026-09-24

### Added

- Quota handling for Free Mobile HTTP 402 (`quota_exceeded`), with sensor state `Quota` and `quota_status: throttled`.
- SMS history of the last 50 messages (success and failures) on the status sensor `sms_log`.
- Events `freesmsxa_sms_sent` and `freesmsxa_sms_failed` for automations / logbook.
- Numeric sensors **SMS sent** and **SMS today** (graphable).
- Config entry diagnostics (token redacted) from the device page.
- Options toggle **Enable debug logging**.
- Lovelace card: 160-character counter, visual title editor, no full re-render on each state update.

### Changed

- Failed sends are recorded in history instead of being silent on the sensor.

## [6.11.2] - 2026-09-24

### Fixed

- Lovelace resource registration on current Home Assistant (`resource_mode` instead of `mode`).
- Custom card missing in the dashboard editor (`Custom element not found`).

## [6.11.1] - 2026-09-24

### Fixed

- Send button overflowing onto the next dashboard card on mobile.

## [6.11.0] - 2026-09-24

### Added

- Native Lovelace card **Envoyer un SMS** (`custom:freesmsxa-send-card`).

## [6.10.0] - 2026-09-24

### Fixed

- RuntimeError `Cannot be called from within the event loop` when calling `freesmsxa.send_sms`.
- Test SMS button ignored option changes until a full restart.
- Failed SMS sends were logged but treated as success by Home Assistant.
- SMS counter and history were lost on restart.

### Changed

- Shared `FreeClient` stored on `entry.runtime_data`.
- Status sensor uses `RestoreEntity`.

### Added

- Reconfigure flow, translated errors, French phone validation.

## [6.9.2] - 2026-09-24

### Fixed

- Replaced `hass.services.services` with `hass.services.has_service()`.
