import html
import json
import os
from datetime import datetime, timedelta, timezone
import feedparser
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

FEEDS = [
    ("🏛️ PIB (Govt. of India)", "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"),
    ("💡 Indian Express Explained", "https://indianexpress.com/section/explained/feed/"),
    ("📰 The Hindu – National", "https://www.thehindu.com/news/national/?service=rss"),
    ("🇮🇳 Indian Express – India", "https://indianexpress.com/section/india/feed/"),
]

POSTED_FILE = "posted.json"
MAX_PER_SOURCE = 2  # Posts up to 8 fresh items per run


def load_posted():
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posted(links):
    # Keep only the latest 200 links to keep the file small
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(links[-200:], f, indent=2)


def fetch_news(posted_links):
    headers = {"User-Agent": "Mozilla/5.0"}
    digest_sections = []
    new_links = []

    for source_name, url in FEEDS:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"Skipping {source_name}: {e}")
            continue

        items = []
        for entry in feed.entries:
            link = entry.get("link", "").strip()
            title = html.escape(entry.get("title", "").strip())
            if not link or not title or link in posted_links or link in new_links:
                continue
            items.append(f'• <a href="{link}">{title}</a>')
            new_links.append(link)
            if len(items) >= MAX_PER_SOURCE:
                break

        if items:
            digest_sections.append(f"<b>{source_name}</b>\n" + "\n".join(items))

    return digest_sections, new_links


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()


def main():
    posted_links = load_posted()
    sections, new_links = fetch_news(posted_links)

    if not sections:
        print("No new UPSC articles found.")
        return

    ist = timezone(timedelta(hours=5, minutes=30))
    now_str = datetime.now(ist).strftime("%d %b %Y, %I:%M %p IST")

    header = f"📚 <b>UPSC &amp; Current Affairs Digest</b>\n🗓 <i>{now_str}</i>\n\n"
    footer = "\n\n#UPSC #CurrentAffairs #DailyNews"
    message = header + "\n\n".join(sections) + footer

    send_telegram_message(message)
    save_posted(posted_links + new_links)
    print(f"Posted {len(new_links)} new items successfully.")


if __name__ == "__main__":
    main()
