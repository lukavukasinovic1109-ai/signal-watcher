import hashlib, json, os, re, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = ["https://bettingsignals.net/index.html",
         "https://bettingsignals.net/football-dropping-odds/"]
TOPIC = "signali-e3fdfb484be5"
MESSAGE = "NOVI SIGNAL JE STIGAO"
STATE = Path("state/seen.json")
VOLATILE = re.compile(r"^[+\-]?\d+([.,]\d+)?\s*%?$")

def notify():
    req = urllib.request.Request("https://ntfy.sh/" + TOPIC, data=MESSAGE.encode("utf-8"),
        headers={"Priority": "high", "Tags": "soccer"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()
    print("Push poslat.")

def signal_key(cells):
    ident = [c for c in cells if c and not (VOLATILE.match(c) and len(c) > 1)]
    if len(ident) < 2:
        ident = cells
    return hashlib.sha1(" | ".join(ident).lower().encode()).hexdigest()[:16]

JS = "() => [...document.querySelectorAll('tr')].map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.trim())).filter(r => r.length >= 2)"

def scrape():
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        for url in PAGES:
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print("Greska:", url, e)
                continue
            time.sleep(5)
            rows = []
            for fr in page.frames:
                try:
                    rows += fr.evaluate(JS)
                except Exception:
                    pass
            if rows:
                print(url, len(rows), "redova")
                b.close()
                return rows
            print(url, "tabela nije nadjena")
        b.close()

def main():
    if os.environ.get("TEST_PUSH") == "1":
        notify()
        return
    rows = scrape()
    if not rows:
        print("Nema podataka, preskacem.")
        return
    for r in rows[:10]:
        print("  ", r)
    keys = list(dict.fromkeys(signal_key(r) for r in rows))
    first = not STATE.exists()
    seen = [] if first else json.loads(STATE.read_text())
    new = [k for k in keys if k not in set(seen)]
    print("Signala:", len(keys), "novih:", len(new))
    if new and not first:
        notify()
    if new or first:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps((seen + new)[-5000:]))

main()
