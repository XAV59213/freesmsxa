# Changelog

All notable changes to the Free Mobile SMS XA Home Assistant integration will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [6.12.13] - 2026-11-08

### FR

- Confidentialité : diagnostics/test_message/alias assainis, retrait des données SMS des nouveaux logs de l’intégration ; métadonnées restaurées validées. Pas de purge rétroactive des sauvegardes/historiques.
- Réauthentification/reconfiguration natives et erreurs traduites ; disponibilité/reprise explicite sans SMS au setup/polling. Opt-out du test de configuration conservé.
- Noms/traductions/icônes/catégories et migration conservant IDs/personnalisations. Certains noms affichés par défaut changent ; nouveau bouton test désactivé par défaut, choix existants conservés. Shim interne compat_name isolé et testé, pas garantie toutes versions.
- Version manifest et cache frontend alignés sur6.12.13 ; ressources Lovelace anciennes mises à jour sans changement de leur identité. Aucun autre changement fonctionnel depuis round7.
- Validation locale round7 :217tests×4scénarios HA2025.12/2026.11 ×freesms0.2/0.3 ; deux cas de cache supplémentaires pour cette publication. Couverture actuelle/union99,648 %,historique99,179 %,mypy propre dans les deux HA,hassfest/probes JS. SDK0.2par overlay runtime, pas quatre locks frais. Aucun SMS réel ni accès HA maison ; pas startup complet/navigateur/toutes versions prouvés.
- Audit :36done/11exempt/7todo,aucun niveau Quality Scale officiel. Transport SDK synchrone/executor/GET inchangé : pas timeout total/sessionHA/exactly-once. Annulation/retry peuvent laisser un résultat de livraison ambigu ; ne pas activer la trace HTTP globale avec de vraies clés. Warning HACS non bloquant : catégories du manifest absentes.

### EN

- Redacted diagnostics/integration logging, validated restore metadata, native reauthentication and translated errors. No retroactive scrub of old backups/history.
- Preserve entity IDs and user registry customizations; default displayed names may change. Newly created test buttons are disabled by default, existing choices remain. A narrow internal compat_name shim is still required on tested modern HA.
- Manifest/frontend cache aligned to6.12.13. Explicit recovery and configuration-test opt-out remain; no setup/polling SMS. Tests block/mock networking; no real SMS or user HA access.
- No official Quality Scale tier:36done/11exempt/7todo. SDK remains synchronous with no total timeout/shared HA session/exactly-once guarantee. See docs/SECURITY_REVIEW.md and docs/REMAINING_ACTIONS.md. Historical audit documents retain their pre-publication context.

## 6.12.8

- docs: badge Downloads cumulés

## 6.12.8

- docs: badge Downloads cumulés

## [6.12.6] - 2026-10-28

### Changed

- Publication / HACS : chaque release GitHub joint désormais l'archive **`freesmsxa.zip`** (contenu de `custom_components/freesmsxa`, sans `__pycache__` ni `.pyc`). `hacs.json` passe en `"zip_release": true` / `"filename": "freesmsxa.zip"` : HACS installe depuis ce zip et affiche un **compteur de téléchargements**. Nouveau workflow `release-zip.yaml` (release publiée à la main, lancement manuel, ou appelé par les workflows de release existants) qui vérifie que le tag correspond à la version de `manifest.json`. Aucun code de l'intégration modifié

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
