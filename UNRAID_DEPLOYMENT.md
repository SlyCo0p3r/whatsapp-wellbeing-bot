# 🐳 Déploiement Unraid - WhatsApp Wellbeing Bot

## 🚀 Déploiement en 2 étapes (ultra-simple)

### Étape 1 : Copier le docker-compose.yml dans Docker Compose Manager

**Le dossier sera créé automatiquement par Docker !** Pas besoin de le créer manuellement.

1. Ouvrez **Docker Compose Manager** dans Unraid
2. Cliquez sur **"Add Stack"**
3. Nom : `whatsapp-wellbeing-bot`
4. Compose File Path : `/mnt/user/appdata/whatsapp-wellbeing-bot/docker-compose.yml`
   - ⚠️ **Note** : Le dossier sera créé automatiquement au premier démarrage
5. **Copiez-collez le contenu ci-dessous** dans le fichier `docker-compose.yml` :

```yaml
services:
  init-repo:
    image: alpine/git:latest
    container_name: whatsapp-bot-init
    volumes:
      - /mnt/user/appdata/whatsapp-wellbeing-bot:/workspace
    working_dir: /workspace
    command: >
      sh -c "
        echo '🚀 Initialisation du projet WhatsApp Wellbeing Bot';
        if [ ! -f app.py ]; then
          echo '📥 Clonage du dépôt depuis GitHub...';
          rm -rf * .* 2>/dev/null || true;
          git clone --depth 1 https://github.com/SlyCo0p3r/whatsapp-wellbeing-bot.git temp_repo;
          mv temp_repo/* temp_repo/.git* . 2>/dev/null || true;
          rm -rf temp_repo;
          echo '✅ Dépôt cloné avec succès';
        else
          echo '✅ Code déjà présent';
        fi;
        if [ ! -f .env ]; then
          echo '📝 Création du fichier .env depuis .env.example...';
          cp .env.example .env 2>/dev/null || touch .env;
          echo '⚠️  IMPORTANT: Éditez /mnt/user/appdata/whatsapp-wellbeing-bot/.env avec vos valeurs';
        else
          echo '✅ Fichier .env existe déjà';
        fi;
        mkdir -p data;
        chmod -R 755 data 2>/dev/null || true;
        echo '✅ Initialisation terminée';
      "
    restart: "no"

  whatsapp-wellbeing-bot:
    build: 
      context: /mnt/user/appdata/whatsapp-wellbeing-bot
      dockerfile: Dockerfile
    container_name: whatsapp-wellbeing-bot
    depends_on:
      init-repo:
        condition: service_completed_successfully
    volumes:
      - /mnt/user/appdata/whatsapp-wellbeing-bot/data:/app/data
    env_file:
      - /mnt/user/appdata/whatsapp-wellbeing-bot/.env
    restart: unless-stopped
    ports:
      - "5090:5000"
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

6. Cliquez sur **"Save"** puis **"Up"**

> ⚠️ **Important** : Au premier démarrage, vous verrez un avertissement `env file not found`. C'est normal ! Le conteneur `init-repo` va créer le fichier `.env` automatiquement. Attendez que `init-repo` se termine, puis configurez le `.env` et redémarrez le stack.

### Étape 2 : Configurer le fichier .env

**Après le premier démarrage**, le conteneur `init-repo` aura cloné le repo et créé le fichier `.env`. Configurez vos variables :

```bash
nano /mnt/user/appdata/whatsapp-wellbeing-bot/.env
```

**Variables obligatoires à configurer :**
```bash
WHATSAPP_TOKEN=your_token_from_meta
WHATSAPP_PHONE_ID=your_phone_id
WEBHOOK_VERIFY_TOKEN=your_secure_token
OWNER_PHONE=+33612345678
ALERT_PHONES=+33611111111,+33622222222
```

Puis redémarrez le conteneur :
```bash
docker-compose restart whatsapp-wellbeing-bot
```

**C'est tout !** 🎉

---

## 📋 Prérequis

- **Docker** : Inclus par défaut dans Unraid
- **Docker Compose Manager** : Plugin Unraid (ou Docker Compose en CLI)
- **Reverse Proxy HTTPS** : Nginx Proxy Manager, Traefik, ou SWAG (requis pour les webhooks WhatsApp)
- **Port 5090** : Doit être disponible

---

## ⚙️ Configuration du Reverse Proxy (Nginx Proxy Manager)

1. **Installez Nginx Proxy Manager** via Community Applications
2. **Créez un Proxy Host** avec :
   - Domain Name : `whatsapp-bot.votre-domaine.com`
   - Scheme : `http`
   - Forward Hostname/IP : `IP-DE-VOTRE-UNRAID` (ou `localhost`)
   - Forward Port : `5090`
   - SSL : Activez et obtenez un certificat Let's Encrypt

3. **Configurez le webhook WhatsApp** dans Meta Developer Dashboard :
   - URL : `https://whatsapp-bot.votre-domaine.com/whatsapp/webhook`
   - Verify Token : La valeur de `WEBHOOK_VERIFY_TOKEN` dans votre `.env`

---

## ✅ Vérification

```bash
# Vérifier les logs
docker logs whatsapp-wellbeing-bot

# Vérifier le healthcheck
curl http://IP-UNRAID:5090/health

# Vérifier que le conteneur est "healthy"
docker ps | grep whatsapp-wellbeing-bot
```

---

## 🔄 Mise à jour

Pour mettre à jour le code :

```bash
cd /mnt/user/appdata/whatsapp-wellbeing-bot
git pull
docker-compose restart whatsapp-wellbeing-bot
```

---

## 🆘 Dépannage

### Le conteneur init-repo échoue
```bash
docker logs whatsapp-bot-init
docker-compose up init-repo
```

### Le build échoue
Vérifiez que le repo a bien été cloné :
```bash
ls -la /mnt/user/appdata/whatsapp-wellbeing-bot/
```

### Le conteneur principal ne démarre pas
Vérifiez le fichier `.env` :
```bash
cat /mnt/user/appdata/whatsapp-wellbeing-bot/.env
docker logs whatsapp-wellbeing-bot
```

---

## 📚 Ressources

- [Documentation Unraid Docker](https://wiki.unraid.net/Docker_Management)
- [Nginx Proxy Manager](https://github.com/NginxProxyManager/nginx-proxy-manager)
- [Meta Developer Dashboard](https://developers.facebook.com/)
- [WhatsApp Cloud API Documentation](https://developers.facebook.com/docs/whatsapp)
