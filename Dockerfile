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
CMD ["python", "app.py"]
