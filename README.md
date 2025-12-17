# 🐾 WhatsApp Wellbeing Bot — by SlyCo0p3r

**Mathieu le Chat**, le petit assistant automatisé qui veille sur vous 🐱💬  
Ce bot envoie chaque jour un message de vérification WhatsApp.  
Si aucune réponse n'est reçue dans un délai défini (ex: 2h), il alerte automatiquement les contacts de sécurité désignés.

> ⚙️ Auto-hébergé sur Unraid, fonctionnant avec la WhatsApp Cloud API et un simple conteneur Docker.

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Python](https://img.shields.io/badge/python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

---

## 🚀 Fonctionnalités

- 📅 **Envoi quotidien** d'un message de vérification ("ping") à une heure configurable
- ⏰ **Délai de réponse configurable** avant envoi d'alerte (par défaut 120 minutes)
- ⚠️ **Envoi automatique** d'un message aux contacts de sécurité en cas d'absence de réponse
- 🐾 **Identité "Mathieu le Chat"** pour rendre les messages plus humains et bienveillants
- 🔒 **100% auto-hébergé**, aucune donnée partagée avec un service externe
- 🛡️ **Sécurité renforcée** : CORS configurable, validation webhook robuste, gestion d'erreurs avancée
- 🔄 **Robustesse** : Gestion automatique des états corrompus, prévention des alertes multiples, validation des données
- 🚀 **Production-ready** : Support Gunicorn, validation de configuration au démarrage, logging configurable
- 📊 **Widget de statut** : Affichage en temps réel de l'état du bot sur votre site web

---

## 🧠 Exemple de messages

### Message quotidien (`mc_daily_ping`)
> Bonjour 🐾 je suis "Mathieu le Chat", le petit assistant automatisé de Sly.  
> C'est l'heure de ta vérification quotidienne ! Peux-tu répondre à ce message pour me dire que tout va bien ? 💛

### Message d'alerte (`mc_safety_alert`)
> Bonjour 🐾 je suis "Mathieu le Chat", le petit assistant automatisé de Sly.  
> Je t'envoie ce message car Sly n'a pas répondu à sa vérification de sécurité habituelle 🕒  
> Il t'a désigné comme contact de sécurité — peux-tu vérifier que tout va bien auprès de lui ? 🙏

### Message de confirmation (`mc_ok`)
> Merci pour ta réponse ! Tout est en ordre 🐾💛

---

## 🧰 Installation

### Prérequis

- Docker et Docker Compose installés
- Un compte Meta Developer avec accès à WhatsApp Cloud API
- Un reverse proxy (Nginx, Traefik, etc.) pour exposer le webhook en HTTPS

### 1. Cloner le dépôt

```bash
git clone https://github.com/SlyCo0p3r/whatsapp-wellbeing-bot.git
cd whatsapp-wellbeing-bot
```

### 2. Créer un fichier `.env` basé sur `.env.example`

```bash
cp .env.example .env
nano .env
```

Remplis les champs obligatoires :

* `WHATSAPP_TOKEN` - Token d'accès permanent depuis Meta Developer Dashboard
* `WHATSAPP_PHONE_ID` - ID du numéro WhatsApp Cloud
* `WEBHOOK_VERIFY_TOKEN` - Token de vérification pour le webhook (choisissez une valeur sécurisée)
* `OWNER_PHONE` - Votre numéro WhatsApp au format E.164 (ex: `+33612345678`)
* `ALERT_PHONES` - Numéros des contacts de sécurité, séparés par des virgules

Ces informations proviennent de votre **application WhatsApp Cloud API** dans le [Meta Developer Dashboard](https://developers.facebook.com/).

### 3. Créer les templates WhatsApp

Dans Meta Business Suite, créez les templates suivants :

- `mc_daily_ping` - Message de vérification quotidienne
- `mc_safety_alert` - Message d'alerte aux contacts de sécurité
- `mc_ok` - Message de confirmation

### 4. Lancer avec Docker Compose

```bash
docker compose up -d
```

Le bot écoute sur le port défini (par défaut `5090`).  
Assurez-vous que votre webhook WhatsApp pointe vers :  
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
⚠️ **Sécurité** : Les endpoints de debug sont **désactivés par défaut**. Pour les activer, définissez `ENABLE_DEBUG=true` dans votre `.env`. Il est également recommandé de définir un `DEBUG_TOKEN` pour protéger ces endpoints.

```bash
# Activer les endpoints de debug dans .env
ENABLE_DEBUG=true
DEBUG_TOKEN=your-secret-token-here

# Forcer un ping de test (sans attendre l'heure configurée)
curl -H "X-Debug-Token: your-secret-token-here" http://IP-DE-VOTRE-NAS:5090/debug/ping
# Ou avec query param
curl "http://IP-DE-VOTRE-NAS:5090/debug/ping?token=your-secret-token-here"

# Voir l'état actuel du bot
curl -H "X-Debug-Token: your-secret-token-here" http://IP-DE-VOTRE-NAS:5090/debug/state
```
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

# Vérifier la configuration
docker exec whatsapp-wellbeing-bot python -c "from app import validate_config; validate_config()"
```

**Erreurs courantes :**

- `❌ WHATSAPP_TOKEN manquant` → Vérifiez votre fichier `.env`
- `❌ DAILY_HOUR invalide` → Doit être entre 0 et 23
- `❌ RESPONSE_TIMEOUT_MIN invalide` → Doit être > 0
- `Permission denied` → Le dossier `data/` doit être accessible en écriture
- `❌ TZ invalide` → Vérifiez le format du timezone (ex: `Europe/Paris`)

### Les messages ne sont pas envoyés

**Vérifiez l'API WhatsApp :**

```bash
# Tester manuellement l'envoi
curl http://IP-DE-VOTRE-NAS:5090/debug/ping
```

**Codes d'erreur courants :**

- `❌ WhatsApp API erreur 401` → Votre `WHATSAPP_TOKEN` a expiré, régénérez-le sur Meta Developer Dashboard
- `❌ WhatsApp API erreur 429` → Rate limit atteint, le bot attendra automatiquement avant de réessayer
- `❌ WhatsApp API erreur 131030` → Le template n'existe pas, créez-le dans Meta Business Suite
- `❌ WhatsApp API erreur 5xx` → Erreur serveur Meta, le bot réessayera automatiquement avec backoff exponentiel

### Le webhook ne reçoit rien

**Testez que le webhook est accessible :**

```bash
curl https://votre-domaine.com/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=VOTRE_TOKEN&hub.challenge=test
```

**Réponse attendue :** `test`

**Si ça ne marche pas :**

1. Vérifiez votre reverse proxy (Nginx Proxy Manager, Traefik, etc.)
2. Vérifiez que le port 5090 est bien mappé dans `docker-compose.yml`
3. Vérifiez les logs du reverse proxy
4. Vérifiez que le `WEBHOOK_VERIFY_TOKEN` correspond dans `.env` et dans la configuration Meta

### Reconstruire le conteneur après modification

```bash
cd /mnt/user/appdata/whatsapp-wellbeing-bot
docker compose down
docker compose build --no-cache
docker compose up -d
docker logs -f whatsapp-wellbeing-bot
```

### Réinitialiser l'état du bot

Si le bot est bloqué dans un état bizarre :

```bash
# Arrêter le conteneur
docker compose down

# Supprimer le state.json (le bot le recréera automatiquement)
rm /mnt/user/appdata/whatsapp-wellbeing-bot/data/state.json

# Redémarrer
docker compose up -d
```

Le bot gère automatiquement les états corrompus et crée un backup du fichier si nécessaire.

---

## 🌐 Widget de statut pour WordPress

Le bot expose un widget HTML qui affiche l'état du bot en temps réel.

### Accès au widget

```
https://votre-domaine.com/widget
```

### Intégration WordPress

**Dans un widget HTML personnalisé :**

```html
<iframe 
    src="https://votre-domaine.com/widget" 
    width="320" 
    height="240" 
    frameborder="0"
    style="border: none; border-radius: 16px; display: block; margin: 0 auto;">
</iframe>
```

**Ou via shortcode** (dans `functions.php`) :

```php
function mathieu_status_widget() {
    return '<iframe src="https://votre-domaine.com/widget" width="320" height="240" frameborder="0" style="border: none; border-radius: 16px;"></iframe>';
}
add_shortcode('mathieu_status', 'mathieu_status_widget');
```

Puis utilisez `[mathieu_status]` dans vos pages.

**Le widget affiche :**

- 🟢 **Actif** - Le bot fonctionne normalement
- 🟡 **En attente** - Un ping a été envoyé, attend la réponse
- 🔴 **Hors ligne** - Le bot ne répond pas

Mise à jour automatique toutes les 30 secondes.

**Note :** Configurez `CORS_ORIGINS` dans votre `.env` avec votre domaine pour autoriser le widget.

---

## 🔧 Structure du projet

```
whatsapp-wellbeing-bot/
│
├── app.py                 # Code principal du bot
├── logging_config.py      # Configuration du logging
├── requirements.txt       # Dépendances Python
├── Dockerfile             # Image Docker
├── docker-compose.yml     # Déploiement du conteneur
├── .env.example           # Exemple de configuration
├── .gitignore             # Fichiers à ne pas pousser
└── README.md              # Ce fichier !
```

---

## 🧩 Variables d'environnement

| Variable               | Description                       | Exemple                     | Obligatoire |
| ---------------------- | --------------------------------- | --------------------------- | ----------- |
| `WHATSAPP_TOKEN`       | Token d'accès permanent Meta      | `EAAB...ZDZD`               | ✅ Oui      |
| `WHATSAPP_PHONE_ID`    | ID du numéro WhatsApp Cloud       | `908888888888889`           | ✅ Oui      |
| `WEBHOOK_VERIFY_TOKEN` | Token de vérification du webhook  | `margdadan-verify`          | ✅ Oui      |
| `OWNER_PHONE`          | Ton numéro WhatsApp personnel     | `+33612345678`              | ✅ Oui      |
| `ALERT_PHONES`         | Numéros d'urgence à prévenir      | `+33611111111,+33622222222` | ⚠️ Recommandé |
| `DAILY_HOUR`           | Heure du message quotidien (0–23) | `9`                         | ❌ Non (défaut: 9) |
| `RESPONSE_TIMEOUT_MIN` | Délai avant alerte (min)          | `120`                       | ❌ Non (défaut: 120) |
| `TZ`                   | Timezone                          | `Europe/Paris`              | ❌ Non (défaut: Europe/Paris) |
| `CORS_ORIGINS`         | Origines autorisées pour CORS     | `http://localhost,https://votre-domaine.com` | ❌ Non (défaut: localhost) |
| `USE_GUNICORN`         | Utiliser Gunicorn en production   | `true` / `false`            | ❌ Non (défaut: false) |
| `LOG_LEVEL`            | Niveau de log (INFO, DEBUG, etc.) | `INFO`                      | ❌ Non      |
| `LOG_FILE`             | Fichier de log (optionnel)        | `/app/data/bot.log`         | ❌ Non      |
| `LOG_JSON`             | Format JSON pour les logs         | `false` / `true`            | ❌ Non      |
| `ENABLE_DEBUG`         | Activer les endpoints de debug    | `true` / `false`            | ❌ Non (défaut: false) |
| `DEBUG_TOKEN`          | Token pour protéger les endpoints de debug | `your-secret-token` | ❌ Non (optionnel) |

### Configuration recommandée pour la production

```bash
# Production
USE_GUNICORN=true
CORS_ORIGINS=https://votre-domaine.com
LOG_LEVEL=INFO
LOG_FILE=/app/data/bot.log
```

---

## 🛡️ Sécurité et bonnes pratiques

### Sécurité

* Le fichier `.env` **ne doit jamais être pushé** sur GitHub (déjà dans `.gitignore`)
* Utilisez des **tokens longue durée** Meta, ou régénérez-les régulièrement
* Pour les tests, préférez le **numéro de test WhatsApp Cloud API** avant votre vrai numéro
* **En production**, définissez `USE_GUNICORN=true` pour utiliser Gunicorn au lieu du serveur Flask de développement
* Configurez `CORS_ORIGINS` avec vos domaines réels en production pour limiter l'accès au widget
* Utilisez un `WEBHOOK_VERIFY_TOKEN` fort et unique
* **Les endpoints de debug sont désactivés par défaut** - activez-les uniquement en développement avec `ENABLE_DEBUG=true` et protégez-les avec `DEBUG_TOKEN`
* Limite de taille des requêtes (16 MB max) pour prévenir les attaques DoS

### Robustesse

* Le bot valide automatiquement la configuration au démarrage et affiche des warnings pour les configurations non optimales
* Gestion automatique des états corrompus avec backup et restauration
* Prévention des alertes multiples grâce au flag `alert_sent`
* Retry automatique avec backoff exponentiel pour les erreurs temporaires
* Gestion spécifique des erreurs API (rate limiting, token expiré, etc.)
* Conversion sécurisée des variables d'environnement avec valeurs par défaut
* Vérification du démarrage du scheduler avec gestion d'erreurs
* Shutdown propre du scheduler lors de l'arrêt de l'application
* Parsing JSON sécurisé dans les appels API
* Limite de taille des requêtes pour prévenir les attaques DoS

### Performance

* Le bot utilise un `StateManager` thread-safe pour gérer l'état
* Validation et normalisation automatique des données
* Logging configurable (JSON ou texte, niveau ajustable)

---

## 🔄 Améliorations récentes

### Version actuelle

- ✅ **Sécurité CORS** : Configuration des origines autorisées
- ✅ **StateManager** : Gestion d'état thread-safe avec validation
- ✅ **Gestion d'erreurs avancée** : Rate limiting, backoff exponentiel, codes HTTP spécifiques
- ✅ **Validation de configuration** : Vérification au démarrage avec messages clairs
- ✅ **Prévention alertes multiples** : Flag `alert_sent` pour éviter les doublons
- ✅ **Gestion états corrompus** : Backup automatique et restauration
- ✅ **Support Gunicorn** : Prêt pour la production
- ✅ **Logging amélioré** : Support JSON, fichiers de log, niveaux configurables
- ✅ **Sécurité renforcée** : Protection des endpoints de debug, limite de taille des requêtes
- ✅ **Robustesse améliorée** : Conversion sécurisée des variables d'environnement, vérification du scheduler, shutdown propre
- ✅ **Parsing JSON sécurisé** : Gestion d'erreurs pour les réponses API malformées

---

## 📚 API Endpoints

### Webhooks

- `GET /whatsapp/webhook` - Vérification du webhook (Meta)
- `POST /whatsapp/webhook` - Réception des messages WhatsApp

### Santé et monitoring

- `GET /health` - État de santé du bot
- `GET /debug/state` - État actuel du bot (debug)
- `GET /debug/ping` - Forcer un ping de test (debug)

### Widget

- `GET /widget` - Widget HTML de statut en temps réel

---

## ❤️ Crédits & remerciements

Créé par [**SlyCo0p3r**](https://github.com/SlyCo0p3r)  
Inspiré par une idée simple : qu'un bot puisse veiller sur ceux qu'on aime, avec tendresse et automatisation.

> "La bienveillance n'a pas besoin d'être compliquée — parfois, un message suffit." 💛

---

## 🐾 Licence

Ce projet est distribué sous licence **MIT**.  
Tu es libre de le modifier, l'améliorer ou le partager, à condition d'en citer l'auteur.

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

## 📝 Changelog

### Version actuelle

- Amélioration de la gestion des erreurs API WhatsApp
- Ajout du StateManager pour une gestion d'état robuste
- Support Gunicorn pour la production
- Validation de configuration au démarrage
- Prévention des alertes multiples
- Gestion automatique des états corrompus
