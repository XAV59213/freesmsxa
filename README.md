Free Mobile SMS XA pour Home Assistant

Free Mobile SMS XA est un composant personnalisé pour Home Assistant qui permet d'envoyer des notifications par SMS via le service Free Mobile. Il prend en charge plusieurs lignes téléphoniques, chacune représentée par un appareil, un service de notification (par exemple, notify.nom_du_service), et une entité capteur pour suivre l'état de l'API.

✨ Fonctionnalités

📱 Envoi de SMS : Envoyez des notifications SMS via l'API Free Mobile.
🔄 Support multi-lignes : Configurez plusieurs lignes téléphoniques avec des noms personnalisés.
🔔 Services de notification : Chaque ligne crée un service notify (par exemple, notify.papa).
📊 Capteurs d'état : Suivez le statut de l'API, la date du dernier envoi, et le nombre total de SMS envoyés.
✅ Validation automatique : Un SMS de test est envoyé lors de la configuration pour vérifier les identifiants.
🌐 Intégration HACS : Facile à installer via HACS ou manuellement.


🛠️ Installation

Téléchargez l'intégration :

Via HACS :
Ajoutez ce dépôt comme dépôt personnalisé dans HACS : https://github.com/xav59213/freesmsxa.
Recherchez et installez "Free Mobile SMS XA".


Manuellement :
Copiez le dossier custom_components/freesmsxa dans le répertoire custom_components/ de votre configuration Home Assistant.




Redémarrez Home Assistant :

Redémarrez Home Assistant pour charger l'intégration.


Ajoutez une ligne téléphonique :

Accédez à Paramètres > Appareils et services > Ajouter une intégration.
Recherchez "Free Mobile SMS XA".
Entrez votre identifiant Free Mobile, le jeton d'accès API SMS, et éventuellement un nom personnalisé pour le service (par exemple, "papa"). Un SMS de test sera envoyé pour valider les identifiants.
Répétez pour ajouter d’autres lignes si nécessaire.




⚙️ Configuration
Chaque ligne téléphonique configurée crée :

Un appareil dans Home Assistant (par exemple, "Free Mobile SMS (12345678)").
Un service de notification de type notify (par exemple, notify.papa ou notify.freesmsxa_12345678 si aucun nom n'est spécifié).
Une entité capteur (par exemple, sensor.freesmsxa_12345678) pour suivre l'état de l'API.

Exemple de configuration
Lors de l'ajout via l'interface, entrez les informations suivantes :
username: votre_identifiant_free_mobile
access_token: votre_token_api_sms
name: papa  # (facultatif) nom personnalisé du service


username : Votre identifiant Free Mobile (par exemple, 12345678).
access_token : Votre jeton d’accès API SMS, disponible dans votre espace client Free Mobile.
name (optionnel) : Un nom personnalisé pour le service de notification (ex. : "Papa"). Les espaces et caractères spéciaux sont convertis (ex. : "Mon Téléphone" devient mon_telephone).


Note : Un SMS de test est envoyé lors de la configuration pour valider les identifiants.


📤 Utilisation
Envoyer un SMS
Utilisez le service de notification dans une automatisation ou un script. Exemple :
service: notify.papa
data:
  message: "Notification de test depuis Home Assistant"

Vérifier l'état via le capteur
Chaque ligne téléphonique crée une entité capteur pour suivre l'état de l'API. Exemple :
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

Bibliothèque Python freesms version ≥ 0.2.1

Assurez-vous que la bibliothèque est installée dans votre environnement Home Assistant :
pip install freesms>=0.2.1


📄 Licence
Ce projet est distribué sous la licence GNU LGPL v2.1. Consultez le fichier LICENSE pour plus de détails.

🤝 Contribution
Les contributions sont les bienvenues ! Pour contribuer :

Forkez le dépôt.
Créez une branche pour vos modifications (git checkout -b feature/ma-fonctionnalite).
Commitez vos changements (git commit -m "Ajout de ma fonctionnalité").
Poussez votre branche (git push origin feature/ma-fonctionnalite).
Ouvrez une Pull Request.

Veuillez respecter les conventions de codage de Home Assistant et inclure des tests si possible.

📚 Documentation
Pour plus de détails, consultez le dépôt GitHub.
Si vous rencontrez des problèmes, ouvrez une issue sur GitHub avec les journaux de débogage activés :
logger:
  default: info
  logs:
    custom_components.freesmsxa: debug


⭐ Remerciements
Merci à la communauté Home Assistant et aux contributeurs pour leur soutien !
