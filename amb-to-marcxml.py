#!/usr/bin/env python3
"""AMB JSON  →  Dublin Core (intern)  →  MARCXML und/oder MARC21 binär (ISO 2709)

Konvertierungspipeline:
  1. AMB-Einträge (JSON-LD, Schema.org) aus oma-amb.json einlesen
  2. Felder auf Dublin Core Elements abbilden (intermediäre Struktur)
  3. Dublin Core auf MARC21-Felder abbilden und als MARCXML ausgeben
  4. Optional: MARC21 binär (ISO 2709, .mrc) ausgeben

Mapping-Übersicht: docs/AMB-zu-MARC21.md
"""

import argparse
import json
import re
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

MARC_NS = "http://www.loc.gov/MARC21/slim"
MARC_SCHEMA = "http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd"

LANG_TO_MARC = {
    "de": "ger", "en": "eng", "fr": "fre",
    "es": "spa", "it": "ita", "nl": "dut",
}


# ---------------------------------------------------------------------------
# Stufe 1: AMB → Dublin Core
# ---------------------------------------------------------------------------

def amb_to_dublin_core(entry: dict) -> dict:
    """Bildet einen AMB-Eintrag auf ein Dublin-Core-Dict ab."""
    creators = entry.get("creator", [])
    creator_names = [c["name"] for c in creators if c.get("name")]

    contributors = entry.get("contributor", [])
    creator_set = set(creator_names)
    contributor_names = [
        c["name"] for c in contributors
        if c.get("name") and c["name"] not in creator_set
    ]

    publishers = entry.get("publisher", [])
    publisher_names = [p["name"] for p in publishers if p.get("name")]

    keywords = list(entry.get("keywords", []))
    for about in entry.get("about", []):
        if about.get("id"):
            keywords.append(about["id"])

    types = list(entry.get("type", []))
    for lrt in entry.get("learningResourceType", []):
        label = (
            lrt.get("prefLabel", {}).get("de")
            or lrt.get("prefLabel", {}).get("en", "")
        )
        if label:
            types.append(label)

    license_obj = entry.get("license", {})
    rights = license_obj.get("id", "") if isinstance(license_obj, dict) else ""

    return {
        "title":       entry.get("name", ""),
        "creator":     creator_names,
        "contributor": contributor_names,
        "publisher":   publisher_names,
        "description": entry.get("description", ""),
        "subject":     keywords,
        "date":        entry.get("datePublished") or entry.get("dateCreated") or "",
        "language":    entry.get("inLanguage", []),
        "rights":      rights,
        "identifier":  entry.get("id", ""),
        "type":        types,
    }


# ---------------------------------------------------------------------------
# Stufe 2: Dublin Core → MARCXML
# ---------------------------------------------------------------------------

def _sf(parent: ET.Element, code: str, value: str) -> None:
    """Fügt ein MARC-Subfeld hinzu."""
    sf = ET.SubElement(parent, f"{{{MARC_NS}}}subfield", code=code)
    sf.text = value


def _df(record: ET.Element, tag: str, ind1: str = " ", ind2: str = " ") -> ET.Element:
    """Fügt ein Datenfeld zum Record hinzu und gibt es zurück."""
    return ET.SubElement(record, f"{{{MARC_NS}}}datafield",
                         tag=tag, ind1=ind1, ind2=ind2)


def _cf(record: ET.Element, tag: str, value: str) -> None:
    """Fügt ein Kontrollfeld zum Record hinzu."""
    cf = ET.SubElement(record, f"{{{MARC_NS}}}controlfield", tag=tag)
    cf.text = value


def _parse_year(date_str: str) -> str:
    if not date_str:
        return "    "
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return str(dt.year)
    except Exception:
        return date_str[:4] if len(date_str) >= 4 else "    "


def _build_008(date_str: str, languages: list) -> str:
    """Erzeugt das 008-Feld (40 Zeichen) für eine Online-Textressource."""
    entry_date = datetime.now(timezone.utc).strftime("%y%m%d")
    year = _parse_year(date_str)

    lang_code = LANG_TO_MARC.get(languages[0], "ger") if languages else "ger"

    # Positionen (MARC 008/Books-Schema für Monographien):
    # 00-05  Eingabedatum
    # 06     Datumstyp  s = einfaches Datum
    # 07-10  Erscheinungsjahr
    # 11-14  zweites Datum (leer)
    # 15-17  Erscheinungsland  xx = unbekannt
    # 18-21  Illustrationen
    # 22     Zielgruppe
    # 23     Erscheinungsform  o = Online-Ressource
    # 24-27  Art des Inhalts
    # 28     staatliche Publikation  ' '
    # 29     Konferenzbeitrag  0
    # 30     Festschrift  0
    # 31     Index  0
    # 32     leer
    # 33     Literarische Form  0
    # 34     Biografie  ' '
    # 35-37  Sprachcode
    # 38     geänderter Datensatz  ' '
    # 39     Katalogisierungsquelle  d
    # 40 Zeichen, Positionen exakt nach MARC-Spezifikation (Books-Schema):
    # 00-05 Eingabe | 06 Datumstyp | 07-10 Jahr | 11-14 leer |
    # 15-17 Land | 18-22 leer | 23 Form(o=Online) | 24-28 leer |
    # 29-31 Konf/Festschr/Index | 32 undef | 33 LitForm | 34 Bio |
    # 35-37 Sprache | 38 geändert | 39 Quelle
    field = f"{entry_date}s{year}    xx      o     000 0 {lang_code} d"
    return field[:40].ljust(40)


def dc_to_marc_record(dc: dict, seq: int) -> ET.Element:
    """Erzeugt einen MARC21-Record-Element aus einem Dublin-Core-Dict."""
    record = ET.Element(f"{{{MARC_NS}}}record")

    # --- Leader -------------------------------------------------------
    leader = ET.SubElement(record, f"{{{MARC_NS}}}leader")
    # nam = Sprachtext (a), Monografie (m), Unicode (a)
    leader.text = "00000nam a2200000   4500"

    # --- Kontrollfelder -----------------------------------------------
    rec_id = re.sub(r".*/", "", dc["identifier"]) or str(seq)
    _cf(record, "001", rec_id)
    _cf(record, "003", "DE-OMA")   # Vergabe-Institution
    _cf(record, "007", "cr")       # c=elektronische Ressource, r=Fernzugriff
    _cf(record, "008", _build_008(dc["date"], dc["language"]))

    # --- Datenfelder --------------------------------------------------

    # 040  Katalogisierungsquelle
    df = _df(record, "040")
    _sf(df, "a", "DE-OMA")
    _sf(df, "b", "ger")
    _sf(df, "e", "rda")

    # 041  Sprachcode
    if dc["language"]:
        df = _df(record, "041", ind1="0")
        for lang in dc["language"]:
            _sf(df, "a", LANG_TO_MARC.get(lang, lang))

    # 100  Haupteintrag – Personenname (erster Urheber)
    if dc["creator"]:
        df = _df(record, "100", ind1="1")
        _sf(df, "a", dc["creator"][0])
        _sf(df, "e", "Verfasser/in")
        _sf(df, "4", "aut")

    # 245  Titel
    ind1 = "1" if dc["creator"] else "0"
    df = _df(record, "245", ind1=ind1, ind2="0")
    title = dc["title"]
    _sf(df, "a", title if title.endswith(".") else title + " /")
    if dc["creator"]:
        _sf(df, "c", " ; ".join(dc["creator"]))

    # 264  Erscheinungsvermerk (RDA)
    df = _df(record, "264", ind2="1")
    _sf(df, "a", "[o.O.]")
    _sf(df, "b", dc["publisher"][0] if dc["publisher"] else "[o.V.]")
    year = _parse_year(dc["date"])
    _sf(df, "c", year if year.strip() else "[o.J.]")

    # 336/337/338  RDA Inhalts-/Medien-/Datenträgertyp
    df = _df(record, "336")
    _sf(df, "a", "Text"); _sf(df, "b", "txt"); _sf(df, "2", "rdacontent")

    df = _df(record, "337")
    _sf(df, "a", "Computermedien"); _sf(df, "b", "c"); _sf(df, "2", "rdamedia")

    df = _df(record, "338")
    _sf(df, "a", "Online-Ressource"); _sf(df, "b", "cr"); _sf(df, "2", "rdacarrier")

    # 520  Zusammenfassung
    if dc["description"]:
        df = _df(record, "520")
        _sf(df, "a", dc["description"])

    # 540  Nutzungsbedingungen / Lizenz
    if dc["rights"]:
        df = _df(record, "540")
        _sf(df, "a", dc["rights"])

    # 650  Schlagwort (freie Vergabe, ind2=4)
    # 653  Nicht-kontrolliertes Schlagwort (für URIs aus about[])
    for kw in dc["subject"]:
        if kw.startswith("http"):
            df = _df(record, "653")
            _sf(df, "a", kw)
        else:
            df = _df(record, "650", ind2="4")
            _sf(df, "a", kw)

    # 655  Genre-/Formbezeichnung (Ressourcentypen aus AMB)
    for t in dc["type"]:
        df = _df(record, "655", ind2="4")
        _sf(df, "a", t)

    # 700  Nebeneintrag – weitere Urheber und Beitragende
    for name in dc["creator"][1:]:
        df = _df(record, "700", ind1="1")
        _sf(df, "a", name); _sf(df, "e", "Verfasser/in"); _sf(df, "4", "aut")

    for name in dc["contributor"]:
        df = _df(record, "700", ind1="1")
        _sf(df, "a", name); _sf(df, "e", "Mitwirkende/r"); _sf(df, "4", "ctb")

    # 856  Elektronische Adresse (URL)
    if dc["identifier"]:
        df = _df(record, "856", ind1="4", ind2="0")
        _sf(df, "u", dc["identifier"])
        _sf(df, "z", "Kostenfrei")

    return record


# ---------------------------------------------------------------------------
# Stufe 3: MARCXML-Record → binäres MARC21 (ISO 2709)
# ---------------------------------------------------------------------------

_FT = b'\x1e'   # Field Terminator
_RT = b'\x1d'   # Record Terminator
_SD = b'\x1f'   # Subfield Delimiter


def _marc_field_bytes(child: ET.Element) -> tuple[str, bytes]:
    """Gibt (tag, rohe Feldbytes inkl. Feldterminator) zurück."""
    local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
    tag = child.get('tag', '')

    if local == 'controlfield':
        content = (child.text or '').encode('utf-8') + _FT
        return tag, content

    if local == 'datafield':
        ind1 = (child.get('ind1', ' ')).encode('utf-8')
        ind2 = (child.get('ind2', ' ')).encode('utf-8')
        sf_data = b''
        for sf in child:
            sf_local = sf.tag.split('}')[-1] if '}' in sf.tag else sf.tag
            if sf_local == 'subfield':
                code = sf.get('code', 'a').encode('utf-8')
                text = (sf.text or '').encode('utf-8')
                sf_data += _SD + code + text
        return tag, ind1 + ind2 + sf_data + _FT

    return '', b''


def record_to_iso2709(record: ET.Element) -> bytes:
    """Serialisiert einen MARCXML-Record als ISO-2709-Bytes."""
    leader_text = "00000nam a2200000   4500"
    raw_fields: list[tuple[str, bytes]] = []

    for child in record:
        local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if local == 'leader':
            leader_text = (child.text or leader_text).ljust(24)
        elif local in ('controlfield', 'datafield'):
            tag, data = _marc_field_bytes(child)
            if tag:
                raw_fields.append((tag, data))

    # Verzeichnis und Datenportion aufbauen
    directory = b''
    data_portion = b''
    pos = 0
    for tag, content in raw_fields:
        length = len(content)
        directory += tag.encode('utf-8') + f'{length:04d}{pos:05d}'.encode('utf-8')
        data_portion += content
        pos += length

    directory += _FT
    data_portion += _RT

    base_addr = 24 + len(directory)
    total_len = base_addr + len(data_portion)

    # Leader aktualisieren: Länge (0-4), Basisadresse (12-16)
    ldr = list(leader_text[:24])
    for i, c in enumerate(f'{total_len:05d}'):
        ldr[i] = c
    ldr[9] = 'a'   # UTF-8
    for i, c in enumerate(f'{base_addr:05d}'):
        ldr[12 + i] = c
    ldr[20:24] = list('4500')

    return ''.join(ldr).encode('utf-8') + directory + data_portion


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Konvertiert AMB JSON → Dublin Core → MARCXML (und optional .mrc)"
    )
    parser.add_argument("--input",      default="docs/oma-amb.json",
                        help="Pfad zur AMB-JSON-Datei")
    parser.add_argument("--output",     default="docs/oma-marc21.xml",
                        help="Pfad der MARCXML-Ausgabedatei")
    parser.add_argument("--mrc-output", default="docs/oma-marc21.mrc",
                        help="Pfad der binären MARC21-Ausgabedatei (ISO 2709); "
                             "leer lassen um die MRC-Ausgabe zu überspringen")
    parser.add_argument("--limit",      type=int, default=None,
                        help="Maximale Anzahl Einträge (Standard: alle)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        amb_data = json.load(f)

    if args.limit:
        amb_data = amb_data[:args.limit]

    ET.register_namespace("marc", MARC_NS)
    collection = ET.Element(
        f"{{{MARC_NS}}}collection",
        attrib={
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{MARC_NS} {MARC_SCHEMA}",
        },
    )

    mrc_records: list[bytes] = []
    for i, entry in enumerate(amb_data, 1):
        dc = amb_to_dublin_core(entry)
        record = dc_to_marc_record(dc, i)
        collection.append(record)
        if args.mrc_output:
            mrc_records.append(record_to_iso2709(record))

    tree = ET.ElementTree(collection)
    ET.indent(tree, space="  ", level=0)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    print(f"MARCXML erzeugt: {args.output} ({len(amb_data)} Datensätze)")

    if args.mrc_output:
        with open(args.mrc_output, 'wb') as f:
            for rec in mrc_records:
                f.write(rec)
        print(f"MARC21 binär erzeugt: {args.mrc_output} ({len(mrc_records)} Datensätze)")


if __name__ == "__main__":
    main()
