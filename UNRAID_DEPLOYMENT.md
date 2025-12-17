# 🐳 Déploiement Unraid - WhatsApp Wellbeing Bot

## 🚀 Déploiement en 3 étapes (ultra-simple)

### Étape 1 : Créer le dossier et le fichier .env

Créez le dossier et un fichier `.env` vide (il sera rempli automatiquement par le conteneur init) :

```bash
mkdir -p /mnt/user/appdata/whatsapp-wellbeing-bot
touch /mnt/user/appdata/whatsapp-wellbeing-bot/.env
```

### Étape 2 : Copier le docker-compose.yml dans Docker Compose Manager

1. Ouvrez **Docker Compose Manager** dans Unraid
2. Cliquez sur **"Add Stack"**
3. Nom : `whatsapp-wellbeing-bot`
4. Compose File Path : `/mnt/user/appdata/whatsapp-wellbeing-bot/docker-compose.yml`
5. **Copiez-collez le contenu ci-dessous** dans le fichier `docker-compose.yml` :

```yaml
services:
  init-repo:
    image: alpine:latest
    container_name: whatsapp-bot-init
    volumes:
      - /mnt/user/appdata/whatsapp-wellbeing-bot:/workspace
    working_dir: /workspace
    command: |
      sh -c "
        apk add --no-cache git;
        echo 'Initialisation du projet WhatsApp Wellbeing Bot';
        mkdir -p /workspace;
        cd /workspace;
        if [ ! -f app.py ]; then
          echo 'Clonage du depot depuis GitHub...';
          rm -rf * .* 2>/dev/null || true;
          git clone --depth 1 https://github.com/SlyCo0p3r/whatsapp-wellbeing-bot.git temp_repo || exit 1;
          if [ ! -d temp_repo ]; then
            echo 'ERREUR: Le clonage a echoue';
            exit 1;
          fi;
          mv temp_repo/* . 2>/dev/null || true;
          mv temp_repo/.git* . 2>/dev/null || true;
          rm -rf temp_repo;
          if [ ! -f Dockerfile ]; then
            echo 'ERREUR: Dockerfile non trouve apres le clonage';
            ls -la;
            exit 1;
          fi;
          echo 'Depot clone avec succes';
        else
          echo 'Code deja present';
        fi;
        if [ ! -f .env ]; then
          echo 'Creation du fichier .env depuis .env.example...';
          if [ -f .env.example ]; then
            cp .env.example .env;
          else
            echo '# Configuration WhatsApp Wellbeing Bot' > .env;
            echo 'WHATSAPP_TOKEN=' >> .env;
            echo 'WHATSAPP_PHONE_ID=' >> .env;
            echo 'WEBHOOK_VERIFY_TOKEN=' >> .env;
            echo 'OWNER_PHONE=' >> .env;
            echo 'ALERT_PHONES=' >> .env;
            echo 'DAILY_HOUR=9' >> .env;
            echo 'RESPONSE_TIMEOUT_MIN=120' >> .env;
            echo 'TZ=Europe/Paris' >> .env;
            echo 'CORS_ORIGINS=http://localhost' >> .env;
            echo 'USE_GUNICORN=false' >> .env;
          fi;
          echo 'IMPORTANT: Editez /mnt/user/appdata/whatsapp-wellbeing-bot/.env avec vos valeurs';
        else
          echo 'Fichier .env existe deja';
        fi;
        mkdir -p data;
        chmod -R 755 data 2>/dev/null || true;
        if [ ! -f Dockerfile ]; then
          echo 'ERREUR: Dockerfile non trouve apres le clonage';
          exit 1;
        fi;
        echo 'Initialisation terminee';
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

> 💡 **Note** : Le conteneur `init-repo` va automatiquement remplir le fichier `.env` avec les valeurs par défaut depuis `.env.example` au premier démarrage.

### Étape 3 : Configurer le fichier .env

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

**Important :** Après avoir modifié le `.env`, vous devez **recréer le conteneur** (pas juste le redémarrer) :

```bash
docker-compose up -d --force-recreate whatsapp-wellbeing-bot
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
docker-compose build --no-cache
docker-compose up -d
```

---

## 🔄 Recréer le conteneur

Si vous devez recréer le conteneur (après modification du `.env` ou pour résoudre un problème) :

```bash
cd /mnt/user/appdata/whatsapp-wellbeing-bot
docker-compose down
docker-compose up -d
```

Ou pour recréer uniquement le conteneur principal :

```bash
docker-compose stop whatsapp-wellbeing-bot
docker-compose rm -f whatsapp-wellbeing-bot
docker-compose up -d whatsapp-wellbeing-bot
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

Si le Dockerfile n'existe pas, relancez init-repo :
```bash
docker-compose up init-repo
```

### Le conteneur principal ne démarre pas
Vérifiez le fichier `.env` :
```bash
cat /mnt/user/appdata/whatsapp-wellbeing-bot/.env
docker logs whatsapp-wellbeing-bot
```

**Important :** Après modification du `.env`, recréez le conteneur avec `docker-compose up -d --force-recreate whatsapp-wellbeing-bot`

### Erreur de permissions sur data/state.json
```bash
chown -R 1000:1000 /mnt/user/appdata/whatsapp-wellbeing-bot/data/
chmod -R 755 /mnt/user/appdata/whatsapp-wellbeing-bot/data/
docker-compose restart whatsapp-wellbeing-bot
```

---

## 📚 Ressources

- [Documentation Unraid Docker](https://wiki.unraid.net/Docker_Management)
- [Nginx Proxy Manager](https://github.com/NginxProxyManager/nginx-proxy-manager)
- [Meta Developer Dashboard](https://developers.facebook.com/)
- [WhatsApp Cloud API Documentation](https://developers.facebook.com/docs/whatsapp)
