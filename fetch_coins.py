#!/usr/bin/env python3
"""Fetch all asicminervalue coin pages, parse JSON-LD, compute profitability metrics."""
import json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

SLUGS = """btc-bitcoin zec-zcash doge-dogecoin xmr-monero bch-bitcoincash ltc-litecoin
etc-ethereum-classic kas-kaspa dash-dash conflux-cfx zen-horizen xec-ecash mwc-mimblewimble
dgb-digibyte-qubit dgb-digibyte-scrypt ckb-nervos sc-siacoin rvn-ravencoin fb-fractal-bitcoin
ethw-ethpow aleo-aleo xtm-tari pep-pepecoin quai-quai-scrypt quai-quai quai-quai-sha nexa-nexa
ppc-peercoin alph-alephium octa-octaspace bcn-bytecoin zephyr-zephyr clore dingo-dingocoin
vtc-vertcoin grin-grin kda-kadena hns-handshake scp-scprime luckycoin-lky cat-catcoin
junkcoin-jkc rxd-radiant sdr-sedra acoin-acoin aeon-aeon aur-auroracoin axe-axe bel-bellscoin
bsv-bitcoinsv blocx-blocx bga-bugna bwk-bulwark btm-bytom clo-callisto dpc-digitalpriceclassic
etn-electroneum emd-emerald egem-ethergem gprx-gainprox ore-galactrum glc-goldcoin
grs-groestlcoin hush-hush ini-initverse krb-karbo kmd-komodo lbc-lbry lthn-lethean
mona-monacoin xmo-monero-original mue-monetaryunit xmy-myriad-groestl nmc-namecoin onx-onix
pasc-pascalcoin pasl-pascallite qkc-quarkchain scc-siaclassic sib-sibcoin strat-stratis
sumo-sumokoin trc-terracoin unb-unbreakable dem-emark""".split()

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

MULT = {'':1,'k':1e3,'M':1e6,'G':1e9,'T':1e12,'P':1e15,'E':1e18,'Z':1e21,'Y':1e24,
        'u':1e-6,'μ':1e-6,'m':1e-3}

def parse_hashrate(s):
    if not s: return None
    m = re.match(r'([\d.]+)\s*([kMGTPEZYuμm]?)h/s', s.strip(), re.I)
    if not m: return None
    v = float(m.group(1)) * MULT.get(m.group(2), 1)
    return v if v > 0 else None

def parse_money(s):
    if not s: return None
    s = s.replace('$','').replace(',','').strip()
    m = re.match(r'([\d.]+)\s*([kMGTPEZ]?)', s)
    if not m: return None
    suf = {'k':1e3,'M':1e6,'G':1e9,'T':1e12,'P':1e15}
    v = float(m.group(1)) * suf.get(m.group(2),1)
    return v if v>0 else None

def parse_time(s):
    if not s: return None
    m = re.match(r'([\d.]+)\s*s', s.strip())
    return float(m.group(1)) if m else None

def fetch(slug):
    url = f"https://www.asicminervalue.com/coins/{slug}"
    for attempt in range(3):
        try:
            r = subprocess.run(["curl","-s","--max-time","40","-A",UA,url],
                               capture_output=True, text=True)
            h = r.stdout
            if len(h) < 5000:
                time.sleep(3); continue
            out = {"slug": slug, "url": url}
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
                try: d = json.loads(m.group(1))
                except Exception: continue
                if isinstance(d, dict) and d.get('@type') == 'Cryptocurrency':
                    out['name'] = d.get('name')
                    out['symbol'] = d.get('alternateName')
                    out['price_usd'] = parse_money(d.get('price',''))
                    props = {p['name']: p['value'] for p in d.get('additionalProperty',[])}
                    out['algorithm'] = props.get('algorithm')
                    out['network_hashrate_display'] = props.get('networkHashrate')
                    out['network_hashrate_hs'] = parse_hashrate(props.get('networkHashrate',''))
                    out['difficulty'] = props.get('difficulty')
                    br = props.get('blockReward','')
                    mbr = re.match(r'([\d.]+)', br)
                    out['block_reward'] = float(mbr.group(1)) if mbr else None
                    out['block_time_s'] = parse_time(props.get('blockTime',''))
                    out['market_cap_usd'] = parse_money(props.get('marketCap',''))
                    return out
            out['error'] = 'no-jsonld'
            return out
        except Exception as e:
            time.sleep(3)
    return {"slug": slug, "url": url, "error": "fetch-failed"}

def main():
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(fetch, SLUGS))
    # compute metrics
    for c in results:
        p, br, bt, nh = (c.get('price_usd'), c.get('block_reward'),
                         c.get('block_time_s'), c.get('network_hashrate_hs'))
        if p and br and bt:
            blocks_day = 86400.0/bt
            c['daily_emission_usd'] = p*br*blocks_day
        else:
            c['daily_emission_usd'] = None
        if c.get('daily_emission_usd') and nh:
            # revenue per GH/s per day (network-share model)
            c['rev_per_ghs_day_usd'] = c['daily_emission_usd']/(nh/1e9)
        else:
            c['rev_per_ghs_day_usd'] = None
    json.dump(results, open('coins.json','w'), indent=1)
    ok = sum(1 for c in results if 'error' not in c)
    print(f"{ok}/{len(results)} pages parsed OK")
    for c in results:
        if 'error' in c: print("FAILED:", c['slug'], c['error'])

if __name__ == '__main__':
    main()
