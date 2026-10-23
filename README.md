# Network Security Tool
A simple Python project for network security students.
Author: Thierry

## NetSecure (TP 3)

Plateforme de supervision réseau conteneurisée :

| Service | Rôle | Réseaux |
|---|---|---|
| `frontend` | Nginx : interface web + reverse proxy `/api/` vers l'API | `frontend` |
| `api` | Flask/Gunicorn : vérifie les ports des services internes et enregistre les résultats | `frontend`, `backend` |
| `db` | PostgreSQL : historique des contrôles | `backend` |

```bash
cp .env.example .env   # puis changer le mot de passe
docker compose up -d --build
```

Interface : http://localhost:8080
