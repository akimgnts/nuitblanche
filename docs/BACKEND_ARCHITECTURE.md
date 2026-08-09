# Architecture Backend - Nuit Blanche Carousel Generator

## Vue d'ensemble

Le backend est un service FastAPI qui transforme une semaine d'événements (JSON) en carrousel de slides Instagram (PNG).

```
Google Sheets (Apps Script)
        ↓
   POST /api/v1/carousels/generate
        ↓
   WeekRequest JSON
        ↓
   GenerationService
        ├─ Normalize events
        ├─ Sort by date/time
        ├─ Group by day
        ├─ Paginate (8 per slide)
        ├─ Render Jinja2 templates
        ├─ Screenshot Playwright
        ├─ Finalize PNGs
        └─ Store + ZIP
        ↓
   Files générés + URLs
```

## Flux de données

### 1. Entrée: WeekRequest JSON

Apps Script envoie exactement cette structure:

```json
{
  "project": "nuit-blanche",
  "template": "nuit-blanche",
  "week": {
    "label": "Semaine 29 – du 16/07/2026 au 22/07/2026",
    "startDate": "2026-07-16",
    "endDate": "2026-07-22"
  },
  "options": {
    "statuses": ["Validé"],
    "sort": ["date", "startTime", "venue"]
  },
  "events": [
    {
      "id": "EVT-0001",
      "date": "2026-07-16",
      "dateLabel": "Jeudi 16 juillet",
      "venue": "3 Brasseurs",
      "venueId": "3BR",
      "type": "Concert",
      "eventName": "Concert variétés",
      "artists": "Artiste invité",
      "startTime": "20:00",
      "endTime": "22:00",
      "price": "Consommation",
      "visualUrl": "https://drive.google.com/...",
      "featured": true,
      "status": "Validé",
      "sourceUrl": "https://instagram.com/..."
    }
  ]
}
```

**Validation**: Pydantic valide structure + types.

**Adaptation**: la route convertit ce payload externe vers un modèle interne unique.
`city` est injectée depuis `NUIT_BLANCHE_CITY` (défaut `Le Havre`) et
`week_number` est calculé en ISO depuis `week.startDate`.

### 2. Pipeline GenerationService

```python
def generate(request: WeekRequest) -> GenerationRecord:
    # Étape 1: Normalisation
    normalized = normalize_events(request.events)
    # → EventIn → NormalizedEvent (display-only fields)
    
    # Étape 2: Tri
    sorted_events = sort_events(normalized)
    # → date + start_time
    
    # Étape 3: Groupement par jour
    grouped = group_by_day(sorted_events)
    # → dict[date] = [NormalizedEvent]
    
    # Étape 4: Construction des slides
    day_slides = build_day_slides(grouped)
    # → [DaySlide(day, template, events)]
    
    # Étape 5: Rendu + Screenshot
    with ScreenshotRenderer(...) as screenshot:
        # Cover slide
        screenshot.capture(_render_cover(...), cover_path)
        
        # Day slides
        for slide in day_slides:
            screenshot.capture(_render_day(...), slide_path)
        
        # Outro slide
        screenshot.capture(_render_outro(...), outro_path)
    
    # Étape 6: Stockage
    stored = storage.store(...)
```

### 3. Normalisation (EventIn → NormalizedEvent)

**EventIn** (schéma brut Apps Script):
- `id`, `date`, `dateLabel`, `venue`, `venueId`, `type`, `eventName`
- `artists`, `startTime`, `endTime`, `price`, `visualUrl`
- `featured`, `status`, `sourceUrl`

**NormalizedEvent** (prêt pour rendu):
```python
@dataclass
class NormalizedEvent:
    external_id: str
    date: Date
    start_time: Time | None
    venue: str
    category: str           # mappé de `type`
    title: str              # mappé de `event_name`
    title_display: str      # tronqué si >60 chars
    artist: str | None      # mappé de `artists`
    artist_display: str     # tronqué si >50 chars
    price_display: str      # valeur de `price`, sinon "Tarif non communiqué"
    poster_url: str | None  # data: URL locale après téléchargement backend
    placeholder_color: str  # basé sur `category`
    poster_label: str       # tronqué si >34 chars
    featured: bool
```

**Avantages**:
- Séparation données brutes / données affichage
- Truncation automatique (évite débordement visuel)
- Couleurs placeholder générées une fois

### 4. Tri

**Ordre final**:
1. `featured == true` en premier
2. Puis par `date` croissante
3. Puis par `start_time` croissante

```python
def sort_events(events: list[NormalizedEvent]) -> list[NormalizedEvent]:
    return sorted(events, key=lambda e: (
        not e.featured,  # False (True) vient avant True (False)
        e.date,
        e.start_time or Time.max
    ))
```

### 5. Groupement par jour

```python
grouped = group_by_day(sorted_events)
# → OrderedDict[date] = [NormalizedEvent]
```

Résultat: événements organisés par jour, déjà triés.

### 6. Construction des slides

**DaySlide**:
```python
@dataclass
class DaySlide:
    day: date
    template: str     # "spacious" | "standard" | "compact"
    events: list[NormalizedEvent]
```

**Logique template** (densité):
- 1–4 événements: `spacious` (descriptions affichées)
- 5–6 événements: `standard`
- 7–8+ événements: `compact`

**Pagination**: Max 8 événements par slide (logique server-side ou client).

### 7. Rendu Jinja2 → HTML

**Cover** (`cover.html`):
- Week number
- City
- Date range
- Category tags (first appearance order, capped)
- Headline text

```jinja2
{{ week_number }}
{{ city }}
{{ period_label }}
{% for tag in category_tags %}<span>{{ tag }}</span>{% endfor %}
```

**Day** (`day.html`):
- Day name (weekday)
- Day date
- Events grid (max 8)
- Page number (`02 / 15`)

```jinja2
{{ day_name }}
{{ day_date_label }}
{% for event in events %}
  {% include "partials/event_card.html" %}
{% endfor %}
{{ page_label }}
```

**Event card** (`partials/event_card.html`):
- Poster (image ou placeholder coloré)
- Venue, category, artist/title
- Start time (if present)
- Price
- Featured flag (CSS class)

```jinja2
{% if event.poster_url %}
  <img src="{{ event.poster_url }}" />
{% else %}
  <div style="--poster-color: {{ event.placeholder_color }}">
    {{ event.poster_label }}
  </div>
{% endif %}
```

**Outro** (`outro.html`):
- Instagram handle
- Closing text
- Page number

### 8. Screenshot → PNG

**Playwright** capture HTML → PNG:
```python
with ScreenshotRenderer(width, height, chromium_path) as screenshot:
    screenshot.capture(html_string, output_path)
    finalize_png(output_path, width, height)
```

**Dimensions**:
- 1080×1350px (Instagram Stories)

**Finalization** (`finalize_png`):
- Optimisation metadata
- Compression

### 9. Stockage + ZIP

**LocalStorageProvider**:
```
generated/
  Le Havre/2026/
    semaine-29/
      01-cover.png
      02-jeudi.png
      03-vendredi.png
      ...
      semaine-29.zip
```

**GenerationRecord** (persisted):
```python
@dataclass
class GenerationRecord:
    generation_id: str      # UUID
    city: str
    week_number: int
    status: str             # "completed" | "error"
    slide_count: int
    files: list[str]        # noms PNG
    output_dir: Path
    zip_path: Path
    warnings: list[str]     # "Aucun événement", etc.
```

## Schémas Pydantic

### EventIn
Champs du JSON reçu:
```python
id: str                          # EVT-0001
date: Date
venue: str
venue_id: str | None             # optionnel
type: str                        # Concert, Exposition, etc.
event_name: str
artists: str | None
start_time: Time | None
end_time: Time | None
price: str | None
visual_url: str | None
featured: bool = False
status: str | None = "Validé"
source_url: str | None
```

### Week
```python
label: str                       # "Semaine 29 – du..."
start_date: Date                 # aliases: startDate
end_date: Date                   # aliases: endDate
```

### GenerationOptions
```python
statuses: list[str]
sort: list[str]
```

### WeekRequest
Payload complet envoyé par Apps Script:
```python
project: str = "nuit-blanche"
template: str = "nuit-blanche"
week: Week
options: GenerationOptions
events: list[EventIn]
```

### GenerationRequest
Modèle interne transmis au moteur existant:
```python
project: str
template: str
city: str                  # settings.city
week_number: int           # ISO depuis week.startDate
week: Week
options: GenerationOptions
events: list[EventIn]
instagram_handle: str | None
```

## Services

### GenerationService
Orchestrateur principal. Étapes:
1. Normalize
2. Sort
3. Group
4. Build day slides
5. Render (cover, days, outro)
6. Screenshot
7. Finalize
8. Store
9. Record metadata

### Normalizer
`EventIn` → `NormalizedEvent`:
- Truncate titles, artist, descriptions
- Compute placeholder colors
- Set price_display default

### Sorting
Tri par: date → time

### Grouping
Groupement par jour (OrderedDict)

### Layout
Construction des slides jour + pagination logique

### ScreenshotRenderer
Wrapper Playwright:
- Launch chromium
- Wait fonts + visible remote images before capture
- Capture HTML
- Save PNG

### Poster assets

Les affiches ne sont plus chargées depuis Google Drive par Playwright.
Le backend :

1. résout `mediaId` / `visualUrl`
2. télécharge l'image côté Python
3. valide `HTTP 200` + `Content-Type image/*`
4. stocke le fichier dans `generated/<generation_id>/assets/`
5. convertit le fichier en `data:` URL
6. injecte cette valeur dans `poster_url` pour le template

En cas d'échec, le backend logge `event_id`, `url`, `status`,
`content_type` et garde le fallback visuel existant.

### StorageProvider
Interface abstraite:
- `store(generation_id, city, week_number, year, png_paths, manifest_path, zip_path)` → StoredResult

**Implémentation**: `LocalStorageProvider` (filesystem)

### Sortie stockée

Chaque génération est persistée dans son propre dossier :

```text
generated/
  <generation_id>/
    manifest.json
    01-cover.png
    02-jeudi.png
    03-vendredi.png
    ...
    nuit-blanche-semaine-29.zip
```

## Route API

```
POST /api/v1/carousels/generate
Headers: X-API-Key: <token>
Body: WeekRequest JSON

Response 200:
{
  "success": true,
  "generation_id": "uuid",
  "status": "completed",
  "slide_count": 15,
  "download_url": "https://.../api/v1/carousels/{uuid}/download?exp=...&sig=...",
  "zip_download_url": "https://.../api/v1/carousels/{uuid}/download?exp=...&sig=...",
  "manifest_url": "https://.../api/v1/carousels/{uuid}/files/manifest.json?exp=...&sig=...",
  "files": ["01-cover.png", "02-jeudi.png", ...],
  "file_downloads": [
    {
      "index": 1,
      "name": "01-cover.png",
      "download_url": "https://.../api/v1/carousels/{uuid}/files/01-cover.png?exp=...&sig=..."
    }
  ],
  "warnings": []
}

Response 504: Timeout (>settings.generation_timeout_seconds)
Response 422: Validation error
```

Routes publiques signées :

```text
GET /api/v1/carousels/{generation_id}/download
GET /api/v1/carousels/{generation_id}/files/{filename}
```

Les deux exigent une signature HMAC valide (`exp`, `sig`) mais pas de
header `X-API-Key`.

## Configuration

**Settings** (`app/core/config.py`):
```python
slide_width: int = 1080
slide_height: int = 1350
chromium_executable_path: Path | None = None
generation_timeout_seconds: int = 120
generated_dir: Path = Path("generated/")
```

**Env vars**:
- `NUIT_BLANCHE_API_KEY`: clé API
- `NUIT_BLANCHE_GENERATION_TIMEOUT_SECONDS`: timeout

## Erreurs possibles

| Erreur | Cause | Réponse |
|--------|-------|--------|
| ValidationError | Schema violation | 422 |
| GenerationTimeoutError | Génération trop lente | 504 |
| GenerationNotFoundError | ID inexistant | 404 |
| FileNotFoundError | Visuel Drive manquant | Warning (placeholder) |

## Exemple complet

```python
# 1. Apps Script envoie
request_json = {
    "project": "nuit-blanche",
    "template": "nuit-blanche",
    "week": {
        "label": "Semaine 29 – du 16/07/2026 au 22/07/2026",
        "startDate": "2026-07-16",
        "endDate": "2026-07-22"
    },
    "options": {
        "statuses": ["Validé"],
        "sort": ["date", "startTime", "venue"]
    },
    "events": [
        {
            "id": "EVT-0001",
            "date": "2026-07-16",
            "dateLabel": "Jeudi 16 juillet",
            "venue": "3 Brasseurs",
            "type": "Concert",
            "eventName": "Concert variétés",
            "artists": "Artiste invité",
            "startTime": "20:00",
            "price": "Consommation",
            "featured": True,
            "status": "Validé"
        }
    ]
}

# 2. Backend adapte puis traite
payload = WeekRequest.model_validate(request_json)
request = to_generation_request(payload, settings)
record = service.generate(request)

# 3. Response
{
    "success": true,
    "generation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "completed",
    "slide_count": 4,
    "download_url": "https://.../download?exp=...&sig=...",
    "zip_download_url": "https://.../download?exp=...&sig=...",
    "manifest_url": "https://.../files/manifest.json?exp=...&sig=...",
    "files": ["01-cover.png", "02-jeudi.png", "03-vendredi.png", "04-outro.png"],
    "file_downloads": [
        {
            "index": 1,
            "name": "01-cover.png",
            "download_url": "https://.../files/01-cover.png?exp=...&sig=..."
        }
    ],
    "warnings": []
}

# 4. Les PNG sont disponibles individuellement
# 5. Le manifest.json est téléchargeable
# 6. Le ZIP reste disponible pour compatibilité
```

## Tests

**Unit tests**: `backend/tests/`
- `test_validation.py`: schémas Pydantic
- `test_sorting.py`: tri événements
- `test_grouping.py`: groupement par jour
- `test_pagination.py`: logique slides

**Integration test**: `test_generate_route.py`
- Request → Response complet
- Vérification ZIP, PNG filenames, manifest, URLs signées, compatibilité

## Déploiement

**Docker**:
```dockerfile
FROM python:3.11-slim
RUN apt-get install chromium
COPY . /app
RUN pip install -r requirements.txt && playwright install chromium
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Env vars production**:
- `NUIT_BLANCHE_API_KEY`
- `NUIT_BLANCHE_GENERATION_TIMEOUT_SECONDS`
- `NUIT_BLANCHE_GENERATED_DIR` (volume persistent)
