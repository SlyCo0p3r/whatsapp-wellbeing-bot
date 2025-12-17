# Image de base légère
FROM python:3.12-slim

# Évite les fichiers .pyc et met les logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dossier de travail dans le conteneur
WORKDIR /app

# Copie uniquement requirements.txt d'abord (cache Docker)
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le code
COPY . .

# Utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Port exposé
EXPOSE 5000

# Commande de démarrage
# Utilise Gunicorn en production, Flask dev server en développement
# Pour forcer Gunicorn, définir USE_GUNICORN=true dans .env
CMD ["sh", "-c", "if [ \"$USE_GUNICORN\" = \"true\" ]; then gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --timeout 120 --access-logfile - --error-logfile - --log-level info app:app; else python app.py; fi"]
