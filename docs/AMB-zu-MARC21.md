# AMB → Dublin Core → MARC21 (MARCXML)

Dokumentation der Konvertierungspipeline für OMA-Metadaten.  
Skript: [`amb-to-marcxml.py`](../amb-to-marcxml.py)

---

## Überblick

```
oma-amb.json
   │
   │  Stufe 1: AMB-Parsing
   ▼
Dublin Core (intern, Python-Dict)
   │
   │  Stufe 2: DC → MARC21-Mapping
   ▼
oma-marc21.xml  (MARCXML, valide gegen LOC-Schema)
```

Das Skript verwendet ausschließlich die Python-Standardbibliothek (`json`,
`xml.etree.ElementTree`) — keine externen Abhängigkeiten.

---

## Quellformat: AMB (Allgemeines Metadatenprofil für Bildungsressourcen)

AMB ist ein JSON-LD-Profil auf Basis von Schema.org, das vom
[KIM-Gremium](https://wiki.dnb.de/display/DINIAGKIM) gepflegt wird.
Context-URL: `https://w3id.org/kim/amb/context.jsonld`

Relevante Felder eines AMB-Eintrags (vereinfacht):

| AMB-Feld | Typ | Beispiel |
|---|---|---|
| `id` | URI | `https://openmusic.academy/docs/naWU…` |
| `name` | String | `Pop Arranging 10 – Das Keyboard` |
| `creator[].name` | String | `Ulrich Kaiser` |
| `contributor[].name` | String | `Ilka Mestemacher` |
| `publisher[].name` | String | `Open Music Academy` |
| `description` | String | Freitext-Zusammenfassung |
| `keywords[]` | String[] | `["Songwriting", "Keyboard", …]` |
| `datePublished` | ISO 8601 | `2020-08-04T21:34:12.749Z` |
| `inLanguage[]` | BCP 47 | `["de"]` |
| `license.id` | URI | `https://creativecommons.org/licenses/by-sa/4.0/…` |
| `type[]` | String[] | `["LearningResource", "Article"]` |
| `learningResourceType[].prefLabel` | Object | `{"de": "Webseite", "en": "Web page"}` |
| `about[].id` | URI | `https://w3id.org/kim/hochschulfaechersystematik/n78` |

---

## Stufe 1: AMB → Dublin Core

Die Funktion `amb_to_dublin_core()` bildet jeden AMB-Eintrag auf ein
flaches Python-Dict mit den 15 Dublin-Core-Elementen ab.

| Dublin-Core-Element | AMB-Quelle | Anmerkung |
|---|---|---|
| `dc:title` | `name` | |
| `dc:creator` | `creator[].name` | Liste; erster Eintrag → MARC 100 |
| `dc:contributor` | `contributor[].name` | Duplikate zu `creator` werden entfernt |
| `dc:publisher` | `publisher[].name` | |
| `dc:description` | `description` | |
| `dc:subject` | `keywords[]` + `about[].id` | Keywords als Freitext, `about`-URIs separat |
| `dc:date` | `datePublished` ‖ `dateCreated` | ISO 8601, Fallback auf `dateCreated` |
| `dc:language` | `inLanguage[]` | BCP 47 → MARC-Sprachcode in Stufe 2 |
| `dc:rights` | `license.id` | Lizenz-URI |
| `dc:identifier` | `id` | Persistente URL der Ressource |
| `dc:type` | `type[]` + `learningResourceType[].prefLabel.de` | Ressourcentypen vereint |

---

## Stufe 2: Dublin Core → MARC21

### Leader

```
00000nam a2200000   4500
          ↑↑↑
          │││ 06: a = Sprachtext (language material)
          ││  07: m = Monografie
          │   09: a = Unicode (UCS/UTF-8)
```

### Kontrollfelder

| Tag | Inhalt |
|---|---|
| `001` | Lokale Kontrollnummer (letztes URL-Segment aus `dc:identifier`) |
| `003` | `DE-OMA` (Vergabe-Institution) |
| `007` | `cr` – c=elektronische Ressource, r=Fernzugriff |
| `008` | 40-Zeichen-Feld (s. unten) |

**008-Aufbau (Bücher-Schema):**

```
Pos.   Inhalt
00-05  Eingabedatum (JJMMTT, automatisch)
06     s  (einfaches Datum)
07-10  Erscheinungsjahr (aus dc:date)
11-14  leer
15-17  xx  (unbekanntes Land)
23     o  (Online-Ressource)
35-37  Sprachcode (ISO 639-2, z. B. ger)
39     d  (andere Katalogisierungsquelle)
```

### Datenfelder

| MARC-Tag | Ind. | Subfelder | Dublin-Core-Quelle | Anmerkung |
|---|---|---|---|---|
| **040** | `  ` | $a DE-OMA / $b ger / $e rda | — | Katalogisierungsquelle |
| **041** | `0 ` | $a Sprachcode (3-stellig) | `dc:language` | BCP 47 → MARC via Lookup |
| **100** | `1 ` | $a Name / $e Verfasser/in / $4 aut | `dc:creator[0]` | Erster Urheber; ind1=1: Nachname-Vorname |
| **245** | `1 0` | $a Titel / $c Urheberangabe | `dc:title`, `dc:creator` | ind1=0 wenn kein 1XX |
| **264** | ` 1` | $a [o.O.] / $b Verlag / $c Jahr | `dc:publisher`, `dc:date` | ind2=1: Veröffentlichung |
| **336** | `  ` | $a Text / $b txt / $2 rdacontent | — | RDA-Inhaltstyp |
| **337** | `  ` | $a Computermedien / $b c / $2 rdamedia | — | RDA-Medientyp |
| **338** | `  ` | $a Online-Ressource / $b cr / $2 rdacarrier | — | RDA-Datenträgertyp |
| **520** | `  ` | $a Text | `dc:description` | Zusammenfassung |
| **540** | `  ` | $a Lizenz-URI | `dc:rights` | Nutzungsbedingungen |
| **650** | ` 4` | $a Schlagwort | `dc:subject` (Freitext-Keywords) | ind2=4: nicht kontrolliert |
| **653** | `  ` | $a URI | `dc:subject` (about-URIs) | Fachsystematik-URIs |
| **655** | ` 4` | $a Typ | `dc:type` | Genre-/Formbezeichnung |
| **700** | `1 ` | $a Name / $e Rolle / $4 Code | `dc:creator[1+]`, `dc:contributor` | aut / ctb |
| **856** | `4 0` | $u URL / $z Kostenfrei | `dc:identifier` | ind1=4: HTTP, ind2=0: Online-Ressource |

---

## Ausgabeformat: MARCXML

Das MARCXML-Dokument folgt dem LOC-Schema:

```xml
<?xml version='1.0' encoding='utf-8'?>
<marc:collection
  xmlns:marc="http://www.loc.gov/MARC21/slim"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.loc.gov/MARC21/slim
                      http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">

  <marc:record>
    <marc:leader>00000nam a2200000   4500</marc:leader>
    <marc:controlfield tag="001">naWUgc2WVubAkjfae9V2PL</marc:controlfield>
    <marc:controlfield tag="003">DE-OMA</marc:controlfield>
    <marc:controlfield tag="007">cr</marc:controlfield>
    <marc:controlfield tag="008">260512s2020    xx      o     000 0 ger d</marc:controlfield>
    <marc:datafield tag="040" ind1=" " ind2=" ">
      <marc:subfield code="a">DE-OMA</marc:subfield>
      <marc:subfield code="b">ger</marc:subfield>
      <marc:subfield code="e">rda</marc:subfield>
    </marc:datafield>
    <marc:datafield tag="041" ind1="0" ind2=" ">
      <marc:subfield code="a">ger</marc:subfield>
    </marc:datafield>
    <marc:datafield tag="100" ind1="1" ind2=" ">
      <marc:subfield code="a">Ulrich Kaiser</marc:subfield>
      <marc:subfield code="e">Verfasser/in</marc:subfield>
      <marc:subfield code="4">aut</marc:subfield>
    </marc:datafield>
    <marc:datafield tag="245" ind1="1" ind2="0">
      <marc:subfield code="a">Pop Arranging 10 - Das Keyboard (am Beispiel Kadenzharmonik) /</marc:subfield>
      <marc:subfield code="c">Ulrich Kaiser</marc:subfield>
    </marc:datafield>
    <!-- … weitere Felder … -->
    <marc:datafield tag="856" ind1="4" ind2="0">
      <marc:subfield code="u">https://openmusic.academy/docs/naWUgc2WVubAkjfae9V2PL</marc:subfield>
      <marc:subfield code="z">Kostenfrei</marc:subfield>
    </marc:datafield>
  </marc:record>

</marc:collection>
```

---

## Ausführung

```bash
# Alle Einträge konvertieren
python amb-to-marcxml.py

# Mit expliziten Pfaden
python amb-to-marcxml.py --input docs/oma-amb.json --output docs/oma-marc21.xml

# Nur erste 10 Einträge (Test)
python amb-to-marcxml.py --limit 10
```

---

## Bekannte Einschränkungen

| Punkt | Beschreibung |
|---|---|
| Leader-Längen | `00000` ist ein Platzhalter; bei echter MARC-Verarbeitung muss die Record-Länge nachberechnet werden. MARCXML-Prozessoren tolerieren dies. |
| Personennamen | AMB speichert Namen als Freitext (`"Ulrich Kaiser"`). Eine Umkehrung in MARC-Konvention `Kaiser, Ulrich` (ind1=1) findet **nicht** statt. |
| Erscheinungsland | Wird pauschal auf `xx` (unbekannt) gesetzt, da AMB kein Land-Feld kennt. |
| Normdaten | Urheber, Schlagwörter und Fachsystematik-URIs werden nicht gegen GND, LCSH o. ä. abgeglichen. |
| Sprachcode | BCP-47-Kürzel → MARC-Sprachcode via festem Lookup; seltene Sprachen fallen auf das BCP-47-Kürzel zurück. |
