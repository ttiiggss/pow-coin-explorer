# PoW Coin Explorer

All 85 proof-of-work coins tracked by [asicminervalue.com](https://www.asicminervalue.com/coins), with charts ranking them by mining profitability and potential.

- `fetch_coins.py` — scrapes the 85 coin pages (JSON-LD structured data) into `coins.json`
- `build_site.py` — generates `index.html` (Chart.js, single file, no build step)

Live: https://ttiiggss.github.io/pow-coin-explorer/

Metrics: miner revenue/day = block_reward x blocks/day x price; yield = annualized emission as % of market cap; score = 40% revenue size + 35% market cap + 25% yield sweet-spot. Not financial advice.
