import argparse
import json
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument("--input", default="docs/oma-amb.json")
parser.add_argument("--output", default="docs/oma-feed.xml")
args = parser.parse_args()


def to_rfc2822(date_string):
    if not date_string:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


MEDIA_NS  = "http://search.yahoo.com/mrss/"
ITUNES_NS = "http://www.itunes.com/DTDs/Podcast-1.0.dtd"
SDX_NS    = "sodix.dtd"

ABOUT_TO_SUBJECT = {
    "https://w3id.org/kim/hochschulfaechersystematik/n78": "420",
}

LICENSE_MAP = {
    "https://creativecommons.org/licenses/by-sa/4.0/deed.de": {
        "name": "Namensnennung-Share Alike 4.0 International, CC BY-SA 4.0",
        "version": "4.0",
    },
}


with open(args.input, "r", encoding="utf-8") as f:
    amb_data = json.load(f)

amb_data.sort(key=lambda x: x.get("datePublished", ""), reverse=True)

ET.register_namespace("media",  MEDIA_NS)
ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("sdx",    SDX_NS)

rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "Open Music Academy – AMB Export"
ET.SubElement(channel, "link").text = "https://openmusic.academy"
ET.SubElement(channel, "description").text = "RSS Feed generiert aus AMB Metadaten"
ET.SubElement(channel, "language").text = "de"
ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

for entry in amb_data:
    item = ET.SubElement(channel, "item")

    title = entry.get("name", "Untitled")
    link = entry.get("id", "")
    description = entry.get("description", "")
    date = entry.get("datePublished") or entry.get("dateCreated")

    ET.SubElement(item, "title").text = title
    ET.SubElement(item, "link").text = link
    guid = link.split("docs/")[-1] if "docs/" in link else link
    ET.SubElement(item, "guid").text = guid
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "pubDate").text = to_rfc2822(date)

    image = entry.get("image", "")
    if image:
        ET.SubElement(item, f"{{{MEDIA_NS}}}content", url=image, medium="image")

    keywords = entry.get("keywords", [])
    if isinstance(keywords, list) and keywords:
        ET.SubElement(item, f"{{{ITUNES_NS}}}keywords").text = ", ".join(str(k) for k in keywords)

    creators = [c["name"] for c in entry.get("creator", []) if c.get("name")]
    creator_set = set(creators)
    contributors = [
        c["name"] for c in entry.get("contributor", [])
        if c.get("name") and c["name"] not in creator_set
    ]
    all_authors = creators + contributors
    if all_authors:
        ET.SubElement(item, f"{{{ITUNES_NS}}}author").text = ", ".join(all_authors)

    for about in entry.get("about", []):
        subject_code = ABOUT_TO_SUBJECT.get(about.get("id", ""))
        if subject_code:
            ET.SubElement(item, f"{{{SDX_NS}}}subject").text = subject_code

    license_obj = entry.get("license", {})
    license_id = license_obj.get("id", "") if isinstance(license_obj, dict) else ""
    license_info = LICENSE_MAP.get(license_id)
    if license_info:
        ET.SubElement(item, f"{{{SDX_NS}}}licenseName").text = license_info["name"]
        ET.SubElement(item, f"{{{SDX_NS}}}licenseVersion").text = license_info["version"]

    if entry.get("learningResourceType"):
        ET.SubElement(item, f"{{{SDX_NS}}}learnResourceType").text = "Anleitung, Unterrichtsbaustein"

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ", level=0)
tree.write(args.output, encoding="utf-8", xml_declaration=True)

print(f"RSS Feed erzeugt: {args.output}")
