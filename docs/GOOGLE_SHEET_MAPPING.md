# Mapping Google Sheet → modèle interne

Ce document explique comment relier les colonnes du **vrai** Google Sheet
(quand nous l'aurons) au format JSON générique attendu par le moteur Python
(`backend/app/schemas/events.py`).

## Le principe

Le moteur Python ne connaît jamais le Google Sheet. Il reçoit uniquement un
JSON propre (`WeekRequest`). C'est `google-apps-script/SheetReader.gs` qui
fait la traduction, ligne par ligne, colonne par colonne, en s'appuyant sur
l'en-tête de chaque colonne (pas sa position) :

```
Ligne du Sheet  →  SheetReader.gs (COLUMN_MAPPING)  →  JSON EventIn  →  API  →  carrousel
```

## Ce qu'il faut adapter

Dans `google-apps-script/SheetReader.gs` :

1. **`EVENTS_SHEET_NAME`** — le nom de l'onglet contenant les événements
   (actuellement `EVENEMENTS`, à remplacer par le vrai nom).
2. **`COLUMN_MAPPING`** — un objet `{ "En-tête du Sheet": "champ_interne" }`.

Exemple donné dans le brief initial :

```json
{
  "ID_EVENEMENT": "id",
  "DATE": "date",
  "HEURE_DEBUT": "start_time",
  "HEURE_FIN": "end_time",
  "LIEU": "venue",
  "ID_LIEU": "venue_id",
  "TYPE_EVENEMENT": "type",
  "NOM_EVENEMENT": "event_name",
  "ARTISTES_PROGRAMMATION": "artists",
  "PRIX_FINAL": "price",
  "VISUEL_DRIVE_URL": "visual_url",
  "SOURCE_URL": "source_url",
  "MISE_EN_AVANT": "featured",
  "STATUT": "status"
}
```

Il suffit de changer les clés (les libellés à gauche) pour qu'elles
correspondent exactement aux en-têtes réels du Sheet — les valeurs à droite
(les noms de champs internes) ne doivent normalement pas changer, sauf si le
schéma Pydantic évolue.

## Champs internes disponibles

| Champ interne  | Obligatoire | Type attendu                        | Notes |
|----------------|:-----------:|--------------------------------------|-------|
| `id`           | oui         | texte                                | Identifiant du Sheet (ex. `EVT-0001`). |
| `date`         | oui         | date (`AAAA-MM-JJ`)                  | Si la colonne du Sheet est au format date natif, la conversion est automatique. |
| `start_time`   | non         | heure (`HH:MM`)                      | Idem pour les colonnes heure natives. |
| `end_time`     | non         | heure (`HH:MM`)                      | Absent si pas de colonne "Horaire fin". |
| `venue`        | oui         | texte                                | Lieu de l'événement. |
| `venue_id`     | non         | texte                                | Identifiant du lieu (ex. `CAI`, `COS`). |
| `type`         | oui         | texte                                | Type d'événement. Sert aussi à choisir la couleur du placeholder d'affiche. |
| `event_name`   | oui         | texte                                | Titre affiché (raccourci automatiquement si trop long). |
| `artists`      | non         | texte                                | Artistes, DJ, groupes ou intervenants. |
| `price`        | non         | texte libre (ex. `"12€"`, `"Gratuit"`) | Utiliser `PRIX_FINAL` du Sheet. Si absent : `"Tarif non communiqué"` sur le visuel. |
| `visual_url`   | non         | URL                                  | URL de l'affiche sur Drive. Si absent : placeholder généré automatiquement. |
| `source_url`   | non         | URL                                  | Instagram, billetterie ou site source (informatif, non affiché). |
| `featured`     | non         | booléen                              | Priorité éditoriale (`MISE_EN_AVANT`). `"oui"` / `"true"` / `"1"` / case cochée → `true`. |
| `status`       | non         | texte                                | Statut de l'événement (`Validé`, `Brouillon`, `À vérifier`). Apps Script filtre avant envoi. |

## Étapes concrètes à la réception du vrai Sheet

1. Ouvrir le Sheet, repérer le nom exact de l'onglet des événements.
2. Relever les en-têtes de colonnes exacts (attention aux accents/espaces).
3. Mettre à jour `EVENTS_SHEET_NAME` et `COLUMN_MAPPING` dans
   `google-apps-script/SheetReader.gs`.
4. Si le Sheet a plusieurs onglets par ville/édition, adapter
   `readEventsFromSheet_()` en conséquence (ex. lire plusieurs onglets, ou
   filtrer par colonne "Ville").
5. Lancer **Nuit Blanche → Générer le carrousel maintenant** une première
   fois pour valider le mapping sur des données réelles.
6. Si des colonnes n'existent pas encore côté Sheet (ex. affiche, tarif),
   elles peuvent rester non mappées : ces champs sont optionnels côté API.

## Ce qui ne change jamais

Le schéma JSON (`backend/app/schemas/events.py`) et tout le moteur de rendu
sont indépendants du Sheet. Changer le mapping ne nécessite **aucune**
modification côté Python.
