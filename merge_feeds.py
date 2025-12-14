#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from lxml import etree

FEEDS = [
    "https://feeds.guardian.co.uk/theguardian/environment/rss",
    "https://feeds.guardian.co.uk/theguardian/environment/rss",
    "https://www.theguardian.com/environment/climate-crisis/rss",
    "https://www.theguardian.com/news/series/the-long-read/rss",
    "https://www.theguardian.com/uk/commentisfree/rss",
    "https://www.theguardian.com/international/rss",
    "https://feeds.guardian.co.uk/theguardian/world/rss",
    "https://www.theguardian.com/us/commentisfree/rss",
"http://www.guardian.co.uk/weekly/rss"
]

OUTPUT = "merged.xml"
MAX_ITEMS = 1000
CUTOFF = datetime.now(timezone.utc) - timedelta(hours=48)

# URL path filters (hard exclusion)
BLOCKED_PATHS = (
    "/sport/",
    "/entertainment/",
    "/culture/","/food/","/music/","/tv-and-tadio/","/lifeandstyle/","/stage/","/film/","/artanddesign/","/fashion/","/books/","/football/","/media/","/travel/","/society/","/uk-news/","/australia-news/"

)

def is_blocked(link):
    if not link:
        return True
    lower = link.lower()
    for p in BLOCKED_PATHS:
        if p in lower:
            return True
    return False

def load_existing_links(root):
    links = set()
    for item in root.xpath("//item/link"):
        if item.text:
            links.add(item.text.strip())
    return links

def parse_datetime(entry):
    if hasattr(entry, "published"):
        return dateparser.parse(entry.published).astimezone(timezone.utc)
    return None

def extract_image(entry):
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get("url")
    if "links" in entry:
        for l in entry.links:
            if l.get("type", "").startswith("image"):
                return l.get("href")
    return None

if os.path.exists(OUTPUT):
    tree = etree.parse(OUTPUT)
    channel = tree.find(".//channel")
    existing_links = load_existing_links(tree)
else:
    rss = etree.Element(
        "rss",
        version="2.0",
        nsmap={"media": "http://search.yahoo.com/mrss/"}
    )
    channel = etree.SubElement(rss, "channel")
    etree.SubElement(channel, "title").text = "Guardian Unified Feed"
    etree.SubElement(channel, "link").text = "https://www.theguardian.com"
    etree.SubElement(channel, "description").text = "Merged Guardian RSS"
    tree = etree.ElementTree(rss)
    existing_links = set()

new_items = []

for url in FEEDS:
    feed = feedparser.parse(url)

    for entry in feed.entries:
        link = entry.get("link")

        # FILTER: path exclusion
        if is_blocked(link):
            continue

        # DUPLICATE check (cross-run + same-run)
        if not link or link in existing_links:
            continue

        # TIME filter
        dt = parse_datetime(entry)
        if not dt or dt < CUTOFF:
            continue

        item = etree.Element("item")

        etree.SubElement(item, "title").text = entry.get("title", "").strip()
        etree.SubElement(item, "link").text = link
        etree.SubElement(item, "guid").text = link
        etree.SubElement(item, "pubDate").text = dt.strftime(
            "%a, %d %b %Y %H:%M:%S %z"
        )

        desc = entry.get("summary", "")
        if desc:
            etree.SubElement(item, "description").text = desc

        img = extract_image(entry)
        if img:
            media = etree.SubElement(
                item,
                "{http://search.yahoo.com/mrss/}content"
            )
            media.set("url", img)
            media.set("medium", "image")

        new_items.append((dt, item))
        existing_links.add(link)

# newest first
new_items.sort(key=lambda x: x[0], reverse=True)

# insert at top
for _, item in new_items:
    channel.insert(0, item)

# circular trimming
items = channel.findall("item")
if len(items) > MAX_ITEMS:
    for old in items[MAX_ITEMS:]:
        channel.remove(old)

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True,
    pretty_print=True
            )
