import os
import json
import urllib.request
import urllib.error
import argparse

API_URL = "https://openmusic.academy/api/v1/amb/metadata"

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="docs/oma-amb.json")
args = parser.parse_args()

api_key = os.environ.get("OMA_API_KEY")
if not api_key:
    raise SystemExit("Fehler: Umgebungsvariable OMA_API_KEY nicht gesetzt.")

req = urllib.request.Request(API_URL, headers={"x-api-key": api_key})

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    raise SystemExit(f"HTTP-Fehler: {e.code} {e.reason}")

entries = data if isinstance(data, list) else (data.get("data") or data.get("items") or [])

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f"Gespeichert: {len(entries)} Einträge → {args.output}")
