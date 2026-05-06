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


with open(args.input, "r", encoding="utf-8") as f:
    amb_data = json.load(f)

amb_data.sort(key=lambda x: x.get("datePublished", ""), reverse=True)

ET.register_namespace("media", "http://search.yahoo.com/mrss/")
rss = ET.Element("rss", version="2.0", attrib={"xmlns:media": "http://search.yahoo.com/mrss/"})
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
    ET.SubElement(item, "guid").text = link
    ET.SubElement(item, "description").text = description
    ET.SubElement(item, "pubDate").text = to_rfc2822(date)

    image = entry.get("image", "")
    if image:
        ET.SubElement(item, "{http://search.yahoo.com/mrss/}content", url=image, medium="image")

    keywords = entry.get("keywords", [])
    if isinstance(keywords, list):
        for keyword in keywords:
            ET.SubElement(item, "category").text = str(keyword)

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ", level=0)
tree.write(args.output, encoding="utf-8", xml_declaration=True)

print(f"RSS Feed erzeugt: {args.output}")
