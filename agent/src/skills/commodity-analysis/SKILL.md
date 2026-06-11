---
name: commodity-analysis
description: Commodity analysis (oil supply-demand balance / gold pricing / copper as an economic predictor / inventory cycles / futures premium-discount structure / seasonality), generating directional commodity signals.
category: analysis
---
# Commodity Analysis

## Overview

Analyze commodities from four dimensions — supply-demand balance, pricing model, inventory cycle, and futures structure — and output directional signals suitable for backtesting. Focuses on crude oil (global pricing anchor), gold (safe haven + inflation hedge), and copper (economic barometer).

## Core Concepts

### 1. Crude Oil Supply-Demand Balance

**Key supply-side variables:**

| Variable | Data Source | Frequency | Direction of Impact |
|------|--------|------|---------|
| OPEC production | OPEC monthly report | Monthly | Production cuts → oil price ↑ |
| US shale output | EIA weekly report | Weekly | Higher output → oil price ↓ |
| Rig count (Baker Hughes) | Baker Hughes | Weekly | Leads production by 3-6 months |
| Strategic Petroleum Reserve (SPR) | EIA | Weekly | SPR release → short-term oil price ↓ |

**Key demand-side variables:**
- IEA global oil demand forecast (quarterly)
- China crude imports (customs monthly data)
- US gasoline demand (EIA weekly report, implied demand)
- Global PMI (leads demand by 1-2 months)

**Supply-demand balance signals:**

```python
# Simplified supply-demand judgment
if opec_compliance > 90% and us_rig_count_declining:
    supply_signal = "tight"  # bullish for oil
elif opec_compliance < 80% and us_production_rising:
    supply_signal = "loose"  # bearish for oil

if global_pmi > 50 and china_import_yoy > 5%:
    demand_signal = "strong"  # bullish for oil
elif global_pmi < 48 and china_import_yoy < 0:
    demand_signal = "weak"    # bearish for oil
```

### 2. Gold Pricing Framework

**Four-factor model:**

| Factor | Weight | Logic | Indicator |
|------|------|------|------|
| Real rates | 40% | Real rates ↓ → lower opportunity cost of holding gold → gold ↑ | 10Y TIPS yield |
| US dollar index | 25% | USD ↓ → gold becomes cheaper in pricing terms → gold ↑ | DXY |
| Safe-haven demand | 20% | Risk ↑ → safe-haven buying → gold ↑ | VIX + geopolitical risk index |
| Central-bank buying | 15% | Central-bank purchases → structural demand support | WGC quarterly report |

**Practical rules:**
- 10Y TIPS < 0%: strong support for gold (negative real rates mean negative holding cost)
- 10Y TIPS > 2%: pressure on gold (positive real rates reduce attractiveness)
- Correlation between DXY and gold is around -0.6, but not absolute (they both rose in 2022 due to safe-haven demand)
- Central-bank purchases >1000 tons / year (2022-2023 level): long-term structural bullish support

### 3. Dr. Copper as an Economic Predictor

**Copper as a leading indicator:**
- YoY copper-price change leads industrial production by about 2-3 months
- Copper / gold ratio is highly positively correlated with the US 10Y Treasury yield (`r > 0.7`)
- Copper breakout above the prior high confirms economic recovery

**Copper fundamental tracking:**

| Indicator | Data Source | Threshold |
|------|--------|------|
| LME copper inventory | LME daily report | <150k tons = tight |
| SHFE copper inventory | SHFE weekly report | WoW decline >10% = tight |
| Copper concentrate TC/RC | SMM | TC < $30/ton = tight mining supply |
| China copper imports | Customs monthly report | YoY growth >10% = strong demand |

### 4. Inventory Cycle Analysis

**Visible inventory vs hidden inventory:**
- Visible inventory: published by exchanges (LME / SHFE / COMEX), transparent and trackable
- Hidden inventory: bonded areas / trader warehouses, opaque but potentially larger
- The true turning point in prices is the turning point in total inventory

**Four inventory-cycle stages (using copper as example):**

```
Active restocking (price↑ volume↑) -> Passive restocking (price↓ volume↑) -> Active destocking (price↓ volume↓) -> Passive destocking (price↑ volume↓)
      mid bull market                 late bull market                 mid bear market                 late bear / early bull market
```

**Signal mapping:**

| Stage | Inventory Direction | Price Direction | Trading Signal |
|------|---------|---------|---------|
| Passive destocking | ↓ | ↑ | Long (best buying point) |
| Active restocking | ↑ | ↑ | Keep long positions |
| Passive restocking | ↑ | ↓ | Close longs (warning) |
| Active destocking | ↓ | ↓ | Short or stay neutral |

### 5. Futures Premium / Discount Structure

**Contango (futures > spot, normal market):**
- Supply is abundant, and the market prices in carrying costs (storage + funding)
- Roll yield is negative (`roll yield < 0`), unfavorable for long holders
- Deep contango (`far month - near month > 5%`) = severe oversupply

**Backwardation (futures < spot, inverted market):**
- Supply is tight, and spot premium reflects strong immediate demand
- Roll yield is positive (`roll yield > 0`), favorable for long holders
- Deep backwardation (`near month - far month > 3%`) = squeeze or extreme shortage

**Term-structure signal:**

```python
# Spread ratio = (front month - second month) / front month
spread_ratio = (front_month - second_month) / front_month

if spread_ratio > 0.02:    # backwardation > 2%
    signal = "strongly bullish"  # spot shortage
elif spread_ratio < -0.03: # contango > 3%
    signal = "bearish"           # oversupply
else:
    signal = "neutral"
```

### 6. Seasonality

**Oil seasonality:**
- March-May: refinery maintenance ends + summer inventory build → seasonal rise (ahead of the "driving season")
- September-October: hurricane season (Gulf of Mexico) → supply disruption → higher volatility
- November-December: heating-oil demand → stronger diesel crack spread

**Gold seasonality:**
- January-February: Lunar New Year + Indian wedding-season physical demand → relatively strong
- July-August: traditional soft season → relatively weak
- October-November: Diwali + Christmas restocking → relatively strong

**Copper seasonality:**
- March-April: China construction season starts → demand recovery
- June-July: off-season inventory buildup → pressure
- September-October: "Golden September, Silver October" → demand recovery

## Analysis Framework

### Five-Step Commodity Analysis

1. **Supply-demand sets direction**: is the balance in surplus or shortage? Which way are marginal variables moving?
2. **Inventory sets rhythm**: which inventory-cycle stage are we in? Is a turning point close?
3. **Term structure confirms**: contango or backwardation? Does it confirm the supply-demand judgment?
4. **Seasonality overlay**: is seasonality currently a tailwind or a headwind?
5. **Macro validation**: do the dollar / rates / risk appetite support the directional judgment?

### Composite Scoring Template

```python
commodity_score = {
    "supply_demand": +1,    # supply-demand is tight
    "inventory_cycle": +2,  # passive destocking (best stage)
    "term_structure": +1,   # mild backwardation
    "seasonality": 0,       # neutral seasonality
    "macro_env": -1,        # stronger dollar is a headwind
}
# Total score = +3/5 = +0.6 -> bullish bias, but not a strong signal
```

## Output Format

```
## Commodity Analysis Report — [Commodity Name]

### Supply-Demand Structure
- Supply side: [surplus / balanced / shortage] — [specific data]
- Demand side: [strong / stable / weak] — [specific data]
- Balance table: [inventory build X tons / drawdown X tons]

### Inventory Cycle
- Current stage: [active restocking / passive restocking / active destocking / passive destocking]
- Visible inventory: [LME X tons, SHFE X tons, WoW change]

### Term Structure
- Front-back spread: [contango X% / backwardation X%]
- Roll yield: [positive / negative]

### Composite Score
| Dimension | Score(-2~+2) | Basis |
|------|------------|------|
| Supply-demand | +1 | OPEC compliance rate 92% |
| Inventory | +2 | LME inventory hit 18-month low |

### Trading Direction
- Direction: [bullish / bearish / neutral]
- Confidence: [high / medium / low]
- Risk points: [specific risks]
```

## Notes

- Commodity data sources are fragmented (EIA / OPEC / LME / SHFE, etc.). This skill provides the analytical framework; data should be retrieved through `web-reader` or entered manually
- Futures prices include roll costs, so direct comparison across different contracts must account for expiry-roll effects
- Seasonal patterns are statistical averages and may be completely overwhelmed by fundamentals in a given year
- Gold has both commodity and financial attributes, and the financial side (rates / dollar) usually dominates short-term pricing
- Copper’s financial characteristics have strengthened since 2020 (copper futures are used as a macro hedge), so pure fundamental analysis may be insufficient
- Inventory data is lagged (hidden inventories cannot be tracked in real time), so cross-check with price and basis behavior
- This framework is for research backtesting only and does not constitute investment advice


## ⚠️ Nguyên tắc dữ liệu (BẮT BUỘC)

1. **Không bịa/cook số liệu.** Mọi số tài chính phải có nguồn thật. Luôn **audit nhanh, cross-check tối thiểu 2 nguồn uy tín** (vd `cafef.vn`, `vietstock.vn`) — dùng **crawl4ai** cào số rồi đối chiếu; nếu nguồn lệch nhau thì nêu rõ, không chọn bừa.
2. **Nếu DataPro VÀ vnstock đều KHÔNG có dữ liệu → ưu tiên crawl4ai** cào từ cafef/vietstock/web công ty để lấy số chính xác, RỒI mới phân tích. Không suy đoán thay số.
- Khoản mục ghi nhận **bất thường** (thu nhập khác / lãi đột biến / LNTT > LN gộp / lãi vay vốn hóa) → đọc **thuyết minh BCTC**, trích nguồn rồi mới diễn giải.
