# TP 3 — NetSecure : audit de sécurité Docker avec Trivy

Outil utilisé : **Trivy 0.76.1**, lancé via son image Docker officielle (version épinglée) :

```bash
docker run --rm -v //var/run/docker.sock:/var/run/docker.sock -v trivy-cache:/root/.cache/ \
  aquasec/trivy:0.76.1 image --severity HIGH,CRITICAL <image>
```

## Partie 1 — Reconnaissance de l'infrastructure (état initial)

| Service | Image | Réseaux | Port publié sur l'hôte | Variables d'environnement |
|---|---|---|---|---|
| `frontend` | `nginx:1.27` | `frontend` | `0.0.0.0:8080 → 80` | — |
| `api` | `python:3.12` (Flask + Gunicorn) | `frontend`, `backend` | `0.0.0.0:5000 → 5000` | `.env` (identifiants BD), `DB_HOST`, `TARGETS` |
| `db` | `postgres:16` | `backend` | `0.0.0.0:5432 → 5432` | `.env` (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) |

Volume : `db-data` (données PostgreSQL). Réseaux : `netsecure_frontend` et `netsecure_backend` (bridge).

**Constats :**
- Seul le **frontend** doit être accessible depuis l'hôte : c'est l'unique point d'entrée. Nginx relaie `/api/` vers l'API par le réseau Docker.
- L'**API** était publiée sur `0.0.0.0:5000`. Elle était donc joignable directement, en contournant Nginx. Preuve : `http://localhost:5000/` renvoyait un 404 *Flask*.
- La **base de données exposait inutilement son port 5432** sur toutes les interfaces de l'hôte, donc sur le réseau local, alors que seule l'API a besoin de la joindre.
- Les secrets ne sont pas dans Git : `.env` est ignoré, et seul `.env.example` est versionné.

## Partie 2 — Scan des images (avant durcissement)

| Image | OS | CRITICAL | HIGH | Total | Taille |
|---|---|---|---|---|---|
| `netsecure-api:dev` (`python:3.12`) | Debian 13.7 | **24** | **434** | **458** | 1,66 Go |
| `netsecure-frontend:dev` (`nginx:1.27`) | Debian 12.11 | 11 | 169 | 180 | 282 Mo |
| `postgres:16` | Debian 13.7 | 2 | 86 | 88 | 642 Mo |

![Résumé du scan de l'API avant durcissement](assets/img/trivy-api-avant-resume.png)
![Détail du scan de l'API avant durcissement](assets/img/trivy-api-avant-detail.png)
![Scan du frontend avant durcissement](assets/img/trivy-frontend-avant.png)

Extrait complet : [docs/trivy/api-avant.txt](docs/trivy/api-avant.txt)

**Trois résultats significatifs (API) :**

| Composant | Version installée | Sévérité | CVE | Version corrigée |
|---|---|---|---|---|
| `libmariadb-dev` | 1:11.8.6-0+deb13u1 | CRITICAL | CVE-2026-49261 (exécution de code arbitraire via `wsrep_notify_cmd`) | aucune (*affected*) |
| `openssh-client` | 1:10.0p1-7+deb13u4 | CRITICAL | CVE-2026-60002 (use-after-free lors du ré-échange de clé d'hôte) | aucune (*affected*) |
| `curl` | 8.14.1-2+deb13u7 | HIGH | CVE-2026-12064 (contournement de la vérification de l'hôte SSH) | aucune (*affected*) |

**Analyse :**
- **100 % des vulnérabilités sont dans les paquets système Debian.** Les dépendances Python de l'application (Flask, Gunicorn, psycopg…) n'en ont aucune.
- Ces paquets viennent de l'image `python:3.12` « complète ». Elle embarque un environnement de compilation : clients MariaDB, ImageMagick, OpenEXR, GnuPG, openssh, en-têtes du noyau… **L'API n'utilise aucun de ces paquets.** Ils ne font qu'élargir la surface d'attaque.
- **Aucune vulnérabilité n'avait de version corrigée** au moment du scan (statuts : 443 *affected*, 12 *fix_deferred*, 3 *will_not_fix*). Mettre à jour les paquets ne suffisait donc pas : la vraie correction était de **retirer les paquets inutiles**.

## Partie 3 — Durcissement appliqué

### Dockerfile de l'API ([api/Dockerfile](api/Dockerfile))

| Mesure | Avant | Après | Pourquoi |
|---|---|---|---|
| Image de base | `python:3.12` (complète) | `python:3.12-slim` | Moins de paquets embarqués, donc moins de CVE et une surface d'attaque réduite |
| Correctifs système | aucun | `apt-get upgrade` au build | Applique les correctifs Debian disponibles |
| Utilisateur | `root` | `app` (uid 10001, sans shell) | Une compromission de l'application ne donne pas les droits root dans le conteneur |
| Outils d'installation | pip, setuptools, wheel présents | désinstallés après `pip install` | Inutiles à l'exécution. pip embarquait des copies vulnérables d'`urllib3` et `msgpack` (4 CVE HIGH corrigeables) |
| Cache / bytecode | cache pip conservé | `PIP_NO_CACHE_DIR`, `PYTHONDONTWRITEBYTECODE` | Image plus légère, compatible avec un système de fichiers en lecture seule |

### Dockerfile du frontend ([frontend/Dockerfile](frontend/Dockerfile))

| Avant | Après | Pourquoi |
|---|---|---|
| `nginx:1.27` (Debian, root, version non maintenue) | `nginxinc/nginx-unprivileged:1.30.6-alpine` | Branche stable maintenue et version épinglée. Base Alpine minimale. Exécution sous l'utilisateur `nginx` (uid 101), sur le port 8080 |
| En-tête `Server: nginx/1.27.5` | `server_tokens off` → `Server: nginx` | Ne divulgue plus la version exacte à un attaquant |

### Compose ([compose.yaml](compose.yaml))

| Mesure | Services | Effet |
|---|---|---|
| Suppression du port publié **5000** | `api` | API joignable uniquement par Nginx, via le réseau Docker |
| Suppression du port publié **5432** | `db` | Base joignable uniquement par l'API, via le réseau `backend` |
| Frontend publié sur `127.0.0.1:8080` au lieu de `0.0.0.0` | `frontend` | Accessible depuis la machine seulement, pas depuis le réseau local |
| Réseau `backend` en `internal: true` | `db`, `api` | Le réseau de la base n'a aucune route vers Internet |
| `read_only: true` + `tmpfs: /tmp` | `api`, `frontend` | Système de fichiers en lecture seule : un attaquant ne peut ni modifier le code ni déposer un binaire |
| `cap_drop: ALL` | tous | Retire toutes les capacités Linux. La base ne récupère que les 5 capacités dont son entrypoint a besoin (`CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `SETGID`, `SETUID`) |
| `no-new-privileges:true` | tous | Empêche toute élévation de privilèges (binaires setuid, etc.) |
| `postgres:16` → `postgres:16-alpine` | `db` | Image plus légère : 88 → 26 vulnérabilités HIGH/CRITICAL |
| Healthcheck de l'API + `depends_on: service_healthy` | `api`, `frontend` | Démarrage ordonné : Nginx attend que l'API réponde |

### Comparaison avant / après

| Image | CRITICAL | HIGH | Corrigeables | Taille |
|---|---|---|---|---|
| API avant (`netsecure-api:dev`) | 24 | 434 | 0 | 1,66 Go |
| **API après (`netsecure-api:hardened`)** | **0** | **44** | **0** | **212 Mo** |
| Frontend avant (`nginx:1.27`) | 11 | 169 | 87 | 282 Mo |
| **Frontend après (`netsecure-frontend:hardened`)** | **0** | **0** | — | **90 Mo** |
| Base avant (`postgres:16`) | 2 | 86 | 26 | 642 Mo |
| Base après (`postgres:16-alpine`) | 1 | 25 | 26 | 420 Mo |

Extraits : [docs/trivy/api-apres.txt](docs/trivy/api-apres.txt), [docs/trivy/frontend-apres.txt](docs/trivy/frontend-apres.txt)

**API après durcissement : 44 HIGH, 0 CRITICAL** (Debian 13.7, 87 paquets système au lieu de 469)

![Résumé du scan de l'API après durcissement](assets/img/trivy-api-apres-resume.png)
![Détail du scan de l'API après durcissement](assets/img/trivy-api-apres-detail.png)

**Frontend après durcissement : 0 vulnérabilité HIGH/CRITICAL** (Alpine 3.24.2, 70 paquets)

![Scan du frontend après durcissement](assets/img/trivy-frontend-apres.png)

Pendant ce scan, Trivy affiche deux avertissements `Unable to get vulnerability details` pour `CVE-2026-107891`. Ce n'est pas une erreur du scan : la CVE est référencée par la base Alpine, mais ses détails sont absents de la base Trivy (CVE en cours de publication ou rejetée). Trivy ne peut donc pas lui attribuer de sévérité, et elle n'apparaît pas dans le filtre HIGH/CRITICAL.

**Les 44 HIGH restantes sur l'API** concernent des paquets du socle Debian minimal (`util-linux`, `ncurses`, `systemd` libs, `perl-base`, `libacl1`), présents même dans l'image *slim*. **Aucune n'a de correctif disponible** : on ne peut pas les corriger aujourd'hui, seulement les surveiller. Pour aller plus loin, il faudrait une image *distroless* ou construite *from scratch*, qui ne contient ni shell ni utilitaires système.

### Vérification fonctionnelle

| Test | Résultat |
|---|---|
| `http://localhost:8080` (interface) | ✅ 200, l'interface fonctionne |
| `localhost:8080/api/health` (via Nginx) | ✅ `{"database":"up","status":"ok"}` |
| `POST /api/checks` (API → BD, API → services) | ✅ 201, résultats enregistrés, historique conservé |
| `localhost:5000` / `localhost:5432` depuis l'hôte | ❌ plus aucun conteneur publié sur ces ports |
| Utilisateur dans les conteneurs | `api` : `uid=10001(app)` ; `frontend` : `uid=101(nginx)` |
| Écriture dans `/app` (API) ou `/etc/nginx` (frontend) | ❌ `Read-only file system` |
| Capacités effectives de l'API | `CapEff: 0000000000000000` (aucune) |
| Accès Internet depuis `db` (réseau `backend`) | ❌ aucune résolution DNS externe |

## Partie 4 — Contrôle Trivy dans le pipeline CI

Workflow : [.github/workflows/security-scan.yml](.github/workflows/security-scan.yml), déclenché à chaque `push` et `pull_request`.

### Fonctionnement

Un job `scan` est lancé pour chaque image (matrice `api` / `frontend`) :

| Étape | Rôle |
|---|---|
| `Checkout repository` | `actions/checkout` épinglée sur le **SHA de commit** de la v7.0.1, et non sur un tag qu'on peut déplacer |
| `Build … image` | `docker build -t netsecure-<service>:ci ./<service>` |
| `Install Trivy` | Téléchargement de la **release officielle 0.76.1** (version fixée), puis **vérification de l'empreinte SHA-256** publiée dans `trivy_0.76.1_checksums.txt` avant extraction. Si l'archive a été altérée, `sha256sum --check` échoue et le job s'arrête. |
| `Report HIGH and CRITICAL vulnerabilities` | Rapport complet, `--exit-code 0` : informatif, ne bloque pas |
| `Fail on CRITICAL vulnerabilities` | **Barrière 1** : `--severity CRITICAL --exit-code 1`. Aucune CRITICAL tolérée, qu'elle ait un correctif ou non |
| `Fail on fixable HIGH vulnerabilities` | **Barrière 2** : `--severity HIGH --ignore-unfixed --exit-code 1`. Bloque toute HIGH pour laquelle un correctif existe |

La permission `contents: read` applique le moindre privilège, et `fail-fast: false` permet d'obtenir le résultat des deux images même si l'une échoue.

### Pourquoi deux barrières plutôt que `--exit-code 1 --severity HIGH,CRITICAL`

La commande proposée dans l'énoncé échouerait **en permanence** sur notre API durcie : il reste 44 HIGH dans le socle Debian, **et aucune n'a de correctif**. Un pipeline toujours rouge pour des problèmes qu'on ne peut pas corriger finit par être ignoré, ou désactivé.

Notre politique bloque donc :
- **toute CRITICAL**, parce que le risque est trop élevé : il faut changer d'image ou de composant ;
- **toute HIGH corrigeable**, parce qu'il suffit de mettre à jour : il n'y a aucune raison de livrer.

Les HIGH sans correctif restent visibles dans le rapport, pour être surveillées.

### Résultats attendus (simulés en local avec les mêmes commandes)

| Image | Barrière CRITICAL | Barrière HIGH corrigeables | Pipeline |
|---|---|---|---|
| `netsecure-api:hardened` | exit 0 | exit 0 | ✅ |
| `netsecure-frontend:hardened` | exit 0 | exit 0 | ✅ |
| `netsecure-api:dev` (image d'avant durcissement) | **exit 1** (24 CRITICAL) | exit 0 | ❌ |

La politique aurait donc **bloqué l'image initiale** et **laisse passer l'image durcie**.

### Pourquoi un scan en échec bloque la suite du pipeline

Quand Trivy trouve une vulnérabilité au niveau demandé, `--exit-code 1` le fait **terminer avec le code 1**. GitHub Actions considère alors l'étape en échec : les étapes suivantes du job ne sont pas exécutées, le job et le run passent au rouge, et le check de la Pull Request échoue. Avec une règle de protection de branche (*Require status checks to pass*), le merge vers `main` devient impossible. Une image vulnérable ne peut donc pas être intégrée, ni déployée par une étape ultérieure.

### Pourquoi le job réussit ici

Les images durcies ne contiennent **aucune CRITICAL** et **aucune HIGH corrigeable** : chaque commande Trivy se termine avec le code 0. Le job réussit **sans** que les images soient exemptes de vulnérabilités : 44 HIGH non corrigées restent présentes dans l'API. Elles sont affichées dans l'étape de rapport et doivent être réévaluées à chaque nouveau scan, car la base Trivy est mise à jour quotidiennement.
