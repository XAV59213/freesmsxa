# Tests locaux — round7, jamais SMS réel

217tests par scénario HA2026.11.0/Python3.14.9 et HA2025.12.0/Python3.13.18 ×freesms0.3/0.2. Réseau bloqué par fixture requests/aiohttp/httpx/httpx2 ; FreeClient contractuel appelle requests.get doublé, jamais Free réel.

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
COVERAGE_FILE=.coverage-current .venv/bin/python -m pytest -q --cov=custom_components.freesmsxa --cov-branch --cov-report=json:coverage-current.json
.venv/bin/python -m mypy
node tests/check_frontend.cjs
python3.13 -m venv .venv-ha2025
.venv-ha2025/bin/pip install -r requirements-test-ha2025.txt
.venv-ha2025/bin/pip install mypy==2.4.1
COVERAGE_FILE=.coverage-ha2025 .venv-ha2025/bin/python -m pytest -q --cov=custom_components.freesmsxa --cov-branch --cov-report=json:coverage-ha2025.json
.venv-ha2025/bin/python -m mypy
COVERAGE_FILE=.coverage-union .venv/bin/python -m coverage combine --keep .coverage-current .coverage-ha2025
COVERAGE_FILE=.coverage-union .venv/bin/python -m coverage report --precision=3
uv pip install --target /chemin/overlay --no-deps freesms==0.2.0
PYTHONPATH=/chemin/overlay .venv/bin/python -m pytest -q
PYTHONPATH=/chemin/overlay .venv-ha2025/bin/python -m pytest -q
```

Mypy2.4.1 **0/12sur les deux interpréteurs réels**,pas uniquement target-python. Option --python-executable encore possible mais pas nécessaire ici. Exigences HA/SDK inchangées ; pycares4.11historique conservé. Environnements existants réutilisés et inventoriés, pas quatre résolutions fraîches/locks complets. Overlay0.2runtime seulement, pas preuve typing SDK0.2.

Actuel99,648 %,historique99,179 %,union réelle99,648 % :711/711lignes,139/142branches. 9lignes standard TYPE_CHECKING/Protocol exclues,aucun omit/exclusion manuel. SourceMap/JSON donnent détail ; chemins privés modernes non parcourus par ancien HA, pas100 %sur chaque module historique prétendu.

Tests cumulés : diagnostics/logs/options/reauth/reconfigure/erreurs ; ressources/frontend4probes faux DOM ; cycle entité/restauration/date/counters/disponibilité/log transitions ; vrais registres/migrations/choix existants/ENFR/IDs ; vrai loader/domaine/forwarding/services/unload/reload/issue403réauth ; round7moteur nativeSchema/contrats, drift privé fail-closed traduit, invalidation sans SMS, stockage allowlisté/copie/backup inchangé/legacyoptionnel. 28cas ajoutés depuis round6.

Deux probes de contrats statiques supplémentaires (preuves archive) : positif accepté dans les deux environnements ; négatif **deux erreurs ATTENDUES**,confirmant que types ne sont pas simplement Any. Probe natif invalidation PASS déjà round6via bridge HA ; ne pas annoncer de panne UI démontrée. Probe stockage FAIL round6/PASS round7sur snapshot synthétique, pas maison utilisateur.

Frontières réseau et UI/HTTP doublées, skip_pip au setup, sans serveur web ; vrais managers/registry/services/flows/issues locaux. Pas startup complet, navigateur/HACS/CI distante/Free réel ou toutes versions. PRIVATE/FAKE sont synthétiques. SDK0.2sans marker et0.3non pleinement annoté : strict-typing officiel encore todo malgré mypy propre. Voir docs/AUDIT.md,docs/SECURITY_REVIEW.md et docs/REMAINING_ACTIONS.md ; aucun niveau officiel.
