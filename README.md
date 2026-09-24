# 📨 Free Mobile SMS XA – Intégration Home Assistant

![Logo](./images/logo.png)

[![GitHub release](https://img.shields.io/github/v/release/XAV59213/freesmsxa)](https://github.com/XAV59213/freesmsxa/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?logo=home-assistant)](https://hacs.xyz/)
[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](./LICENSE)

<a href="https://www.buymeacoffee.com/xav59213"> <img src="https://img.buymeacoffee.com/button-api/?text=xav59213&emoji=&slug=xav59213&button_colour=5F7FFF&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00" />

**Free Mobile SMS XA** est une intégration personnalisée pour [Home Assistant](https://www.home-assistant.io/) qui permet d’envoyer des notifications **par SMS** via l’API gratuite de Free Mobile. Elle prend en charge plusieurs lignes, crée des entités (capteurs, boutons, `notify`) et offre une interface complète dans Lovelace.

---

## 🔧 Fonctionnalités

- 🔔 Envoi de SMS via l’entité `notify.<nom>`
- 👥 Support **multi-utilisateurs** (ex : `Papa`, `Maman`)
- 📊 Capteur de **statut enrichi** : nombre total de SMS, date du dernier envoi, journal (conservé après redémarrage)
- 🔘 Bouton test SMS personnalisable (options de l’intégration)
- 🧹 Historique des 10 derniers messages
- 📱 Carte dashboard pour écrire et envoyer un SMS
- 🔁 Reconfiguration de la clé API sans supprimer l’entrée
- 🧩 Intégration via l’interface graphique Home Assistant

---

## 📸 Aperçu

### 🛠 Interface de configuration

![Configuration UI](./images/Capture%20d’écran%20du%202025-05-02%2011-11-45.png)

### 🧩 Services configurés

![Services configurés](./images/Capture%20d’écran%20du%202025-05-02%2011-12-06.png)

### 🔑 Interface Free Mobile (Clé API)

![Free Mobile Token](./images/token.png)

---

## ⚙️ Setup

Shortcut:  
[![](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=freesmsxa)

- Allez dans **Paramètres -> Intégrations -> Ajouter une intégration**
- Cherchez **Free Mobile SMS XA** et suivez les instructions.

---

## 🧰 Installation

### 📦 Via HACS (recommandé)

1. Ouvre **HACS > Intégrations**
2. Clique sur **les trois points > Dépôts personnalisés**
3. Ajoute :
   ```
   https://github.com/XAV59213/freesmsxa
   ```
4. Sélectionne la catégorie `Intégration`
5. Installe **Free Mobile SMS XA**
6. Redémarre Home Assistant
7. Va dans **Paramètres > Appareils et services > Ajouter une intégration**
8. Cherche `Free Mobile SMS XA` et ajoute une ligne

---

## 🔐 Obtenir tes identifiants Free Mobile

1. Connecte-toi à ton [espace abonné Free Mobile](https://mobile.free.fr/moncompte)
2. Va dans **Gérer mes options**
3. Active **Notifications par SMS**
4. Copie ton **Identifiant utilisateur** et ta **Clé API**

---

## ⚙️ Exemple d’automatisation (recommandé)

Depuis Home Assistant 2024.6, le bon appel est `notify.send_message` sur l’entité créée par l’intégration :

```yaml
alias: Alarme activée
mode: single
triggers:
  - trigger: state
    entity_id: alarm_control_panel.maison
    to: armed_away
actions:
  - action: notify.send_message
    target:
      entity_id:
        - notify.maman
        - notify.papa
    data:
      message: Alarme activée
```

### Alternative : service de l’intégration

```yaml
action: freesmsxa.send_sms
data:
  target: notify.papa
  message: Alarme activée
```

`target` accepte `papa` ou `notify.papa`.

---

## 📱 Carte dashboard — Envoyer un message

Carte utilisée sur le tableau de bord mobile : destinataire + message + bouton Envoyer.

Fichiers prêts à copier :
- [examples/helpers.yaml](./examples/helpers.yaml)
- [examples/script-envoyer-message.yaml](./examples/script-envoyer-message.yaml)
- [examples/lovelace-envoyer-message.yaml](./examples/lovelace-envoyer-message.yaml)

### 1) Créer les deux helpers

**Paramètres → Appareils et services → Entrées → Créer une entrée**

- Liste `input_select.destinataire_app` : `TOUS LE MONDE !`, `Papa`, `Maman`, …
- Texte `input_text.message_sms` : longueur max 160

### 2) Créer le script

**Automatisations et scènes → Scripts → Nouveau → YAML**  
Colle [examples/script-envoyer-message.yaml](./examples/script-envoyer-message.yaml) et adapte les `notify.*` à tes lignes.

### 3) Ajouter la carte Lovelace

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Envoyer un message
    entities:
      - entity: input_select.destinataire_app
        name: Destinataire
      - entity: input_text.message_sms
        name: Message
    state_color: true
  - show_name: true
    show_icon: true
    type: button
    name: Envoyer
    icon: mdi:send
    tap_action:
      action: call-service
      service: script.turn_on
      target:
        entity_id: script.envoyer_message_cible_app_mobile
    show_state: true
    icon_height: 60px
```

Le bouton appelle `script.envoyer_message_cible_app_mobile`. Si l’ID de ton script est différent, adapte `entity_id`.

---

## 📊 Carte Lovelace — État SMS

```yaml
type: vertical-stack
cards:
  - type: entity
    entity: sensor.free_mobile_sms_papa_etat_sms
    name: 📲 Papa - État SMS
  - type: button
    name: ✉️ Envoyer un test
    entity: button.free_mobile_sms_papa_test_sms
    tap_action:
      action: perform-action
      perform_action: button.press
      target:
        entity_id: button.free_mobile_sms_papa_test_sms
  - type: markdown
    title: 📝 Historique des SMS
    content: >
      {% set log = state_attr('sensor.free_mobile_sms_papa_etat_sms', 'sms_log') %}
      {% if log %}
      {% for item in log %}
      • **{{ item.time }}** : {{ item.message }}
      {% endfor %}
      {% else %}
      Aucun SMS envoyé.
      {% endif %}
```

Les IDs d’entités dépendent du nom que tu as donné à la ligne. Vérifie-les dans **Paramètres > Entités**.

---

## 🛡️ Sécurité

- ✅ Aucune donnée externe utilisée
- ✅ Aucune collecte de messages
- ✅ La clé API n’est plus affichée dans le nom de l’appareil
- ✅ 100 % local côté Home Assistant, envoi uniquement vers l’API Free Mobile

---

## 🧰 Licence

Distribué sous **GNU LGPL v2.1** – [Voir la licence](./LICENSE)

---

## 📚 Documentation

> Intégration créée avec ❤️ pour Home Assistant.  
> Pour toute question ou amélioration, [ouvre une issue](https://github.com/XAV59213/freesmsxa/issues).
