# Nuit Blanche — Automatisation du carrousel Instagram

## 1. But du projet

**Nuit Blanche** est une page Instagram qui publie chaque semaine un
carrousel recensant les événements du Havre et de sa région. Aujourd'hui,
l'équipe remplit un Google Sheet puis recrée le carrousel à la main dans
Canva.

Ce projet automatise entièrement la génération du carrousel **sans changer
les habitudes de l'équipe** : ils continuent de remplir leur Google Sheet
comme avant. Ce n'est pas une application SaaS ni un dashboard — c'est une
automatisation invisible reliée à leur Sheet, avec un simple menu Google
Sheets en secours pour les ajouts de dernière minute.

## 2. Architecture

Deux parties, séparées et indépendantes :

```
nuit-blanche-automation/
├── backend/                  # Moteur Python (FastAPI + Playwright)
│   ├── app/
│   │   ├── api/               # Routes HTTP + dépendances FastAPI
│   │   ├── core/               # Config, sécurité, erreurs, logging
│   │   ├── models/             # Modèles internes (ex. GenerationRecord)
│   │   ├── schemas/             # Schémas Pydantic (JSON en entrée/sortie)
│   │   ├── services/            # Fonctions pures : normalisation, tri,
│   │   │                          groupement, pagination, textes
│   │   ├── rendering/           # Jinja2 → HTML → Playwright → PNG → ZIP
│   │   ├── storage/              # Abstraction de stockage (Local / Drive)
│   │   ├── templates/            # Templates HTML des slides
│   │   └── static/css/            # Design system (couleurs, typographie)
│   ├── tests/                  # pytest
│   ├── scripts/                 # generate_demo.py
│   ├── generated/                # Sortie locale (ignorée par git)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── google-apps-script/        # Script attaché au Google Sheet
│   ├── Menu.gs                  # Menu "Nuit Blanche"
│   ├── Config.gs                 # Onglet PARAMETRES ↔ PropertiesService
│   ├── SheetReader.gs             # Lignes du Sheet → JSON générique
│   ├── ApiClient.gs                # Appel de l'API de génération
│   ├── Drive.gs                     # Dernier export généré
│   ├── Triggers.gs                   # Déclencheur hebdomadaire
│   ├── Code.gs                        # Orchestration (menu + trigger)
│   └── appsscript.json
├── examples/events.demo.json  # Jeu de données de démonstration
├── docs/GOOGLE_SHEET_MAPPING.md
├── docker-compose.yml
├── Makefile
└── README.md
```

Le moteur Python **ne dépend jamais de Google Sheets**. Il reçoit un JSON
propre et ne sait rien d'autre. C'est Apps Script qui fait toute la
traduction Sheet → JSON.

## 3. Flux complet

```
L'équipe remplit le Google Sheet
        ↓
Déclencheur hebdomadaire (Apps Script)
        ↓
Lecture des lignes du Sheet, conversion en JSON
        ↓
Appel de l'API POST /api/v1/carousels/generate
        ↓
Le moteur Python valide, normalise, trie, groupe par jour, pagine,
choisit une mise en page, génère le HTML, l'exporte en PNG (Playwright),
crée le ZIP
        ↓
Fichiers déposés (aujourd'hui : localement / demain : Google Drive)
        ↓
L'URL de téléchargement est stockée, un email de notification est envoyé
```

Un bouton manuel (**Générer maintenant** / **Régénérer le dernier**) sert
uniquement de secours pour les ajouts de dernière minute.

## 4. Lancement local

### Sans Docker

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium   # télécharge Chromium si nécessaire

cp .env.example .env          # puis éditez NUIT_BLANCHE_API_KEY

uvicorn app.main:app --reload --port 8000
```

Ou via le Makefile (à la racine du projet) :

```bash
make install
make run
```

Testez :

```bash
curl http://localhost:8000/health
```

### Avec Docker

```bash
docker compose up --build
curl http://localhost:8000/health
```

> Le conteneur utilise `python:3.12-slim` + `playwright install --with-deps
> chromium`, donc Chromium est déjà présent dedans — aucune étape
> supplémentaire nécessaire.

## 5. Variables d'environnement

Voir `backend/.env.example`. Toutes préfixées `NUIT_BLANCHE_` :

| Variable                                  | Rôle                                                   |
|--------------------------------------------|---------------------------------------------------------|
| `NUIT_BLANCHE_API_KEY`                      | Secret attendu dans le header `X-API-Key` sur les routes protégées. Obligatoire.  |
| `NUIT_BLANCHE_DOWNLOAD_URL_SECRET`          | Secret HMAC dédié pour signer les URL de téléchargement ouvertes dans le navigateur. |
| `NUIT_BLANCHE_DOWNLOAD_URL_TTL_SECONDS`     | Durée de validité d'une URL signée de téléchargement (défaut 86400s / 24h). |
| `NUIT_BLANCHE_MAX_PAYLOAD_BYTES`             | Taille max du corps JSON accepté (défaut ~2 Mo).          |
| `NUIT_BLANCHE_GENERATION_TIMEOUT_SECONDS`     | Timeout d'une génération (défaut 60s).                    |
| `NUIT_BLANCHE_GENERATED_DIR`                   | Dossier racine du stockage local.                         |
| `NUIT_BLANCHE_SLIDE_WIDTH` / `_SLIDE_HEIGHT`    | Format du visuel (1080 × 1350 par défaut).                 |
| `NUIT_BLANCHE_CHROMIUM_EXECUTABLE_PATH`         | Chemin optionnel vers un Chromium système (rarement utile). |
| `NUIT_BLANCHE_LOG_LEVEL`                         | Niveau de log.                                              |

Aucun secret n'est jamais écrit en dur dans le code.

## 6. Génération de démonstration

Un jeu de données réaliste (`examples/events.demo.json`) couvre : un jour
avec peu d'événements, un jour avec beaucoup d'événements (pagination
automatique au-delà de 8), un titre très long, une affiche absente, un
tarif absent, et un événement mis en avant.

```bash
cd backend
source .venv/bin/activate
python -m scripts.generate_demo
```

Ou : `make demo`. Les PNG, le `manifest.json` et le ZIP sont écrits dans
`backend/generated/<generation_id>/`.

Avec l'API démarrée, la même génération est aussi disponible en HTTP :

```bash
curl -X POST http://localhost:8000/api/v1/carousels/generate \
  -H "X-API-Key: <votre clé>" \
  -H "Content-Type: application/json" \
  --data @examples/events.demo.json
```

La réponse conserve l'ancien contrat Apps Script et ajoute un contrat
orienté fichiers individuels. Elle contient notamment :

- `download_url` : ancien lien ZIP signé, conservé
- `files` : ancienne liste de noms PNG, conservée
- `file_downloads` : nouvelles URLs signées par PNG
- `manifest_url` : URL signée du `manifest.json`
- `zip_download_url` : alias explicite du lien ZIP signé

Les URLs absolues ont cette forme :

```text
https://votre-domaine/api/v1/carousels/<generation_id>/download?exp=<timestamp>&sig=<signature-hex>
```

Cette URL est directement ouvrable dans un navigateur sans header `X-API-Key`.
Seule la route `POST /api/v1/carousels/generate` reste protégée pour lancer une
génération ; la route de téléchargement ne devient publique qu'avec une
signature HMAC valide et non expirée.

Les téléchargements PNG individuels utilisent cette route :

```text
https://votre-domaine/api/v1/carousels/<generation_id>/files/<filename>?exp=<timestamp>&sig=<signature-hex>
```

## 7. Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Les tests couvrent : validation des événements, tri chronologique,
groupement par jour, pagination, sélection de template selon la densité,
génération des noms de fichiers, authentification API, la route de
génération de bout en bout (vrais PNG + `manifest.json` + ZIP), la
signature des URL de téléchargement par ZIP et par fichier, et la création
du ZIP. Aucun test ne dépend d'un vrai compte Google.

## 8. Installation future dans Google Sheets

1. Ouvrir le Google Sheet de l'équipe → **Extensions → Apps Script**.
2. Créer un fichier `.gs` par fichier de `google-apps-script/` (mêmes noms)
   et copier leur contenu. Remplacer le `appsscript.json` du projet Apps
   Script (onglet **Aperçu du manifeste** dans l'éditeur, ou via `clasp`)
   par celui du dossier.
3. Recharger le Sheet : le menu **Nuit Blanche** apparaît automatiquement
   (`onOpen()`).
4. Remplir l'onglet **PARAMETRES** (créé automatiquement au premier appel) :
   URL de l'API, clé API, dossier Drive, jour/heure de génération, jours à
   inclure, email de notification, fuseau horaire, ville, identifiant
   Instagram.
5. Adapter `SheetReader.gs` au vrai onglet d'événements — voir
   `docs/GOOGLE_SHEET_MAPPING.md`.

## 9. Création du déclencheur hebdomadaire

Après avoir rempli l'onglet PARAMETRES :

1. Dans l'éditeur Apps Script, sélectionner la fonction
   `installWeeklyTrigger` (fichier `Triggers.gs`) et cliquer **Exécuter**.
2. Autoriser les permissions demandées (Sheets, Drive, requêtes externes,
   envoi d'email).
3. Le déclencheur hebdomadaire est créé au jour/heure définis dans
   PARAMETRES ; il appelle `generateCarouselNow()` automatiquement.

Pour changer le jour/l'heure : modifier PARAMETRES puis relancer
`installWeeklyTrigger` (il supprime l'ancien déclencheur avant d'en créer
un nouveau).

## 10. Futur déploiement sur Cloud Run (ou Coolify)

Le moteur est déjà conteneurisé, donc :

- **Cloud Run** : `gcloud run deploy --source backend --set-env-vars
  NUIT_BLANCHE_API_KEY=...` (ou via Cloud Build). Monter un volume ou
  brancher `GoogleDriveStorageProvider` avant la mise en production, sinon
  le stockage local ne survit pas aux redéploiements Cloud Run.
- **Coolify** : pointer sur le `Dockerfile` de `backend/`, définir les
  variables d'environnement `NUIT_BLANCHE_*`, exposer le port 8000.

Dans les deux cas, mettre à jour l'onglet PARAMETRES (`URL de l'API`) avec
l'URL publique obtenue.

## 11. Futur transfert du projet au client

- Le client récupère la clé API (`NUIT_BLANCHE_API_KEY`) et le secret de
  signature (`NUIT_BLANCHE_DOWNLOAD_URL_SECRET`) via un canal sécurisé,
  jamais par email en clair.
- Transférer l'accès au projet Apps Script (ou le dupliquer dans le Sheet
  du client) et au dépôt du moteur Python.
- Documenter l'URL de production dans PARAMETRES avant la passation.
- `GoogleDriveStorageProvider` (actuellement un stub documenté dans
  `backend/app/storage/google_drive.py`) est le morceau à finaliser pour
  que les fichiers atterrissent directement dans le Drive du client.

## 12. À adapter à la réception du vrai Google Sheet

- `EVENTS_SHEET_NAME` et `COLUMN_MAPPING` dans
  `google-apps-script/SheetReader.gs` (voir
  `docs/GOOGLE_SHEET_MAPPING.md`).
- Si plusieurs villes/onglets : adapter `readEventsFromSheet_()`. Le
  backend dérive désormais `week_number` depuis `week.startDate` en ISO et
  injecte `city` depuis `NUIT_BLANCHE_CITY`.
- Les vraies polices, le logo Nuit Blanche et les vraies affiches
  remplaceront les polices système et les placeholders générés
  (`app/static/css/styles.css`, `app/services/text_utils.py`).
- Le `DRIVE_FOLDER_ID` réel et l'implémentation de
  `GoogleDriveStorageProvider` une fois le compte de service configuré.

## Ce qui fonctionne réellement

- Moteur Python complet : validation, normalisation, tri, groupement,
  pagination, choix de template, rendu Jinja2 → Playwright → PNG 1080×1350,
  stockage individuel des slides, `manifest.json`, ZIP de compatibilité,
  API FastAPI (`/health`, `/version`, génération, statut, téléchargement),
  authentification par clé API sur les routes protégées, URL de
  téléchargement signées, limite de taille de payload, timeout de
  génération, suite pytest verte.
- `LocalStorageProvider` (stockage réel sur disque).
- Script de démonstration (`generate_demo.py`) — produit réellement des
  PNG et un ZIP, vérifié dans ce dépôt.
- Squelette Apps Script complet et modulaire (menu, config, lecture Sheet,
  appel API, déclencheur, notification, dernier export).

## Ce qui reste un stub / à finaliser

- `GoogleDriveStorageProvider` (`backend/app/storage/google_drive.py`) :
  lève `NotImplementedError`, documente précisément ce qu'il faut pour le
  rendre réel.
- Le build/exécution Docker n'a pas pu être vérifié dans l'environnement
  qui a produit ce squelette (démon Docker indisponible dans ce
  bac à sable) — à valider avec `docker compose up --build` sur une
  machine avec Docker fonctionnel.
- Polices réelles, logo, vraies affiches : actuellement polices système et
  placeholders SVG générés.
- `EVENTS_SHEET_NAME` / `COLUMN_MAPPING` : génériques, à adapter au vrai
  Sheet (point 12 ci-dessus).
