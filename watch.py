import hashlib, json, os, re, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = ["https://bettingsignals.net/index.html",
         "https://bettingsignals.net/football-dropping-odds/"]
TOPIC = "signali-e3fdfb484be5"
MESSAGE = "NOVI SIGNAL JE STIGAO"
STATE = Path("state/seen2.json")
DEBUG = Path("state/debug")
VOLATILE = re.compile(r"^[+\-]?\d+([.,]\d+)?\s*%?$")
SEL = "tr, ion-row, ion-item, ion-card, [class*=row], [class*=match], [class*=signal], [class*=item]"

JS = """(sel) => {
  const els = [...document.querySelectorAll(sel)];
  const leaf = els.filter(e => !e.querySelector(sel));
  return leaf.map(e => (e.innerText || '').split('\\n').map(s => s.trim()).filter(Boolean))
             .filter(r => r.length >= 2 && r.join('').length > 8);
}"""

def notify():
    req = urllib.request.Request("https://ntfy.sh/" + TOPIC, data=MESSAGE.encode("utf-8"),
        headers={"Priority": "high", "Tags": "soccer"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()
    print("Push poslat.")

def signal_key(c):
    if len(c) >= 5:
        ident = c[:4] + [c[4].split("|")[0].strip()]
    else:
        ident = [x for x in c if not (VOLATILE.match(x) and len(x) > 1)]
    return hashlib.sha1(" | ".join(ident).lower().encode()).hexdigest()[:16]

def scrape(debug):
    net = []
    def on_resp(r):
        try:
            ct = r.headers.get("content-type", "")
            if "json" in ct or "text/plain" in ct or "csv" in ct:
                net.append(r.url + "\n" + r.text()[:3000])
            else:
                net.append(r.url)
        except Exception:
            net.append(r.url)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 3000})
        page.on("response", on_resp)
        result = None
        texts = []
        for url in PAGES:
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print("Greska:", url, e)
                continue
            time.sleep(8)
            rows = []
            for fr in page.frames:
                try:
                    rows += fr.evaluate(JS, SEL)
                    texts.append("=== " + fr.url + "\n" + fr.evaluate("() => document.body ? document.body.innerText : ''"))
                except Exception:
                    pass
            print(url, len(rows), "redova")
            if rows:
                result = rows
                break
        b.close()
    if debug or not result:
        DEBUG.mkdir(parents=True, exist_ok=True)
        (DEBUG / "text.txt").write_text("\n\n".join(texts)[:200000])
        (DEBUG / "net.txt").write_text("\n\n".join(net)[:200000])
        (DEBUG / "rows.json").write_text(json.dumps(result or [], ensure_ascii=False, indent=1)[:200000])
    return result

def main():
    if os.environ.get("TEST_PUSH") == "1":
        notify()
        return
    first = not STATE.exists()
    rows = scrape(debug=first)
    if not rows:
        print("Nema podataka, preskacem.")
        return
    keys = list(dict.fromkeys(signal_key(r) for r in rows))
    seen = [] if first else json.loads(STATE.read_text())
    new = [k for k in keys if k not in set(seen)]
    print("Signala:", len(keys), "novih:", len(new))
    if new and not first:
        notify()
    if new or first:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps((seen + new)[-5000:]))

main()
