# OMA AMB → RSS Feed

Automatisierter wöchentlicher Export der [Open Music Academy](https://openmusic.academy) Inhaltsmetadaten im AMB-Format als öffentlich abrufbarer RSS-Feed via GitHub Pages.

## Öffentliche URLs

| Datei | Beschreibung |
|-------|--------------|
| `docs/oma-amb.json` | Rohdaten im AMB-Format (JSON) |
| `docs/oma-feed.xml` | RSS-Feed (XML) für MUNDO u.a. |
| `docs/oma-marc21.xml` | MARCXML (MARC21) für Bibliothekssysteme |

Nach Aktivierung von GitHub Pages erreichbar unter:
```
https://<org>.github.io/<repo>/oma-amb.json
https://<org>.github.io/<repo>/oma-feed.xml
https://<org>.github.io/<repo>/oma-marc21.xml
```

## Setup (einmalig)

### 1. Repository Secret anlegen

`Settings → Secrets and variables → Actions → New repository secret`

| Name | Wert |
|------|------|
| `OMA_API_KEY` | API-Key der openmusic.academy |

### 2. GitHub Pages aktivieren

`Settings → Pages → Source: Deploy from branch → Branch: main → Folder: /docs`

### 3. Workflow manuell anstoßen (erster Lauf)

`Actions → Update OMA Feed → Run workflow`

## Automatischer Ablauf

Der Workflow läuft **jeden Montag um 05:00 UTC** und:

1. Lädt `oma-amb.json` von der OMA API herunter (Secret wird nie geloggt)
2. Konvertiert mit `amb-to-rss.py` in `oma-feed.xml`
3. Konvertiert mit `amb-to-marcxml.py` in `oma-marc21.xml`
4. Committed alle drei Dateien in `docs/` und pusht

Falls sich nichts geändert hat, wird kein leerer Commit erzeugt.

## Lokale Ausführung

```bash
# amb.json manuell laden
curl -H "x-api-key: DEIN_KEY" https://openmusic.academy/api/v1/amb/metadata -o docs/oma-amb.json

# RSS-Feed erzeugen
python amb-to-rss.py --input docs/oma-amb.json --output docs/oma-feed.xml

# MARCXML erzeugen
python amb-to-marcxml.py --input docs/oma-amb.json --output docs/oma-marc21.xml
```
