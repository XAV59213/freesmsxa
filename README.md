📱 Free Mobile SMS XA – Intégration Home Assistant

Free Mobile SMS XA est une intégration personnalisée pour Home Assistant permettant d’envoyer des notifications SMS via l’API Free Mobile. Elle prend en charge plusieurs lignes, crée automatiquement les services de notification et expose un capteur de suivi pour chaque ligne.
✨ Fonctionnalités

    📤 Notifications SMS via l’API Free Mobile

    📞 Multi-lignes avec noms personnalisés

    🔔 Services de notification : notify.nom_du_service

    📊 Capteurs d’état : suivi API, dernier envoi, nombre de SMS

    ✅ Validation automatique : SMS de test à la configuration

    🛠️ Installation via HACS ou manuelle

📋 Prérequis

    Home Assistant v2023.6.0+

    Python : freesms>=0.2.1
    Installation :

    pip install freesms>=0.2.1

🛠️ Installation
✅ Option 1 – Via HACS (recommandé)

    Allez dans HACS > Intégrations > Menu (⁝) > Dépôts personnalisés

    Ajoutez :

        URL : https://github.com/xav59213/freesmsxa

        Catégorie : Intégration

    Recherchez Free Mobile SMS XA et installez

    Redémarrez Home Assistant

📁 Option 2 – Manuelle

    Copiez le dossier custom_components/freesmsxa dans :
    <config>/custom_components/

    Redémarrez Home Assistant

➕ Ajouter une ligne téléphonique

    Allez dans Paramètres > Appareils et services > Ajouter une intégration

    Recherchez Free Mobile SMS XA

    Entrez :

        username : identifiant Free Mobile (ex. : 12345678)

        access_token : clé API SMS (espace client Free Mobile)

        name (optionnel) : nom du service, ex. papa

    ✅ Un SMS de test est envoyé pour valider vos identifiants

⚙️ Configuration générée automatiquement

Chaque ligne crée :

    Un appareil : Free Mobile SMS (12345678)

    Un service de notification : notify.papa ou notify.freesmsxa_12345678

    Un capteur d’état : sensor.freesmsxa_12345678

💬 Exemple de configuration (UI)

username: 12345678
access_token: votre_token_api_sms
name: papa  # optionnel

Les noms comme "Mon Téléphone" deviennent mon_telephone
📤 Utilisation
Exemple d'envoi de SMS

service: notify.papa
data:
  message: "Notification de test depuis Home Assistant"

Exemple de capteur

entity_id: sensor.freesmsxa_12345678
attributes:
  last_sent: "2025-05-01T12:00:00"
  sms_count: 5
  username: 12345678
  service_name: papa
  service_type: notify

Exemple d’automatisation

automation:
  - alias: Envoyer SMS Free Mobile Test
    trigger:
      - platform: time_pattern
        hours: "/1"
        minutes: "00"
    action:
      - service: notify.papa
        data:
          message: "Test de notification à {{ now().strftime('%H:%M') }}"

🧩 Dépendances

    Python : freesms>=0.2.1

❓ FAQ
🔸 Le service notify.papa n’apparaît pas ?

    Activez le débogage :

logger:
  default: info
  logs:
    custom_components.freesmsxa: debug

    Vérifiez le nom saisi lors de la configuration

    Consultez les attributs du capteur associé

🔸 Comment vérifier mes identifiants ?

    Un SMS de test est envoyé automatiquement

    Si vous ne le recevez pas, vérifiez :

        username et access_token dans l’espace client Free Mobile

        Les journaux pour erreurs de type : Identifiants incorrects

🔸 Ajouter plusieurs lignes ?

    Répétez le processus via Paramètres > Ajouter une intégration

🤝 Contribution

Les contributions sont bienvenues !

    Forkez le dépôt

    Créez une branche :

git checkout -b feature/ma-fonctionnalite

Commitez :

    git commit -m "Ajout de ma fonctionnalité"

    Poussez et ouvrez une Pull Request

    Merci de respecter les conventions Home Assistant
    Ajoutez des tests si possible

📄 Licence

Projet sous licence GNU LGPL v2.1
Voir le fichier LICENSE
📚 Documentation

    Dépôt GitHub : FreeSMSXA sur GitHub

    En cas de bug, ouvrez une issue avec :

        Les logs en mode debug

        La version de Home Assistant

        Une description détaillée du problème

⭐ Remerciements

Un grand merci à la communauté Home Assistant et aux contributeurs 🙌
