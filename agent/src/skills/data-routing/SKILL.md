---
name: data-routing
category: data-source
description: Data source selection decision tree. Load this skill BEFORE any backtest or data-fetching task to choose the best available data source.
---

## Data Source Overview

| Source | Markets | Auth Required | Network | Skill |
|--------|---------|---------------|---------|-------|
| tushare | A-shares, funds, futures, macro | Yes (`TUSHARE_TOKEN`) | China network | tushare |
| akshare | A-shares, US, HK, futures, macro, forex | No | Unrestricted | akshare |
| yfinance | US stocks, HK stocks, ETFs | No | Needs Yahoo Finance access | yfinance |
| okx | Crypto (OKX exchange) | No | Needs okx.com access | okx-market |
| ccxt | Crypto (100+ exchanges) | No | Needs exchange access | ccxt |
| datapro | **Vietnam equities** (HOSE/HNX/UPCOM) — OHLCV, foreign flow | No (localhost) | Needs DataPro desktop on `localhost:6789` | — |
| vnstock | **Vietnam equities** — OHLCV (internet, no desktop) + fundamentals (income/balancesheet/cashflow) | No | Needs internet | — |

> **Vietnam (HOSE/HNX/UPCOM):** write symbols with a `.VN` suffix (e.g.
> `VCB.VN`, `FPT.VN`) and the runner applies VN trading rules (T+2, ±7/10/15%
> bands, no short) and auto-attaches vnstock financial statements when
> `fundamental_fields` is set. Two price sources back this market:
> `datapro` (preferred — richest bars incl. foreign flow + the official
> reference price, but needs the DataPro desktop on `localhost:6789`) and
> `vnstock` (internet, no desktop; reference price approximated from the prior
> close). With `source: "auto"` the runner uses DataPro when its desktop is up
> and **falls back to vnstock automatically** otherwise, so VN data loads with
> zero setup. This is the DEFAULT choice for any Vietnamese stock.

## Decision Tree

### Backtest Scenario (writing config.json)

Use `source: "auto"` — the runner automatically routes by symbol pattern and falls back to alternative sources if the primary one is unavailable.

You do NOT need to specify a concrete data source in config.json unless the user explicitly asks for one.

### Analysis / Research Scenario (writing Python scripts)

1. Identify the market type from the user's request
2. Pick the source by priority:

**Vietnam stocks (HOSE/HNX/UPCOM)**: datapro (price, if DataPro desktop up) > vnstock (price, internet fallback) + vnstock (fundamentals) — always; write symbols as `TICKER.VN`
**A-shares**: tushare (if TUSHARE_TOKEN is set) > akshare (free fallback)
**US stocks**: yfinance > akshare
**HK stocks**: yfinance > akshare
**Crypto**: okx (single exchange) > ccxt (multi-exchange)
**Futures**: tushare > akshare
**Macro / economics**: akshare > tushare
**Forex**: akshare > yfinance

3. Load the corresponding skill for API details: `load_skill("akshare")`

### Availability Check

- **tushare**: check if `TUSHARE_TOKEN` environment variable exists
- **datapro**: requires the DataPro desktop app running with its API on `localhost:6789` (set `DATAPRO_URL` / `DATAPRO_API_KEY` for a remote host)
- **vnstock**: free; needs internet. Serves VN **price** (OHLCV — the fallback when DataPro's desktop is off; set `VNSTOCK_PRICE_SOURCE` to `vci`/`kbs`, default `vci`) and **fundamentals** (community tier returns ~4 most-recent annual periods)
- **yfinance / okx / ccxt / akshare**: free but may have network restrictions
- If the user reports "connection timeout" or "cannot access", switch to the same-market fallback

## Symbol Format Reference

| Market | Format | Examples |
|--------|--------|---------|
| **Vietnam** | `TICKER.VN` | VCB.VN, FPT.VN, VNINDEX.VN |
| A-shares | `NNNNNN.SZ/SH/BJ` | 000001.SZ, 600000.SH |
| US stocks | `TICKER.US` | AAPL.US, MSFT.US |
| HK stocks | `NNN(N).HK` | 700.HK, 9988.HK |
| Crypto | `SYMBOL-USDT` | BTC-USDT, ETH-USDT |
| Futures | `XXNNNN.EXCHANGE` | CU2406.SHFE |
| Forex | `XXX/YYY` | USD/CNY, EUR/USD |

## Fallback Chain (Runner Layer)

The backtest runner implements automatic fallback at the market level:

```
User requests 000001.SZ (A-share)
  -> detect market: a_share
  -> try tushare: TUSHARE_TOKEN missing -> skip
  -> try akshare: available -> use akshare
  -> success (zero config required)
```

This is transparent to the user — they just see results.


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
