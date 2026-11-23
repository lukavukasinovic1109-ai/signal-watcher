import hashlib, json, os, re, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = ["https://bettingsignals.net/index.html",
         "https://bettingsignals.net/football-dropping-odds/"]
TOPIC = "signali-e3fdfb484be5"
MESSAGE = "NOVI SIGNAL JE STIGAO"
STATE = Path("state/seen.json")
VOLATILE = re.compile(r"^[+\-]?\d+([.,]\d+)?\s*%?$|^[+\-]?\d+[.,]\d+\s*[-→>/]+\s*\d+[.,]\d+$")

def notify():
    req = urllib.request.Request(f"https://ntfy.sh/{TOPIC}", data=MESSAGE.encode("utf-8"),
        headers={"Priority": "high", "Tags": "soccer"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()
    print("Push poslat.")

def signal_key(cells):
    ident = [c for c in cells if c and not (VOLATILE.match(c) and not re.fullmatch(r"\d", c))]
    if len(ident) < 2:
        ident = cells
    return hashlib.sha1(" | ".join(ident).lower().encode()).hexdigest()[:16]

def scrape():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(user_agent="Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36")
        for url in PAGES:
            try
