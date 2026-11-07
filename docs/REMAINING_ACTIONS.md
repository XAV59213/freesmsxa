# Décision de clôture — round7 local

7 novembre2026, Europe/Paris. **36 done /11 exempt /7 todo**, aucun score forcé ni niveau officiel. Les trois diagnostics de typage HA2025 du round6 ont disparu sans ignore global ni nouveau cast. Mypy est maintenant installé et exécuté dans chacun des deux environnements, pas uniquement lancé avec --python-executable depuis l’autre.

## Dette locale résolue, pas typage SDK prétendu

- Les anciens imports probatio dans TYPE_CHECKING uniquement ne constituaient PAS un fallback runtime optionnel. HA2026 installe lui-même un bridge voluptuous→probatio ; le probe natif d’entrée invalide passe déjà sur round6. Aucun dysfonctionnement UI de ce cas n’a été démontré : cette hypothèse a été vérifiée puis écartée, pas transformée en faux correctif.
- schema.py dérive la classe de schéma du PLATFORM_SCHEMA public réellement fourni par HA. Les marqueurs proviennent du même moteur et sont vérifiés callable/hashable. Les deux checkers voient les vrais types ; ni paquet absent simulé ni import ignoré.
- Migration privée : Protocol ciblé, contrôle réel du callable puis signature.bind des arguments avant mutation ; absence compat_name2025 respectée, chemin privé jamais utilisé normalement sur cet endpoint. Échec fermé traduit en cas de dérive, pas effacement silencieux du cache ni cast aveugle. Probes statiques négatifs font effectivement échouer les deux checkers sur keyword manquant et constructeur de schéma invalide.

## Sept critères restent ouverts et actions utiles

| Critère | Obstacle réel après round7 | Action / choix précis |
|---|---|---|
| brands | Règle core exige actifs/admission externe, sans exception ; vérification exhaustive round6 conservée. | Choisir HACS sans revendication core, OU projet d’admission core et approbation distincte pour toute future PR brands. Aucune nouvelle recherche requise. |
| dependency-transparency | Plage>=0.2 non épinglée ; source0.2 MIT/tag/artefacts concordants, publication CI non établie ;0.3attesté mais pin incompatible core0.2. | Provenance de publication d’une version compatible + politique de pin coordonnée amont/core. Pin0.2seul ne règle pas la preuve CI. Ne pas publier soi-même une dépendance dans ce mandat. |
| test-before-configure | Opt-out volontaire, SDK sans vérification authentifiée en lecture seule ; aucune exception write-only officielle équivalente à test-before-setup. | Recommandation : conserver opt-out et critère ouvert. Changement vers SMS obligatoire exige décision produit explicite, non donnée ici ; aucun SMS réel ou au setup autorisé. |
| entity-unavailable | Politique write-only sûre : statut indisponible après panne, compteurs locaux valides, commandes activées réessayables sans sonde. Pas d’exception officielle automatique. | Maintenir cette politique ; si objectif core, obtenir revue de règle. Ne pas bloquer les commandes pour cocher un booléen sans décider/tester une voie de reprise séparée. |
| async-dependency | Production SDK sync/executor, candidat incohérent déjà écarté. | Attendre/sélectionner un SDK asyncio maintenu et cohérent avec provenance/sécurité/contrat Free démontrés. Reprendre seulement sur preuve/version nouvelle, pas refaire la même recherche. |
| inject-websession | Pas de contrat de session HA dans le SDK actuel. | Même choix de dépendance ; contrat session native HA aux deux endpoints, non fermée/non mutée globalement, timeout/annulation et erreurs à tester. Pas wrapper executor assimilé à asyncio. |
| strict-typing | **Plus de dette locale recensée par mypy sur les deux HA** ; mais SDK0.2sans marker,0.3méthodes non annotées, pas inscription CI core. | Dépendance réellement typée avec pin compatible et, uniquement si admission core décidée, inscription .strict-typing/CI.0/12local ne prouve pas typage SDK ; Protocol/cast SDK antérieur reste frontière seulement. |

## Recommandation ferme avant diffusion

**Ne pas poursuivre une boucle de micro-correctifs pour ces sept critères.** La prochaine étape raisonnable est une revue du patch et un essai sur HA de développement sauvegardé, hors maison utilisateur et sans SMS tant qu’aucun essai réel n’est autorisé.

Choix utilisateur/mainteneur nécessaire : **livraison HACS pragmatique avec ces limites**, ou **projet de conformité core** impliquant dépendance/pin/provenance/typage et admissions externes. Je recommande la première voie tant qu’aucun SDK fiable n’est disponible, en conservant opt-out et retry explicite.

La diffusion éventuelle nécessite une autorisation séparée de publication ET de stratégie version/cache : manifest6.12.12 inchangé et Const.VERSION6.12.8 préexistant ne doivent pas être assimilés à une release prête à publier. Aucun bump/publication n’a été fait ici. Revoir notamment friendly_name, bouton neuf désactivé, métadonnées restaurées et anciens historiques. SECURITY_REVIEW.md énumère risques et limites, pas promesse d’anonymisation ou toutes versions.
