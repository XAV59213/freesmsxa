# Noms et traduction — migration locale round7

Base47eaf170614c44aadcdf1e97b22b41ed97611815, 7 novembre2026 Europe/Paris. Aucun SMS réel, HA maison ou publication.

## Contrat

- Les cinq classes ont has_entity_name=True et une translation_key ; notify utilise sms, noms « SMS » EN/FR et icône mdi:message-text. Aucun alias utilisateur injecté dans les traductions.
- Seul le registre notify historique de cette entrée (domain/platform/unique_id/config_entry_id exacts) est migré avant forwarding. Pas de recréation ni génération d’ID, pas de changement des options, données, titres, alias runtime, événements, icônes, noms explicites, zones/labels/options, masquage/désactivation ou appareil personnel name_by_user.
- Un ancien alias d’affichage non vide autre que le compte est retenu comme registry.name si aucun nom personnalisé n’existe ; les noms explicites, y compris chaîne vide ou compte choisi explicitement, restent inchangés. Une fois migrée, l’entrée registry.has_entity_name sert de marqueur : vider la personnalisation ensuite ne la réintroduit pas au prochain chargement.
- Aucun SMS/HTTP pendant migration ou setup. Tests natifs prouvent qu’une action existante notify.send_message ciblant le même entity_id fonctionne et conserve l’alias d’événement. Les autres entités n’ont pas de migration d’identité à faire.

## Confidentialité et changements visibles

Nouvelles entrées sans alias : Free Mobile SMS. DeviceInfo ne réutilise plus le compte comme défaut. Les vieux alias de données/événements, entry.title, unique_id et entity_id peuvent encore révéler le compte : préservés pour compatibilité, pas promesse d’anonymisation de HA. Aucun nom explicitement personnalisé n’est masqué arbitrairement.

L’ancien nom notify implicite égal au compte est remplacé par le nom traduit, et l’ancien nom d’appareil par défaut par Free Mobile SMS. Le nom complet peut donc changer volontairement. Les noms personnalisés stockés restent inchangés ; **les préfixes de friendly_name peuvent être recomposés par HA après un changement du nom d’appareil**. Les templates comparant du texte d’affichage ne bénéficient pas de la stabilité des IDs : revue nécessaire avant diffusion. HA2025.12 traite aussi une personnalisation vide ("") comme absence de nom et suit alors le nouveau défaut ; la valeur stockée reste vide.

## Compatibilité HA particulière

HA2026.11 stocke compat_name pour préserver certains noms complets lors de sa propre migration de registre1.24. La migration utilise maintenant **la méthode publique async_update_entity par défaut**, même sous HA2026.11, sans créer de cache compat_name. Si HA fournit une composante publique entity_name non préfixée, elle évite de recopier deux fois le préfixe appareil ; les noms explicites ne sont jamais recalculés. Un fallback implicite égal au compte, brut ou dérivé, n’est pas promu en nom personnalisé.

Le seul appel interne _async_update_entity reste isolé au cas où un compat_name **déjà non nul** doit réellement être conservé pour un nom choisi. L’API publique ne permet pas de passer ce champ et l’efface sur changement has_entity_name. Le helper public async_preserve_compat_name_as_alias ne conserve qu’un alias vocal dans certains cas, pas le friendly_name ; le substituer changerait le contrat et potentiellement des alias utilisateurs. Aucune API publique équivalente de préservation exacte du cache n’a été trouvée dans les deux endpoints inspectés. HA2025.12 ne passe jamais par le shim. Aucun fichier HA n’est modifié.

Dette explicite : ce shim dépend d’un détail interne de HA, testé aux deux endpoints seulement. Toute nouvelle version doit rejouer les tests, notamment noms complets de compatibilité, noms vides, reload et modification du nom d’appareil. Il n’y a pas de garantie inventée pour toutes les versions HA. Pas d’alias d’automation ajouté arbitrairement ni d’API privée de service distant utilisée.

## Preuves

tests/test_round5.py : vrais EntityRegistry/DeviceRegistry/EntityPlatform/StateMachine et dispatcher d’actions HA temporaires, données EN/FR réelles chargées dans le moteur de noms natif. Cas noms explicites/vide/compte, entité désactivée/masquée, icône, alias vocal, zone et label réels/options conversation, reload, opt-in après effacement, ownership, défaut privé, personnalisation appareil et compat_name HA. Les noms localisés sont lus depuis les JSON du dépôt, pas une traduction inventée pour le test. Les frontières chargement/reload restent doublées selon les tests ; pas installation complète via HACS ou navigateur.


Round6 ajoute tests de la voie publique (espion de la vraie méthode), absence de cache manufacturé, cache existant/personnalisations vides/compte explicite, anciens noms préfixés avec composante vide, fallback compte dérivé et confidentialité. Test d’intégration isolée : vrai loader HA, setup de domaine, forwarding réel notify/sensor/button, services, états, unload/reload, issue et flow de réauth natifs ; seuls client réseau et ressources UI/HTTP sont doublés. Pas serveur web ni frontend complet, encore moins maison HA ou SMS réel. Reproduction et limites de typage historique dans AUDIT.md/tests/README.md.


## Round7 — contrat privé vérifié

Le shim existant utilise maintenant un Protocol d’appel précis sans cast. Callable puis signature.bind sont vérifiés avant toute invocation ; keyword compat_name absent2025 => chemin privé non pris normalement. Une dérive simulée échoue fermée avec erreur traduite sans noms/cache dans ses placeholders. Les deux checkers sont0/12, probes négatifs réellement rejetés ; le contrat natif moderne conserve effectivement le cache et toutes identités. Cela ne transforme pas une API interne en API publique ou en garantie future.
