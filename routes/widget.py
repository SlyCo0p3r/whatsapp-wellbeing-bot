"""Routes pour le widget et la documentation API"""
import json
import logging
from flask import Blueprint, request

logger = logging.getLogger("whatsapp_bot")

bp = Blueprint('widget', __name__)


@bp.get("/widget")
def widget():
    """Widget HTML de statut en temps réel"""
    base_url = request.url_root.rstrip('/')
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-transparent p-2">
    <div id="w" class="max-w-xs bg-gradient-to-br from-purple-600 to-indigo-700 rounded-2xl p-5 text-white shadow-2xl">
        <div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div>
        <div class="text-center py-5 opacity-80"><div class="inline-block w-6 h-6 border-3 border-white border-t-transparent rounded-full animate-spin mb-2"></div><div class="text-sm">Chargement...</div></div>
    </div>
    <script>
        function f(){{fetch('{base_url}/health').then(r=>r.json()).then(d=>{{var s=d.status!=='ok'?{{t:'offline',l:'Hors ligne',c:'red'}}:d.waiting?{{t:'waiting',l:'En attente',c:'yellow'}}:{{t:'online',l:'Actif',c:'green'}};function fmt(i){{if(!i)return 'Jamais';var m=Math.floor((Date.now()-new Date(i))/60000);if(m<1)return"A l'instant";if(m<60)return'Il y a '+m+'min';if(m<1440)return'Il y a '+Math.floor(m/60)+'h';var dt=new Date(i);return('0'+dt.getDate()).slice(-2)+'/'+('0'+(dt.getMonth()+1)).slice(-2)}}document.getElementById('w').innerHTML='<div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div><div class="bg-white bg-opacity-20 backdrop-blur-lg rounded-xl p-4 mb-3 space-y-2"><div class="flex justify-between items-center"><span class="text-sm opacity-90">Etat</span><span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-'+s.c+'-500 bg-opacity-30"><span class="w-2 h-2 rounded-full bg-'+s.c+'-500 animate-pulse"></span>'+s.l+'</span></div><div class="flex justify-between items-center"><span class="text-sm opacity-90">Dernier ping</span><span class="text-sm font-semibold">'+fmt(d.last_ping)+'</span></div><div class="flex justify-between items-center"><span class="text-sm opacity-90">Dernière réponse</span><span class="text-sm font-semibold">'+fmt(d.last_reply)+'</span></div></div><div class="text-center text-xs opacity-70">Mise à jour toutes les 30s</div>'}}).catch(()=>{{document.getElementById('w').innerHTML='<div class="flex items-center gap-3 mb-4"><div class="text-3xl">🐾</div><div><div class="text-lg font-semibold">Mathieu le Chat</div><div class="text-xs opacity-90">Bot de surveillance</div></div></div><div class="bg-red-500 bg-opacity-30 rounded-xl p-3 text-center text-sm">⚠️ Erreur de connexion</div>'}})}}f();setInterval(f,30000)
    </script>
</body>
</html>""", 200, {'Content-Type': 'text/html'}


@bp.get("/api")
def api_docs():
    """Page web de documentation de l'API"""
    base_url = request.url_root.rstrip('/')
    
    endpoints = [
        {
            "method": "GET",
            "path": "/health",
            "description": "Vérifie que le bot est vivant et retourne l'état actuel",
            "auth": False,
            "params": [],
            "example_response": {
                "status": "ok",
                "waiting": False,
                "last_ping": "2024-01-15T09:00:00+01:00",
                "last_reply": "2024-01-15T09:05:00+01:00"
            }
        },
        {
            "method": "GET",
            "path": "/stats",
            "description": "Retourne les statistiques d'utilisation du bot (pings, alertes, taux de réponse, etc.)",
            "auth": False,
            "params": [],
            "example_response": {
                "status": "ok",
                "stats": {
                    "total_pings": 150,
                    "total_alerts": 3,
                    "total_replies": 147,
                    "response_rate": 98.0,
                    "first_ping_date": "2024-01-01T09:00:00+01:00",
                    "uptime_days": 14
                },
                "current_state": {
                    "waiting": False,
                    "scheduler_running": True
                },
                "configuration": {
                    "daily_hour": 9,
                    "response_timeout_min": 120
                }
            }
        },
        {
            "method": "GET",
            "path": "/widget",
            "description": "Widget HTML de statut en temps réel (à intégrer dans une page web)",
            "auth": False,
            "params": [],
            "example_response": "HTML widget"
        },
        {
            "method": "GET",
            "path": "/whatsapp/webhook",
            "description": "Vérification du webhook par Meta (appelé lors de la configuration)",
            "auth": True,
            "params": [
                {"name": "hub.mode", "type": "string", "required": True, "description": "Doit être 'subscribe'"},
                {"name": "hub.verify_token", "type": "string", "required": True, "description": "Token de vérification (WEBHOOK_VERIFY_TOKEN)"},
                {"name": "hub.challenge", "type": "string", "required": True, "description": "Challenge à retourner"}
            ],
            "example_response": "Challenge string (si token valide)"
        },
        {
            "method": "POST",
            "path": "/whatsapp/webhook",
            "description": "Réception des messages WhatsApp depuis Meta",
            "auth": False,
            "params": [],
            "example_response": {"status": "ok"}
        },
        {
            "method": "GET",
            "path": "/debug/ping",
            "description": "Force un ping de test (sans attendre l'heure configurée)",
            "auth": True,
            "params": [
                {"name": "token", "type": "string", "required": False, "description": "Token de debug (ou header X-Debug-Token)"}
            ],
            "example_response": {"status": "ok", "message": "Ping envoyé"},
            "note": "Nécessite ENABLE_DEBUG=true dans .env"
        },
        {
            "method": "GET",
            "path": "/debug/state",
            "description": "Voir l'état actuel du bot sans le modifier",
            "auth": True,
            "params": [
                {"name": "token", "type": "string", "required": False, "description": "Token de debug (ou header X-Debug-Token)"}
            ],
            "example_response": {
                "waiting": False,
                "deadline": None,
                "last_reply": "2024-01-15T09:05:00+01:00",
                "last_ping": "2024-01-15T09:00:00+01:00",
                "alert_sent": False,
                "stats": {...}
            },
            "note": "Nécessite ENABLE_DEBUG=true dans .env"
        }
    ]
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - WhatsApp Wellbeing Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .method-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .method-get {{ background-color: #10b981; color: white; }}
        .method-post {{ background-color: #3b82f6; color: white; }}
        code {{
            background-color: #1f2937;
            color: #f3f4f6;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
            font-family: 'Courier New', monospace;
        }}
        pre {{
            background-color: #1f2937;
            color: #f3f4f6;
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <div class="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div class="flex items-center gap-3 mb-6">
                <div class="text-4xl">🐾</div>
                <div>
                    <h1 class="text-3xl font-bold text-gray-800">WhatsApp Wellbeing Bot</h1>
                    <p class="text-gray-600">Documentation de l'API</p>
                </div>
            </div>
            <div class="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
                <p class="text-sm text-blue-700">
                    <strong>Base URL:</strong> <code>{base_url}</code>
                </p>
            </div>
        </div>
        
        <div class="space-y-6">
"""
    
    for endpoint in endpoints:
        method_class = f"method-{endpoint['method'].lower()}"
        html += f"""
            <div class="bg-white rounded-lg shadow-lg p-6">
                <div class="flex items-center gap-3 mb-4">
                    <span class="method-badge {method_class}">{endpoint['method']}</span>
                    <code class="text-lg font-mono">{endpoint['path']}</code>
                    {f'<span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">Auth requise</span>' if endpoint['auth'] else ''}
                </div>
                <p class="text-gray-700 mb-4">{endpoint['description']}</p>
"""
        
        if endpoint.get('note'):
            html += f"""
                <div class="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-4">
                    <p class="text-sm text-yellow-700"><strong>Note:</strong> {endpoint['note']}</p>
                </div>
"""
        
        if endpoint['params']:
            html += """
                <div class="mb-4">
                    <h3 class="font-semibold text-gray-800 mb-2">Paramètres:</h3>
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Requis</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
"""
            for param in endpoint['params']:
                html += f"""
                                <tr>
                                    <td class="px-4 py-2"><code>{param['name']}</code></td>
                                    <td class="px-4 py-2 text-sm text-gray-600">{param['type']}</td>
                                    <td class="px-4 py-2 text-sm">{'✅' if param['required'] else '❌'}</td>
                                    <td class="px-4 py-2 text-sm text-gray-600">{param['description']}</td>
                                </tr>
"""
            html += """
                            </tbody>
                        </table>
                    </div>
                </div>
"""
        
        html += """
                <div class="mb-4">
                    <h3 class="font-semibold text-gray-800 mb-2">Exemple de réponse:</h3>
                    <pre><code>"""
        
        html += json.dumps(endpoint['example_response'], indent=2, ensure_ascii=False)
        
        html += """</code></pre>
                </div>
                
                <div class="mt-4 pt-4 border-t border-gray-200">
                    <p class="text-sm text-gray-600">
                        <strong>Exemple curl:</strong>
                        <code class="block mt-2 p-2 bg-gray-100 rounded">
"""
        if endpoint['method'] == 'GET':
            if endpoint['auth'] and endpoint['path'].startswith('/debug'):
                html += f"curl -H 'X-Debug-Token: your-token' {base_url}{endpoint['path']}"
            elif endpoint['path'] == '/whatsapp/webhook':
                html += f"curl '{base_url}{endpoint['path']}?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test'"
            else:
                html += f"curl {base_url}{endpoint['path']}"
        else:
            html += f"curl -X POST {base_url}{endpoint['path']}"
        
        html += """
                        </code>
                    </p>
                </div>
            </div>
"""
    
    html += """
        </div>
        
        <div class="mt-8 bg-white rounded-lg shadow-lg p-6">
            <h2 class="text-xl font-bold text-gray-800 mb-4">📊 Statistiques en direct</h2>
            <div id="stats" class="text-center py-4">
                <div class="inline-block w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                <p class="mt-2 text-sm text-gray-600">Chargement...</p>
            </div>
        </div>
    </div>
    
    <script>
        // Charger les statistiques
        fetch('""" + base_url + """/stats')
            .then(r => r.json())
            .then(data => {{
                const stats = data.stats || {{}};
                const html = `
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="bg-blue-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-blue-600">${{stats.total_pings || 0}}</div>
                            <div class="text-sm text-gray-600">Pings envoyés</div>
                        </div>
                        <div class="bg-green-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-green-600">${{stats.total_replies || 0}}</div>
                            <div class="text-sm text-gray-600">Réponses reçues</div>
                        </div>
                        <div class="bg-purple-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-purple-600">${{stats.response_rate || 0}}%</div>
                            <div class="text-sm text-gray-600">Taux de réponse</div>
                        </div>
                        <div class="bg-red-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-red-600">${{stats.total_alerts || 0}}</div>
                            <div class="text-sm text-gray-600">Alertes envoyées</div>
                        </div>
                        <div class="bg-yellow-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-yellow-600">${{stats.uptime_days || 0}}</div>
                            <div class="text-sm text-gray-600">Jours d'activité</div>
                        </div>
                        <div class="bg-indigo-50 p-4 rounded-lg">
                            <div class="text-2xl font-bold text-indigo-600">${{data.current_state?.scheduler_running ? '✅' : '❌'}}</div>
                            <div class="text-sm text-gray-600">Scheduler</div>
                        </div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = html;
            }})
            .catch(err => {{
                document.getElementById('stats').innerHTML = '<p class="text-red-600">Erreur de chargement des statistiques</p>';
            }});
    </script>
</body>
</html>"""
    
    return html, 200, {'Content-Type': 'text/html'}
