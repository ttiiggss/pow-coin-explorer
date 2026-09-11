#!/usr/bin/env python3
"""Build index.html for the PoW coin explorer from coins.json."""
import json, math, datetime

coins = json.load(open('coins.json'))

ALGO_GROUPS = {}
for c in coins:
    a = c.get('algorithm') or 'Unknown'
    ALGO_GROUPS.setdefault(a, []).append(c)

# ---- composite potential score (transparent, 0-100) ----
def safe_log(v):
    return math.log10(v) if v and v > 0 else None

em_logs = [safe_log(c.get('daily_emission_usd')) for c in coins]
mc_logs = [safe_log(c.get('market_cap_usd')) for c in coins]
em_vals = [v for v in em_logs if v is not None]
mc_vals = [v for v in mc_logs if v is not None]
em_min, em_max = min(em_vals), max(em_vals)
mc_min, mc_max = min(mc_vals), max(mc_vals)

for c in coins:
    em = safe_log(c.get('daily_emission_usd'))
    mc = safe_log(c.get('market_cap_usd'))
    mcap = c.get('market_cap_usd')
    emission = c.get('daily_emission_usd')
    y = (emission * 365 / mcap * 100) if (mcap and emission) else None
    c['miner_yield_pct'] = y
    # score: emission size 40%, mcap/liquidity 35%, yield sweet spot 25%
    if em is None or mc is None:
        c['score'] = None
        continue
    s_em = (em - em_min) / (em_max - em_min)
    s_mc = (mc - mc_min) / (mc_max - mc_min)
    # yield sweet spot: peak around 20-100%/yr, penalise hyperinflation
    if y is None: s_y = 0
    elif y <= 0: s_y = 0
    else:
        ly = math.log10(y)
        s_y = max(0.0, 1.0 - abs(ly - 1.5) / 2.5)  # peak at ~31%/yr
    c['score'] = round(100 * (0.40 * s_em + 0.35 * s_mc + 0.25 * s_y), 1)

data_js = json.dumps([{
    'slug': c['slug'], 'name': c.get('name'), 'symbol': c.get('symbol'),
    'algo': c.get('algorithm'), 'price': c.get('price_usd'),
    'mcap': c.get('market_cap_usd'), 'hashrate': c.get('network_hashrate_display'),
    'hashrate_hs': c.get('network_hashrate_hs'), 'difficulty': c.get('difficulty'),
    'block_reward': c.get('block_reward'), 'block_time': c.get('block_time_s'),
    'emission': c.get('daily_emission_usd'), 'yield_pct': c.get('miner_yield_pct'),
    'score': c.get('score'), 'url': c['url'],
} for c in coins], separators=(',', ':'))

today = datetime.date.today().isoformat()

head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PoW Coin Explorer — Profitability &amp; Potential</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0b1020;--panel:#131a30;--panel2:#182240;--txt:#e8ecf8;--dim:#8b96b8;
--accent:#4f8ff7;--gold:#f7c948;--green:#3ddc97;--red:#ff6b6b;--violet:#a78bfa;}
*{margin:0;padding:0;box-sizing:border-box}
body{background:radial-gradient(1200px 600px at 70% -10%,#1a2547 0%,var(--bg) 55%);
color:var(--txt);font:15px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;min-height:100vh}
.wrap{max-width:1200px;margin:0 auto;padding:32px 20px 80px}
h1{font-size:2rem;letter-spacing:-.5px;background:linear-gradient(90deg,var(--accent),var(--violet));
-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--dim);margin:6px 0 26px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:30px}
.stat{background:var(--panel);border:1px solid #223056;border-radius:14px;padding:16px 18px}
.stat b{display:block;font-size:1.5rem}
.stat span{color:var(--dim);font-size:.82rem}
.panel{background:var(--panel);border:1px solid #223056;border-radius:16px;padding:22px;margin-bottom:26px}
.panel h2{font-size:1.15rem;margin-bottom:4px}
.panel .note{color:var(--dim);font-size:.83rem;margin-bottom:14px}
.chartbox{position:relative;width:100%}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}
.card{background:var(--panel2);border:1px solid #26335c;border-radius:14px;padding:14px 16px;position:relative}
.card .rank{position:absolute;top:10px;right:12px;color:var(--dim);font-size:.8rem}
.card h3{font-size:1.02rem}
.card .algo{display:inline-block;font-size:.72rem;color:var(--accent);background:#1b2a52;
border-radius:20px;padding:1px 9px;margin:4px 0 8px}
.card dl{font-size:.8rem;color:var(--dim)}
.card dd{color:var(--txt);margin-bottom:3px}
.scorebar{height:6px;border-radius:4px;background:#223056;margin-top:8px;overflow:hidden}
.scorebar i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--green))}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{padding:8px 10px;text-align:right;border-bottom:1px solid #1d2848;white-space:nowrap}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
th{color:var(--dim);cursor:pointer;user-select:none;position:sticky;top:0;background:var(--panel)}
th:hover{color:var(--txt)}
tr:hover td{background:#182142}
td a{color:var(--txt);text-decoration:none;font-weight:600}
td a:hover{color:var(--accent)}
.pos{color:var(--green)}.neut{color:var(--gold)}.dim{color:var(--dim)}
.tablewrap{max-height:640px;overflow:auto;border-radius:10px}
.footer{color:var(--dim);font-size:.78rem;margin-top:30px}
.footer a{color:var(--accent)}
@media(max-width:640px){h1{font-size:1.4rem}}
</style>
</head>
<body>
<div class="wrap">
<h1>Proof-of-Work Coin Explorer</h1>
<p class="sub">All 85 mineable PoW coins tracked by asicminervalue.com &mdash; ranked by mining economics and potential. Data snapshot: __DATE__</p>
<div class="stats" id="stats"></div>

<div class="panel">
<h2>Daily mining revenue pool</h2>
<p class="note">Total USD paid to miners per day (block reward &times; blocks/day &times; price) &mdash; the size of the pie you're competing for. Log scale, top 30 coins.</p>
<div class="chartbox" style="height:640px"><canvas id="cEmission"></canvas></div>
</div>

<div class="panel">
<h2>Potential map: market cap vs miner revenue</h2>
<p class="note">Up-right = big &amp; rewarding (majors). Above the diagonal trend = paying miners generously for their size &mdash; that's where opportunity (and inflation risk) lives. Bubble size = miner yield. Log-log scale.</p>
<div class="chartbox" style="height:520px"><canvas id="cScatter"></canvas></div>
</div>

<div class="panel">
<h2>Miner yield &mdash; annualized emission as % of market cap</h2>
<p class="note">How much of the coin's whole market value is paid out to miners per year. High = generous rewards but heavy sell pressure; ~5&ndash;50% is a healthy band.</p>
<div class="chartbox" style="height:520px"><canvas id="cYield"></canvas></div>
</div>

<div class="panel">
<h2>Top potential picks</h2>
<p class="note">Composite score: 40% miner-revenue size + 35% market cap (liquidity/staying power) + 25% yield sweet-spot (peaks ~30%/yr). Transparent &amp; mechanical, not financial advice.</p>
<div class="cards" id="cards"></div>
</div>

<div class="panel">
<h2>All 85 coins</h2>
<p class="note">Click any column header to sort. &mdash; means the site had no live data for that field (mostly dead/zombie chains).</p>
<div class="tablewrap"><table id="tbl"><thead><tr>
<th data-k="symbol">Coin</th><th data-k="algo">Algorithm</th><th data-k="price">Price</th>
<th data-k="mcap">Market cap</th><th data-k="hashrate_hs">Net hashrate</th>
<th data-k="emission">Miner rev/day</th><th data-k="yield_pct">Yield %/yr</th>
<th data-k="score">Score</th></tr></thead><tbody></tbody></table></div>
</div>

<p class="footer">Source: <a href="https://www.asicminervalue.com/coins">asicminervalue.com/coins</a> (85 coin pages, structured data). Revenue pool = block_reward &times; 86400/block_time &times; price. Coins showing &mdash; lack price/reward data upstream. Nothing here is financial advice; PoW mining profits depend on your hardware, electricity cost and pool luck.</p>
</div>
<script>
const DATA=__DATA__;
</script>
"""

script = """<script>
const fmt$=v=>v==null?'\\u2014':v>=1e12?'$'+(v/1e12).toFixed(2)+'T':v>=1e9?'$'+(v/1e9).toFixed(2)+'B':v>=1e6?'$'+(v/1e6).toFixed(2)+'M':v>=1e3?'$'+(v/1e3).toFixed(1)+'k':'$'+v.toFixed(v<1?4:2);
const fmtP=v=>v==null?'\\u2014':v<0.01?'$'+v.toFixed(6):v<1?'$'+v.toFixed(4):'$'+v.toLocaleString(undefined,{maximumFractionDigits:2});
const fmtY=v=>v==null?'\\u2014':v.toFixed(v<10?1:0)+'%';
Chart.defaults.color='#8b96b8';Chart.defaults.borderColor='#223056';Chart.defaults.font.family='system-ui';

const live=DATA.filter(c=>c.emission>0);
const totalEm=live.reduce((s,c)=>s+c.emission,0);
const algos=[...new Set(DATA.map(c=>c.algo).filter(Boolean))];
document.getElementById('stats').innerHTML=[
 ['<b>85</b><span>PoW coins tracked</span>'],
 ['<b>'+algos.length+'</b><span>mining algorithms</span>'],
 ['<b>'+fmt$(totalEm)+'</b><span>paid to miners / day (all coins)</span>'],
 ['<b>'+live.length+'</b><span>chains actively emitting</span>'],
].map(s=>'<div class="stat">'+s+'</div>').join('');

const PALETTE=['#4f8ff7','#f7c948','#3ddc97','#ff6b6b','#a78bfa','#f97316','#22d3ee','#e879f9','#84cc16','#fb7185'];
const algoColor={};algos.forEach((a,i)=>algoColor[a]=PALETTE[i%PALETTE.length]);

// 1. emission bar
const topEm=live.slice().sort((a,b)=>b.emission-a.emission).slice(0,30);
new Chart(cEmission,{type:'bar',data:{labels:topEm.map(c=>c.symbol+' \\u00b7 '+c.algo),
 datasets:[{data:topEm.map(c=>c.emission),backgroundColor:topEm.map(c=>algoColor[c.algo]||'#4f8ff7'),borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false},
 tooltip:{callbacks:{label:x=>' '+fmt$(x.raw)+' / day'}}},
 scales:{x:{type:'logarithmic',title:{display:true,text:'USD per day (log)'}},y:{ticks:{autoSkip:false,font:{size:11}}}}}});

// 2. scatter mcap vs emission
const sc=live.filter(c=>c.mcap>0);
new Chart(cScatter,{type:'bubble',data:{datasets:sc.map(c=>({label:c.symbol,
 data:[{x:c.mcap,y:c.emission,r:Math.max(4,Math.min(22,Math.sqrt(c.yield_pct||1)*2))}],
 backgroundColor:(algoColor[c.algo]||'#4f8ff7')+'cc'}))},
 options:{maintainAspectRatio:false,plugins:{legend:{display:false},
 tooltip:{callbacks:{label:x=>{const c=sc[x.datasetIndex];
  return[c.name+' ('+c.symbol+') \\u00b7 '+c.algo,'mcap '+fmt$(c.mcap)+' \\u00b7 miners get '+fmt$(c.emission)+'/day','yield '+fmtY(c.yield_pct)+'/yr'];}}}},
 scales:{x:{type:'logarithmic',title:{display:true,text:'Market cap (log)'}},
 y:{type:'logarithmic',title:{display:true,text:'Miner revenue USD/day (log)'}}}}});

// 3. yield bar
const yd=live.filter(c=>c.yield_pct>0).sort((a,b)=>b.yield_pct-a.yield_pct).slice(0,25);
new Chart(cYield,{type:'bar',data:{labels:yd.map(c=>c.symbol),
 datasets:[{data:yd.map(c=>c.yield_pct),backgroundColor:yd.map(c=>c.yield_pct>100?'#ff6b6b':c.yield_pct>50?'#f7c948':'#3ddc97'),borderRadius:4}]},
 options:{indexAxis:'y',maintainAspectRatio:false,plugins:{legend:{display:false},
 tooltip:{callbacks:{label:x=>' '+x.raw.toFixed(1)+'% of mcap paid to miners per year'}}},
 scales:{x:{type:'logarithmic',title:{display:true,text:'% of market cap / year (log)'}}}}});

// 4. cards
const picks=DATA.filter(c=>c.score!=null).sort((a,b)=>b.score-a.score).slice(0,10);
document.getElementById('cards').innerHTML=picks.map((c,i)=>
 '<div class="card"><span class="rank">#'+(i+1)+'</span><h3>'+c.name+' <span class="dim">'+c.symbol+'</span></h3>'+
 '<span class="algo">'+c.algo+'</span><dl>'+
 '<dt>Miners earn</dt><dd>'+fmt$(c.emission)+' / day</dd>'+
 '<dt>Market cap</dt><dd>'+fmt$(c.mcap)+'</dd>'+
 '<dt>Yield</dt><dd>'+fmtY(c.yield_pct)+' / yr</dd></dl>'+
 '<div class="scorebar"><i style="width:'+c.score+'%"></i></div>'+
 '<dl><dd class="dim">score '+c.score+'</dd></dl></div>').join('');

// 5. table
let sortK='score',sortDir=-1;
function render(){
 const rows=DATA.slice().sort((a,b)=>{
  const av=a[sortK],bv=b[sortK];
  if(av==null&&bv==null)return 0;if(av==null)return 1;if(bv==null)return -1;
  return (typeof av==='string'?av.localeCompare(bv):av-bv)*sortDir;});
 document.querySelector('#tbl tbody').innerHTML=rows.map(c=>
  '<tr><td><a href="'+c.url+'" target="_blank" rel="noopener">'+(c.symbol||c.slug)+'</a> <span class="dim">'+(c.name||'')+'</span></td>'+
  '<td>'+(c.algo||'\\u2014')+'</td><td>'+fmtP(c.price)+'</td><td>'+fmt$(c.mcap)+'</td>'+
  '<td>'+(c.hashrate||'\\u2014')+'</td><td class="'+(c.emission>1e5?'pos':c.emission>0?'neut':'dim')+'">'+fmt$(c.emission)+'</td>'+
  '<td>'+fmtY(c.yield_pct)+'</td><td>'+(c.score==null?'\\u2014':c.score)+'</td></tr>').join('');
}
document.querySelectorAll('#tbl th').forEach(th=>th.onclick=()=>{
 const k=th.dataset.k;
 if(sortK===k)sortDir*=-1;else{sortK=k;sortDir=k==='symbol'||k==='algo'?1:-1;}
 render();});
render();
</script>
</body>
</html>
"""

html = head.replace('__DATE__', today).replace('__DATA__', data_js) + script
open('index.html', 'w').write(html)
print('index.html written:', len(html), 'bytes')
# verify markers
for marker in ['<!DOCTYPE html', '</html>', 'const DATA=[', 'cEmission', 'cScatter', 'cYield']:
    assert marker in html, marker
print('all markers present')
