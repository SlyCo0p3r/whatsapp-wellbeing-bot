# Analyse des dépendances et erreurs potentielles

## 📊 Graphique des dépendances

```
app.py
├── logging_config.py (configure_logging)
├── config.py (CORS_ORIGINS, STATE_FILE, TZ, DAILY_HOUR, RESPONSE_TIMEOUT_MIN, ALERT_PHONES, validate_config)
├── state_manager.py (StateManager)
├── scheduler_tasks.py (daily_ping, check_deadline)
└── routes/
    ├── webhooks.py (bp)
    ├── health.py (bp)
    ├── debug.py (bp)
    └── widget.py (bp)

config.py
└── (aucune dépendance interne)

state_manager.py
└── config.py (TZ, STATE_FILE)

whatsapp_api.py
└── config.py (WHATSAPP_TOKEN, WHATSAPP_PHONE_ID)

scheduler_tasks.py
├── config.py (TZ, OWNER_PHONE, ALERT_PHONES, RESPONSE_TIMEOUT_MIN, TEMPLATE_*)
├── whatsapp_api.py (send_template)
└── app.py (state_manager via get_state_manager()) ⚠️ Import circulaire géré

routes/webhooks.py
├── config.py (WEBHOOK_VERIFY_TOKEN, OWNER_PHONE, TEMPLATE_OK)
├── whatsapp_api.py (send_template)
└── app.py (state_manager via get_state_manager()) ⚠️ Import circulaire géré

routes/health.py
├── config.py (TZ, DAILY_HOUR, RESPONSE_TIMEOUT_MIN, ALERT_PHONES)
└── app.py (state_manager, scheduler via get_state_manager() et import direct) ⚠️ Import circulaire géré

routes/debug.py
├── config.py (ENABLE_DEBUG, DEBUG_TOKEN)
├── scheduler_tasks.py (daily_ping)
└── app.py (state_manager via get_state_manager()) ⚠️ Import circulaire géré

routes/widget.py
└── (aucune dépendance interne, seulement Flask)
```

## ⚠️ Imports circulaires gérés

Les imports circulaires sont gérés avec des fonctions `get_state_manager()` qui importent depuis `app.py` uniquement au moment de l'exécution, pas au moment de l'import du module. Cela évite les erreurs de dépendance circulaire.

**Fichiers concernés :**
- `scheduler_tasks.py` → `app.py` (state_manager)
- `routes/webhooks.py` → `app.py` (state_manager)
- `routes/health.py` → `app.py` (state_manager, scheduler)
- `routes/debug.py` → `app.py` (state_manager)

**Solution :** Import lazy dans une fonction, appelé uniquement lors de l'exécution.

## ✅ Vérifications de sécurité ajoutées

### 1. whatsapp_api.py
- ✅ Vérification que `WHATSAPP_TOKEN` et `WHATSAPP_PHONE_ID` ne sont pas None avant utilisation

### 2. scheduler_tasks.py
- ✅ Vérification que `OWNER_PHONE` est configuré avant d'envoyer le ping
- ✅ Vérification que `ALERT_PHONES` n'est pas vide avant d'envoyer les alertes

### 3. routes/webhooks.py
- ✅ Vérification que `OWNER_PHONE` est configuré avant de traiter les messages

### 4. routes/health.py
- ✅ Gestion d'erreur pour l'import de `scheduler` (ImportError, AttributeError)

### 5. state_manager.py
- ✅ Gestion du cas où `os.path.dirname()` retourne une chaîne vide (fichier à la racine)

## 🔍 Erreurs potentielles à l'exécution

### Erreurs critiques (bloquantes)

1. **Config manquante** : `validate_config()` lève une exception si variables obligatoires manquantes
   - ✅ Géré dans `app.py` avant le démarrage

2. **Scheduler ne démarre pas** : Exception levée si le scheduler ne peut pas démarrer
   - ✅ Géré avec try/except dans `app.py`

3. **StateManager ne peut pas charger l'état** : Retourne état par défaut si fichier corrompu
   - ✅ Géré avec fallback dans `state_manager.py`

### Erreurs non-bloquantes (gérées)

1. **WHATSAPP_TOKEN/PHONE_ID None** : `wa_call()` retourne None
   - ✅ Vérifié dans `whatsapp_api.py`

2. **OWNER_PHONE vide** : Ping/webhook ignorés avec log d'erreur
   - ✅ Vérifié dans `scheduler_tasks.py` et `routes/webhooks.py`

3. **ALERT_PHONES vide** : Alertes non envoyées avec log d'avertissement
   - ✅ Vérifié dans `scheduler_tasks.py`

4. **Scheduler non accessible** : `scheduler_running` retourne False
   - ✅ Géré avec try/except dans `routes/health.py`

5. **Parsing JSON échoue** : Fallback sur `r.text`
   - ✅ Géré dans `whatsapp_api.py`

6. **Fichier state.json corrompu** : Backup créé, état par défaut restauré
   - ✅ Géré dans `state_manager.py`

## 🔄 Ordre d'initialisation

1. `logging_config.py` - Configuration du logging (le plus tôt)
2. `config.py` - Chargement des variables d'environnement
3. `state_manager.py` - Création de l'instance StateManager
4. `whatsapp_api.py` - Fonctions disponibles (pas d'initialisation)
5. `scheduler_tasks.py` - Fonctions disponibles (pas d'initialisation)
6. `routes/*.py` - Blueprints créés (pas d'initialisation)
7. `app.py` - Initialisation Flask, scheduler, enregistrement des routes

## ✅ Tous les fichiers compilent sans erreur

La syntaxe Python est valide pour tous les fichiers.

