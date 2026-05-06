import os
import json
import urllib.request
import urllib.error
import argparse

API_URL = "https://openmusic.academy/api/v1/amb/metadata"
PAGE_SIZE = 100

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="docs/oma-amb.json")
args = parser.parse_args()

api_key = os.environ.get("OMA_API_KEY")
if not api_key:
    raise SystemExit("Fehler: Umgebungsvariable OMA_API_KEY nicht gesetzt.")

all_entries = []
page = 1

while True:
    url = f"{API_URL}?page={page}&pageSize={PAGE_SIZE}"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP-Fehler auf Seite {page}: {e.code} {e.reason}")

    # API kann Array oder {data: [...]} zurückgeben
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = data.get("data") or data.get("items") or data.get("results") or []
    else:
        entries = []

    all_entries.extend(entries)
    print(f"Seite {page}: {len(entries)} Einträge (gesamt: {len(all_entries)})")

    if len(entries) < PAGE_SIZE:
        break
    page += 1

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(all_entries, f, ensure_ascii=False, indent=2)

print(f"Gespeichert: {len(all_entries)} Einträge → {args.output}")
