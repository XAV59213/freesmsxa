Free Mobile SMS XA pour Home Assistant

Free Mobile SMS XA est une intégration personnalisée pour Home Assistant qui permet d'envoyer des notifications SMS via le service Free Mobile. Chaque ligne téléphonique configurée crée un appareil, un service de notification (par exemple, notify.papa), et une entité capteur pour surveiller l'état de l'API.

✨ Fonctionnalités

📱 Notifications SMS : Envoyez des SMS via l'API Free Mobile depuis Home Assistant.
🔄 Multi-lignes : Configurez plusieurs lignes téléphoniques avec des noms personnalisés.
🔔 Services de notification : Chaque ligne génère un service notify (par exemple, notify.papa).
📊 Capteurs d'état : Suivez l'état de l'API, la date du dernier envoi, et le nombre total de SMS envoyés.
✅ Validation automatique : Un SMS de test est envoyé lors de la configuration pour vérifier les identifiants.
🌐 Intégration HACS : Installation facile via HACS ou manuellement.


📋 Prérequis

Home Assistant version 2023.6.0 ou supérieure.
Bibliothèque Python freesms>=0.2.1 installée dans l'environnement de Home Assistant :pip install freesms>=0.2.1




🛠️ Installation
Option 1 : Via HACS (recommandé)

Ajoutez ce dépôt comme dépôt personnalisé dans HACS :
Allez à HACS > Intégrations > Menu (⁝) > Dépôts personnalisés.
URL : https://github.com/xav59213/freesmsxa.
Catégorie : Intégration.


Recherchez "Free Mobile SMS XA" dans HACS et installez-le.
Redémarrez Home Assistant.

Option 2 : Installation manuelle

Copiez le dossier custom_components/freesmsxa dans le répertoire <votre dossier Home Assistant>/config/custom_components/.
Redémarrez Home Assistant.

Ajout d'une ligne téléphonique

Accédez à Paramètres > Appareils et services > Ajouter une intégration.
Recherchez Free Mobile SMS XA.
Entrez :
Nom d'utilisateur : Votre identifiant Free Mobile (par exemple, 12345678).
Clé API : Votre jeton d'accès API SMS (trouvable dans votre espace client Free Mobile).
Nom du service (optionnel) : Un nom personnalisé pour le service (par exemple, papa).


Validez. Un SMS de test sera envoyé pour confirmer les identifiants.
Répétez pour ajouter d'autres lignes si nécessaire.


Note : Chaque ligne crée un appareil, un service de notification (notify.nom_du_service), et une entité capteur (sensor.freesmsxa_identifiant).


⚙️ Configuration
L'intégration est configurée via l'interface utilisateur de Home Assistant. Chaque ligne téléphonique ajoutée génère :

Un appareil (par exemple, "Free Mobile SMS (12345678)") visible dans Paramètres > Appareils et services.
Un service de notification de type notify (par exemple, notify.papa si le nom est papa, ou notify.freesmsxa_12345678 par défaut).
Une entité capteur (par exemple, sensor.freesmsxa_12345678) pour surveiller l'état de l'API.

Exemple de configuration
Lors de l'ajout via l'interface, entrez :
username: votre_identifiant_free_mobile
access_token: votre_token_api_sms
name: papa  # (facultatif) nom personnalisé du service


username : Identifiant Free Mobile (par exemple, 12345678).
access_token : Jeton d’accès API SMS (espace client Free Mobile).
name : Nom personnalisé pour le service (ex. : papa). Les espaces et caractères spéciaux sont convertis (ex. : "Mon Téléphone" → mon_telephone).


Note : Un SMS de test est envoyé pour valider les identifiants.


📤 Utilisation
Envoyer un SMS
Utilisez le service de notification dans une automatisation, un script, ou l'outil de développement. Exemple :
service: notify.papa
data:
  message: "Notification de test depuis Home Assistant"

Vérifier l'état via le capteur
Chaque ligne crée une entité capteur pour suivre l'état de l'API. Exemple :
entity_id: sensor.freesmsxa_12345678
attributes:
  last_sent: "2025-05-01T12:00:00"
  sms_count: 5
  username: 12345678
  service_name: papa
  service_type: notify

Exemple d'automatisation
Envoyer un SMS toutes les heures pour tester :
automation:
  - alias: Envoyer SMS Free Mobile Test
    description: Envoie un SMS via notify.papa toutes les heures
    trigger:
      - platform: time_pattern
        hours: "/1"
        minutes: "00"
    condition: []
    action:
      - service: notify.papa
        data:
          message: "Test de notification à {{ now().strftime('%H:%M') }}"
    mode: single


📦 Dépendances

Bibliothèque Python freesms>=0.2.1 :pip install freesms>=0.2.1




📄 Licence
Ce projet est distribué sous la licence GNU LGPL v2.1. Consultez le fichier LICENSE pour plus de détails.

🤝 Contribution
Les contributions sont les bienvenues ! Pour contribuer :

Forkez le dépôt : Cliquez sur "Fork" sur GitHub.
Créez une branche : git checkout -b feature/ma-fonctionnalite.
Commitez vos changements : git commit -m "Ajout de ma fonctionnalité".
Poussez votre branche : git push origin feature/ma-fonctionnalite.
Ouvrez une Pull Request : Incluez une description claire de vos changements.

Veuillez respecter les conventions de codage de Home Assistant et ajouter des tests si possible. Pour signaler un bug ou proposer une fonctionnalité, ouvrez une issue en utilisant le modèle fourni.

❓ FAQ
Pourquoi le service notify.papa n'apparaît-il pas ?

Vérifiez les journaux avec le mode débogage activé :logger:
  default: info
  logs:
    custom_components.freesmsxa: debug


Assurez-vous que le nom saisi dans le flux de configuration (name) est valide (par exemple, papa).
Vérifiez les attributs du capteur sensor.freesmsxa_<identifiant> pour confirmer service_name.

Comment vérifier si mes identifiants sont corrects ?

Un SMS de test est envoyé lors de la configuration. Si vous ne le recevez pas, vérifiez votre username et access_token dans votre espace client Free Mobile.
Consultez les journaux pour des erreurs comme Erreur : Identifiants incorrects.

Comment ajouter plusieurs lignes téléphoniques ?

Répétez le processus d'ajout dans Paramètres > Appareils et services > Ajouter une intégration. Chaque ligne crée un nouvel appareil, service, et capteur.


📚 Documentation
Pour plus de détails, consultez le dépôt GitHub.
En cas de problème, ouvrez une issue avec :

Les journaux de débogage (custom_components.freesmsxa: debug).
Une description détaillée du problème.
Votre version de Home Assistant.


⭐ Remerciements
Un grand merci à la communauté Home Assistant et à tous les contributeurs qui rendent ce projet possible !
