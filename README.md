# 📨 Free Mobile SMS XA – Intégration Home Assistant

![Logo](./images/logo.png)

[![GitHub release](https://img.shields.io/github/v/release/XAV59213/freesmsxa)](https://github.com/XAV59213/freesmsxa/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?logo=home-assistant)](https://hacs.xyz/)
[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL%20v2.1-blue.svg)](./LICENSE)

<a href="https://www.buymeacoffee.com/xav59213"> <img src="https://img.buymeacoffee.com/button-api/?text=xav59213&emoji=&slug=xav59213&button_colour=5F7FFF&font_colour=ffffff&font_family=Cookie&outline_colour=000000&coffee_colour=FFDD00" />

**Free Mobile SMS XA** est une intégration personnalisée pour [Home Assistant](https://www.home-assistant.io/) qui permet d’envoyer des notifications **par SMS** via l’API gratuite de Free Mobile. Elle prend en charge plusieurs lignes, crée des entités (capteurs, boutons, `notify`) et offre une carte Lovelace native.

---

## 🔧 Fonctionnalités

- 🔔 Envoi de SMS via `notify.<nom>` / `notify.send_message`
- 👥 Support **multi-utilisateurs** (ex : `Papa`, `Maman`)
- 📊 Capteur d’état : total, aujourd’hui, quota, dernière erreur
- 📜 Historique des **50** derniers SMS (succès et échecs), conservé après redémarrage
- 🚦 Gestion du quota Free Mobile (HTTP 402)
- 🔍 Diagnostics téléchargeables (clé API masquée) + option logs debug
- 🔘 Bouton test SMS personnalisable
- 📱 Carte Lovelace native **Envoyer un SMS** (`custom:freesmsxa-send-card`)
- 🔁 Reconfiguration de la clé API sans supprimer l’entrée

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

## 📱 Carte Lovelace native — Envoyer un SMS

Après mise à jour, **Modifier le tableau de bord → Ajouter une carte → Envoyer un SMS**.

```yaml
type: custom:freesmsxa-send-card
```

Si la carte n’apparaît pas : **Paramètres → Tableaux de bord → ⋮ → Ressources** et ajoute `/freesmsxa/freesmsxa-send-card.js` en module JavaScript, puis redémarre l’app.

Compteur 160 caractères intégré. Destinataires détectés automatiquement, option **TOUS LE MONDE !**.

---

## 📊 Historique, quota et debug

Le capteur **État SMS** expose :

- `sms_count` / `sms_today` / `quota_status` (`ok` ou `throttled`)
- `last_error` (`quota_exceeded`, `invalid_auth`, …)
- `sms_log` : 50 derniers envois (`status: sent|failed`)

Deux capteurs numériques permettent de grapher **SMS envoyés** et **SMS aujourd’hui**.

Événements : `freesmsxa_sms_sent` et `freesmsxa_sms_failed`.

**Diagnostics** : appareil Free Mobile SMS → ⋮ → Télécharger les diagnostics (la clé API est masquée).

**Logs debug** : options de l’intégration → *Activer les logs de débogage*.

```yaml
type: markdown
title: Historique des SMS
content: >
  {% set log = state_attr('sensor.free_mobile_sms_papa_etat_sms', 'sms_log') %}
  {% if log %}
  {% for item in log %}
  • **{{ item.time }}** [{{ item.status }}] {{ item.message }}
  {% endfor %}
  {% else %}
  Aucun SMS.
  {% endif %}
```

Les IDs d’entités dépendent du nom de la ligne. Vérifie-les dans **Paramètres > Entités**.

---

## 🛡️ Sécurité

- ✅ Aucune donnée externe utilisée
- ✅ La clé API n’est plus affichée dans le nom de l’appareil ni dans les diagnostics
- ✅ 100 % local côté Home Assistant, envoi uniquement vers l’API Free Mobile

---

## 🧰 Licence

Distribué sous **GNU LGPL v2.1** – [Voir la licence](./LICENSE)

---

## 📚 Documentation

> Intégration créée avec ❤️ pour Home Assistant.  
> Pour toute question ou amélioration, [ouvre une issue](https://github.com/XAV59213/freesmsxa/issues).
