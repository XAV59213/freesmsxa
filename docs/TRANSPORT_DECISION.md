# Transport — décision locale round6

7 novembre 2026, Europe/Paris. Aucun SMS réel, accès HA maison, modification d’un autre dépôt ou publication. Manifest inchangé (`freesms>=0.2.0`).

## Décision finie, pas recherche indéfinie

**Ne pas adopter freemobile-sms-client 0.1.0 dans cette livraison.** Sa provenance est maintenant établie, contrairement au constat incomplet du round4. Il s’agit d’un vrai client async, avec injection et respect de la propriété du client externe ; ces capacités sont reconnues. Mais adoption sûre et maintenable de son contrat HTTPX dans les deux HA, confidentialité et garanties fournisseur ne sont pas démontrées par cette revue statique. Aucun module HTTP artisanal, dépendance publiée, fork ou faux done async n’a été ajouté.

Le transport de production reste freesms/requests dans executor, timeout connexion/lecture10/30s, un retry HTTP500 après2s, **sans borne totale ni session HA injectée**. Un timeout asyncio autour du thread n’arrête pas sûrement l’envoi : pas de fausse correction pouvant encourager un doublon. Les chemins send/config/reconfigure/reauth et leurs erreurs demeurent testés.

## Candidat : source, licence et publication désormais vérifiées

- [PyPI freemobile-sms-client0.1.0](https://pypi.org/project/freemobile-sms-client/0.1.0/) ; wheel SHA256 `a5036101d8563a94c8b9680a87a96286c5f2e370c6a9d93591dc51913c61d90d`, sdist `5121f5cb4da007de73fc644575e4d6802a3e42916c20bf0acb5546533a00842b`.
- Les attestations PEP740 **wheel et sdist ont été vérifiées cryptographiquement** avec pypi-attestations0.0.30 et le dépôt attendu [kemar-openclaw/freemobile-sms](https://github.com/kemar-openclaw/freemobile-sms). Ce lien a été trouvé dans le certificat, pas deviné d’après l’auteur PyPI.
- Certificat : workflow `.github/workflows/release.yml@refs/tags/v0.1.2`, commit `2a8deaf461784784fd7a25d0297f57e9766af904`. Sujet/hash vérifiés séparément. **Le tag est v0.1.2 mais l’artefact et pyproject restent0.1.0** : incohérence enregistrée, pas preuve d’attaque ni de version0.1.2 installable depuis PyPI.
- Tous les six modules Python de la wheel correspondent au sdist ET aux Git blobs de ce commit. LICENSE MIT, pyproject et workflow de release également identiques entre source publiée et commit. Source et pipeline sont publics ; on ne prétend plus qu’ils sont introuvables.
- Pipeline : test puis uv build et publication PyPI OIDC ; le fait qu’il exécute des tests n’est pas une exécution locale de ces tests par nous. Pas de build reproductible complet certifié.
- Snapshot GitHub : dépôt non archivé, quatre commits retournés, trois tags, dernier push le **21 avril2026 à12:47:26 Europe/Paris** ; aucune activité ultérieure visible dans ce snapshot. Release PyPI unique visible. Cela ne prouve pas que le projet est abandonné, mais ne prouve pas non plus une maintenance suivie.
- Source lue statiquement, **pas installée ni exécutée**. Les vérifications cryptographiques n’exécutent pas la bibliothèque. Licence/provenance ne sont pas une garantie de sûreté du code. Preuves : round5-evidence/candidate-*.json et candidate-attestation-*.log.

## Contrats encore à établir avant une adoption

1. **Session HA** : le SDK annote `httpx.AsyncClient`, accepte ce client et ne le ferme pas s’il est injecté. HA2025.12 fournit httpx ; HA2026.11 fournit **httpx2** dans `helpers/httpx_client.py`. Un usage structurel pourrait fonctionner, mais la compatibilité de type et de contrat n’est pas démontrée. Ne pas changer ou fermer un client partagé, ni contourner le problème avec une session indépendante pour revendiquer inject-websession.
2. **Confidentialité** : send utilise GET par défaut, clés/user/message dans la query ; HTTPX peut logger les URL au niveau INFO. Le SDK propose POST form-data, sans secrets en query dans sa source, mais il faut prouver le contrat fournisseur pour Unicode et erreurs sans supposer qu’un mock valide Free. Les témoignages publics POST (formulaire/JSON) sont contradictoires ; aucune sonde sur smsapi.free-mobile.fr n’a été faite. La configuration Pydantic contient password en str, et repr du client contient user : ne jamais logger ces objets.
3. **Configuration explicite** : neutraliser `.env`/variables d’environnement pour user/clé/endpoint et imposer l’URL HTTPS attendue. Ne pas laisser une configuration système rediriger des secrets. Le SDK ajoute aussi pydantic-settings et typer ; pins/graphe des deux HA restent à valider.
4. **Timeout et annulation** : send ne propose pas d’options par requête. Une borne totale opérationnelle async (retry inclus), l’annulation et la réutilisation de session doivent être testées sans mutation globale. Un timeout ne prouve jamais que le fournisseur n’a pas déjà accepté le message ; ne pas ajouter de retry réseau automatique.
5. **Adaptateur d’erreurs** : préserver200/400/402/403/500/inconnue, 403→reauth, quota, validation pré-I/O, événements et disponibilité. Le SDK lève des exceptions402/403/500 et retourne un objet pour400/inconnue : pas équivalence automatique avec FreeResponse. Tests HTTP locaux contractuels sur tous chemins nécessaires avant adoption.
6. **Maintenance/type** : version publiée cohérente avec tag, contrat HA HTTPX/httpx2 assumé et maintenance acceptée ; pas de py.typed dans la wheel examinée. Aucun upstream modifié ou contacté. Choisir cette dépendance malgré ces réserves nécessite une décision de mainteneur ; ce n’est pas une incapacité absolue à écrire un adaptateur.

Cette passe clôt donc l’étude de provenance, **pas** la migration transport. Refaire la même recherche sans changement amont/décision produit n’apporterait pas la preuve manquante. Les critères async-dependency/inject-websession et strict-typing restent ouverts.

## Dépendance actuelle et transparence

Les preuves round4 de freesms0.3 restent valables : source identique au tag public c19342f, wheel ET sdist attestés cryptographiquement via pipeline public MIT. Un pin exact0.3 a été rejeté par hassfest, car le core free_mobile des deux HA exige0.2 ; il n’est pas réintroduit. Plage>=0.2 conservée, sans changer de validateur ni autre dépôt. 0.2/0.3 restent exercés en runtime ; 0.2 via overlay, pas nouveau lock complet. Typage strict local11modules dans la venv0.3, pas typage complet de l’amont0.2/0.3. Transparence de toute la plage/pin compatible encore non établie.

## Setup et disponibilité : applicabilité distincte

L’AST des deux SDK supportés confirme : FreeClient n’offre que constructeur/send_sms. Aucun contrôle authentifié sans effet de bord n’est fourni. L’exception officielle **test-before-setup** couvre le cas où l’intégration ne peut vérifier sa configuration pendant le setup : autoévaluation **exempt**, justification documentée, pas SMS automatique ni exemption officielle accordée. **test-before-configure reste todo** : la règle ne propose pas la même exception explicite et l’utilisateur peut désactiver le SMS de validation. Ne pas supprimer cette option pour gagner un point.

Disponibilité : le statut devient unavailable après panne de transport observée, récupération par action explicite ; réponse HTTP même en erreur rétablit joignabilité, pas livraison. Compteurs historiques restent valides, commandes restent utilisables pour réessayer. Pas de SMS/probe au setup, polling, disponibilité online inventée ou retry réseau caché. entity-unavailable reste partiel/todo : politique write-only à faire accepter en revue, pas commande rendue irrécupérable artificiellement.

Sources officielles relues : [test-before-setup](https://contributors.home-assistant.io/core/quality-scale/test-before-setup/), [test-before-configure](https://contributors.home-assistant.io/core/quality-scale/test-before-configure/), [entity-unavailable](https://contributors.home-assistant.io/core/quality-scale/entity-unavailable/), [async-dependency](https://contributors.home-assistant.io/core/quality-scale/async-dependency/), [inject-websession](https://contributors.home-assistant.io/core/quality-scale/inject-websession/).


## Complément borné round6 — décision finale inchangée

Aucune nouvelle recherche/adoption du candidat incohérent. Les preuves rounds4/5 sont conservées. Le transport reste synchronisé dans executor ; un thread déjà parti peut continuer après annulation, donc un faux timeout asyncio total pourrait favoriser un envoi doublé. Ne pas le présenter comme correction fiable.

Vérification ciblée supplémentaire freesms0.2 : tag0.2.0/commit **f422cbfbd1fd96b9cd79021da21c7114fbff7e69**, licence MIT. Source wheel/sdist et overlay runtime identique octet pour octet à ce tag (SHA source78921e03f683e4de9224bcda4f83964300535f955a9091dd9828fd179f7053a5). Artefacts PyPI vérifiés contre leurs SHA256 ; workflow du tag .github/workflows/python.yml construit, teste et vérifie le packaging, mais ne contient pas de publication PyPI. Les deux endpoints de provenance retournent404 : ce n’est **pas** une preuve de publication manuelle, seulement une chaîne publique de publication toujours non établie. Preuves complètes round6-evidence/freesms02-source-verification.json et fichiers source/metadata/workflow/licence associés. Ce complément remplace « 0.2 non vérifié » par une limite précise, sans cocher dependency-transparency.

Aucun pin exact imposé ni core modifié. La plage>=0.2 conserve la coexistence avec le pin core0.2 ; preuve0.3 ne prouve pas toute la plage ni publication future. Reprendre seulement après une décision explicite de dépendance ou une nouvelle version amont cohérente répondant au contrat de session/typing/sécurité ; pas une nouvelle archive parce que la même recherche a été relancée.

La matrice runtime des deux HA et deux SDK est testée localement, avec garde HTTP globale. Elle ne garantit pas qu’un résolveur installe toutes combinaisons possibles d’intégrations, ni le service Free réel. Les sept actions restantes, dont limites de typage statique historique, sont fermement délimitées dans REMAINING_ACTIONS.md. Aucun niveau officiel.


## Round7 — pas de nouvelle recherche ni remplacement

Décision transport inchangée, preuves historiques réutilisées. Dette statique locale3→0sur HA2025 et0sur HA2026, mypy installé dans les deux environnements ; SDK toujours non pleinement typé, strict-typing officiel encore todo. Le correctif de schéma/stockage ne change aucun appel Free, timeout/retry ni session. Voir REMAINING_ACTIONS.md et SECURITY_REVIEW.md pour décision de fin de périmètre et risques GET/annulation/cache avant diffusion. Les descriptions de trois diagnostics historiques plus haut sont des constats round6 désormais résolus localement.
