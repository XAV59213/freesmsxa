# Correctifs locaux cumulatifs — round7

Base47eaf170614c44aadcdf1e97b22b41ed97611815,7novembre2026 Europe/Paris ; rien publié,aucun SMS réel/HA maison/bump. **36done/11exempt/7todo**,pas niveau officiel. Les trois diagnostics locaux HA2025 du round6 sont maintenant0 ; SDK non pleinement typé => strict-typing officiel reste ouvert.

## Delta round7

- schema.py : type concret du schéma public HA + marqueurs du même moteur vérifiés, remplace imports TYPE_CHECKING probatio dans __init__/config_flow. HA2026 disposait déjà d’un bridge runtime ; probe baselinePASS, pas défaut UI inventé.
- migration.py : Protocol précis et signature.bind avant le seul appel privé de préservation d’un cache existant. Pas cast ou ignore ; dérive échoue fermée, erreur localisée EN/FR sans valeurs privées. Noms/IDs/personnalisations préservés ; limite interne assumée.
- sensor.py : compteurs restaurés robustes, timestamps/erreurs/quota/journal validés et allowlistés, copie sans mutation latérale, restauration sans doublons. Snapshot synthétique round6republiantPRIVATE désormais assaini ; valeurs/records valides conservés, pas purge historique.
- 28tests ajoutés ; contrats statiques positifs et négatifs, vrai FlowManager/service refusant données invalides sans client/SMS, cache natif/absence2025/dérive, metadata/diagnostics/restauration/copies/compatibilité. Nouvelle erreur de migration traduite strings/EN/FR.
- Revue ciblée cumulative documentée dans SECURITY_REVIEW.md ; pas nouvelle recherche brands/async, ni nouvelle dépendance transport/SDK/pin. Mypy ajouté seulement aux outils dev de l’ancienne venv, pas au manifest.

Correctifs rounds1–6 conservés : confidentialité diagnostics/logs/historique, reauth/reconfigure/options/erreurs, disponibilité/retry explicite, noms/traductions/icônes/registres/IDs, bouton neuf désactivé, compteurs/date, frontend borné, docs et tests. Transport sync/executor10/30s et retry500unique inchangés ; pas timeout total/session HA.

## Vérifications

217tests×4scénarios HA2025.12/2026.11 ×SDK0.2/0.3 et4replays propres. Couverture actuel99,648 %,ancien99,179 %,union99,648 % (711/711lignes,139/142branches). Mypy **0/12dans DEUX environnements** ; probes négatifs2erreurs attendues chacun, pas erreurs source.4probes JS,hassfest0invalide, statique/patch propre/reproductionZIP/SHA historiques vérifiés.

Limites et recommandation : SECURITY_REVIEW.md et REMAINING_ACTIONS.md. Revue+HA de développement sauvegardé, puis choix HACS pragmatique ou projet core ; autorisation distincte pour version/cache/publication. Aucune boucle vague ni promotion officielle.

Livrables freesmsxa-local-fixes-round7.patch/.zip/.sha256 et AUDIT/YAML/LOCAL_FIXES/NAMING_MIGRATION/TRANSPORT_DECISION/REMAINING_ACTIONS/SECURITY_REVIEW. Cumulatif depuis base,anciens artefacts intacts.
