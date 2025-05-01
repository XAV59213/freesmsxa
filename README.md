Free Mobile SMS XA pour Home Assistant
Free Mobile SMS XA est un composant personnalisé pour Home Assistant permettant d’envoyer des notifications par SMS via le service Free Mobile. Il prend en charge plusieurs lignes téléphoniques, avec des noms de services personnalisés et des capteurs de statut.
🛠️ Installation

Copiez le dossier custom_components/freesmsxa dans le répertoire custom_components/ de votre configuration Home Assistant.
Redémarrez Home Assistant.
Accédez à Paramètres > Appareils et services > Ajouter une intégration, puis recherchez "Free Mobile SMS XA".
Entrez votre identifiant Free Mobile, le jeton d'accès API SMS, et éventuellement un nom personnalisé pour le service de notification. Un SMS de test sera envoyé pour valider les identifiants.
Répétez l’opération pour ajouter d’autres lignes téléphoniques si nécessaire.

⚙️ Configuration
Un SMS de test est envoyé lors de la configuration pour valider les identifiants. Exemple de configuration :
username: votre_identifiant_free_mobile
access_token: votre_token_api_sms
name: mon_telephone  # (facultatif) nom personnalisé du service


username : Votre identifiant Free Mobile.
access_token : Votre jeton d’accès API pour les SMS (trouvable dans votre espace client Free Mobile).
name (optionnel) : Un nom personnalisé pour le service de notification (ex. : "Mon Téléphone"). Les espaces et caractères spéciaux sont automatiquement convertis (ex. : "Mon Téléphone" devient mon_telephone).

Chaque ligne téléphonique configurée génère :

Un service de notification : notify.mon_telephone ou notify.freesmsxa_12345678.
Une entité capteur : sensor.freesmsxa_12345678, affichant le statut de l’API, la date du dernier envoi et le nombre total de SMS envoyés.

📤 Utilisation
Utilisez le service dans une automatisation ou un script, par exemple :
service: notify.mon_telephone
data:
  message: "Notification de test depuis Home Assistant"

Vérifiez le capteur pour consulter le statut de l’API et d’autres attributs :
entity_id: sensor.freesmsxa_12345678
attributes:
  last_sent: "2025-05-01T12:00:00"
  sms_count: 5
  username: 12345678
  service_name: mon_telephone

📦 Dépendances

Bibliothèque Python freesms version ≥ 0.2.1

📄 Licence
Distribué sous licence GNU LGPL v2.1
📚 Documentation
Pour plus de détails, consultez le dépôt GitHub.
