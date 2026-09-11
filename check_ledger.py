#!/usr/bin/env python3
"""Check each PoW coin against Ledger's supported-assets search endpoint."""
import json, re, subprocess, time

coins = json.load(open('coins.json'))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

def query(q):
    r = subprocess.run(["curl","-s","--max-time","30","-A",UA,"-X","POST",
        "https://www.ledger.com/wp-admin/admin-ajax.php",
        "-F","action=supported_crypto_search",
        "-F","supported_crypto_page=1",
        "-F",f"supported_crypto_query={q}"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return d['html']['body'] if d.get('status')==200 else ''
    except Exception:
        return ''

ROW = re.compile(r'<tr>.*?</tr>', re.S)
def parse_rows(html):
    out = []
    for row in ROW.findall(html):
        nm = re.search(r'text-body-highlight">([^<]+)</p>', row)
        tk = re.search(r'text-caption">([^<]+)</p>', row)
        if not (nm and tk): continue
        cells = {}
        for cls in ['send','buy','swap','staking','support']:
            cm = re.search(r'<td class="'+cls+r'".*?</td>', row, re.S)
            cells[cls] = bool(cm and 'icon-check-alone' in cm.group(0))
        url = re.search(r'href="(https://www\.ledger\.com/coin/wallet/[^"]+)"', row)
        out.append({'name': nm.group(1).strip(), 'ticker': tk.group(1).strip(),
                    'url': url.group(1) if url else None, **cells})
    return out

def norm(s): return re.sub(r'[^a-z0-9]','', (s or '').lower())

results = {}
for c in coins:
    name = c.get('name') or ''
    sym  = (c.get('symbol') or '').upper()
    base_sym = sym  # e.g. QUAI appears 3x with variants
    cand = []
    for q in {name, sym}:
        if not q: continue
        cand += parse_rows(query(q))
        time.sleep(0.4)
    match = None
    for r in cand:
        if r['ticker'].upper() == base_sym and (
            norm(r['name']) == norm(name)
            or norm(name) in norm(r['name']) or norm(r['name']) in norm(name)):
            match = r; break
    if not match:  # exact-name-only fallback (ticker rendering may differ)
        for r in cand:
            if norm(r['name']) == norm(name):
                match = r; break
    results[c['slug']] = match
    print(f"{c['slug']:26} {'LEDGER: '+match['name']+' ('+match['ticker']+')' if match else '-'}"
          + (f"  send={match['send']} buy={match['buy']} swap={match['swap']} 3rd={match['support']}" if match else ''))

json.dump(results, open('ledger.json','w'), indent=1)
n = sum(1 for v in results.values() if v)
print(f"\n{n}/{len(coins)} coins found on Ledger supported-assets")
