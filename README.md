# 🐾 WhatsApp Wellbeing Bot — by SlyCo0p3r

**Mathieu le Chat**, le petit assistant automatisé qui veille sur vous 🐱💬  
Ce bot envoie chaque jour un message de vérification WhatsApp.  
Si aucune réponse n’est reçue dans un délai défini (ex: 2h), il alerte automatiquement les contacts de sécurité désignés.

> ⚙️ Auto-hébergé sur Unraid, fonctionnant avec la WhatsApp Cloud API et un simple conteneur Docker.

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)
---

## 🚀 Fonctionnalités

- 📅 Envoi quotidien d’un message de vérification ("ping")
- ⏰ Délai de réponse configurable avant alerte
- ⚠️ Envoi automatique d’un message aux contacts de sécurité
- 🐾 Identité “Mathieu le Chat” pour rendre les messages plus humains
- 🔒 100% auto-hébergé, aucune donnée partagée avec un service externe

---

## 🧠 Exemple de messages

### Message quotidien (`mc_daily_check`)
> Bonjour 🐾 je suis “Mathieu le Chat”, le petit assistant automatisé de Sly.  
> C’est l’heure de ta vérification quotidienne ! Peux-tu répondre à ce message pour me dire que tout va bien ? 💛

### Message d’alerte (`mc_alert_contacts`)
> Bonjour 🐾 je suis “Mathieu le Chat”, le petit assistant automatisé de Sly.  
> Je t’envoie ce message car Sly n’a pas répondu à sa vérification de sécurité habituelle 🕒  
> Il t’a désigné comme contact de sécurité — peux-tu vérifier que tout va bien auprès de lui ? 🙏  

---

## 🧰 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/SlyCo0p3r/whatsapp-wellbeing-bot.git
cd whatsapp-wellbeing-bot
````

### 2. Créer un fichier `.env` basé sur `.env.example`

```bash
cp .env.example .env
nano .env
```

Remplis les champs :

* `WHATSAPP_TOKEN`
* `WHATSAPP_PHONE_ID`
* `OWNER_PHONE`
* `ALERT_PHONES`

Ces informations proviennent de ton **application WhatsApp Cloud API** dans le [Meta Developer Dashboard](https://developers.facebook.com/).

### 3. Lancer avec Docker Compose

```bash
docker compose up -d
```

Le bot écoute sur le port défini (par défaut `5090`)
Assure-toi que ton webhook WhatsApp pointe vers :
`https://<ton-domaine>/whatsapp/webhook`

---
## 🏥 Vérifier que le bot fonctionne

### Healthcheck automatique
Le conteneur vérifie automatiquement sa santé toutes les 30 secondes.

```bash
# Voir le statut du conteneur
docker ps

# Le statut doit afficher "healthy" au lieu de "starting"
```

### Vérification manuelle

**Depuis votre navigateur :**
```
http://IP-DE-VOTRE-NAS:5090/health
```

**Réponse attendue :**
```json
{
  "status": "ok",
  "waiting": false,
  "last_ping": "2025-11-06T09:00:00+01:00",
  "last_reply": "2025-11-06T09:15:00+01:00"
}
```

### Endpoints de debug

```bash
# Forcer un ping de test (sans attendre 9h)
curl http://IP-DE-VOTRE-NAS:5090/debug/ping

# Voir l'état actuel
curl http://IP-DE-VOTRE-NAS:5090/debug/state
```

### Logs en temps réel

```bash
# Suivre les logs du bot
docker logs -f whatsapp-wellbeing-bot

# Dernières 50 lignes
docker logs --tail 50 whatsapp-wellbeing-bot
```
---
## 🔧 Dépannage

### Le conteneur ne démarre pas

```bash
# Voir les erreurs de démarrage
docker logs whatsapp-wellbeing-bot

# Vérifier la config
docker exec whatsapp-wellbeing-bot python -c "from app import validate_config; validate_config()"
```

**Erreurs courantes :**
- `❌ WHATSAPP_TOKEN manquant` → Vérifiez votre fichier `.env`
- `Permission denied` → Le fichier `state.json` doit être accessible en écriture

---

### Les messages ne sont pas envoyés

**Vérifiez l'API WhatsApp :**
```bash
# Tester manuellement l'envoi
curl http://IP-DE-VOTRE-NAS:5090/debug/ping
```

**Si vous voyez `❌ WhatsApp API erreur 401` :**
→ Votre `WHATSAPP_TOKEN` a expiré, régénérez-le sur Meta

**Si vous voyez `❌ WhatsApp API erreur 131030` :**
→ Le template n'existe pas, créez-le dans Meta Business Suite

---

### Le webhook ne reçoit rien

**Testez que le webhook est accessible :**
```bash
curl https://votre-domaine.com/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=VOTRE_TOKEN&hub.challenge=test
```

**Réponse attendue :** `test`

**Si ça ne marche pas :**
1. Vérifiez Nginx Proxy Manager / reverse proxy
2. Vérifiez que le port 5090 est bien mappé
3. Vérifiez les logs : `docker logs nginx-proxy-manager`

---

### Reconstruire le conteneur après modification

```bash
cd /mnt/user/appdata/whatsapp-wellbeing-bot
docker compose down
docker compose build --no-cache
docker compose up -d
docker logs -f whatsapp-wellbeing-bot
```

---

### Réinitialiser l'état du bot

Si le bot est bloqué dans un état bizarre :

```bash
# Arrêter le conteneur
docker compose down

# Supprimer le state.json
rm /mnt/user/appdata/whatsapp-wellbeing-bot/state.json

# Redémarrer
docker compose up -d
```


---

## 🔧 Structure du projet

```
whatsapp-wellbeing-bot/
│
├── app.py                 # Code principal du bot
├── requirements.txt       # Dépendances Python
├── docker-compose.yml     # Déploiement du conteneur
├── .env.example           # Exemple de configuration
├── .gitignore             # Fichiers à ne pas pousser
└── README.md              # Ce fichier !
```

---

## 🧩 Variables d’environnement principales

| Variable               | Description                       | Exemple                     |
| ---------------------- | --------------------------------- | --------------------------- |
| `WHATSAPP_TOKEN`       | Token d’accès permanent Meta      | `EAAB...ZDZD`               |
| `WHATSAPP_PHONE_ID`    | ID du numéro WhatsApp Cloud       | `908888888888889`           |
| `WEBHOOK_VERIFY_TOKEN` | Token de vérification du webhook  | `margdadan-verify`          |
| `OWNER_PHONE`          | Ton numéro WhatsApp personnel     | `+33612345678`              |
| `ALERT_PHONES`         | Numéros d’urgence à prévenir      | `+33611111111,+33622222222` |
| `DAILY_HOUR`           | Heure du message quotidien (0–23) | `9`                         |
| `RESPONSE_TIMEOUT_MIN` | Délai avant alerte (min)          | `120`                       |

---

## 🛡️ Sécurité et bonnes pratiques

* Le fichier `.env` **ne doit jamais être pushé** sur GitHub.
* Utilise des **tokens longue durée** Meta, ou régénère-les régulièrement.
* Pour les tests, préfère le **numéro de test WhatsApp Cloud API** avant ton vrai numéro.

---

## ❤️ Crédits & remerciements

Créé par [**SlyCo0p3r**](https://github.com/SlyCo0p3r)
Inspiré par une idée simple : qu’un bot puisse veiller sur ceux qu’on aime, avec tendresse et automatisation.

> “La bienveillance n’a pas besoin d’être compliquée — parfois, un message suffit.” 💛

---

## 🐾 Licence

Ce projet est distribué sous licence **MIT**.
Tu es libre de le modifier, l’améliorer ou le partager, à condition d’en citer l’auteur.





