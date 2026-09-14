"""Small verified starting universe; optional coverage is explicitly visible."""
from .models import Rule, Settings, SourceSpec


# HNX/HOSE 2026 full-day closures, including the 02/01 adjustment. Exchange
# notices explicitly say Saturday make-up office days are not trading days.
VN_EQUITY_HOLIDAYS_2026 = [
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-27", "2026-04-30", "2026-05-01",
    "2026-08-31", "2026-09-01", "2026-09-02",
]


def default_settings():
    sources = []
    rules = []
    for entity in ("VNINDEX", "VN30INDEX", "HNXINDEX", "UPCOMINDEX"):
        for column, unit, group in (("close", "index_points", "price"), ("volume", "shares", "liquidity")):
            identity = f"{entity.lower()}_{column}"
            sources.append(SourceSpec(id=identity, kind="price", domain="market", indicator=identity,
                                      entity=entity, unit=unit, group=group, value_column=column))
            rules.append(Rule(id=identity + "_high", indicator=identity))
            rules.append(Rule(id=identity + "_low", indicator=identity, side="low"))
    sources.append(SourceSpec(id="vn_cpi", kind="nso_cpi", domain="macro", indicator="vn_cpi",
                              entity="Vietnam", unit="percent_yoy", group="inflation",
                              value_column="cpi_total", published_column="published_at",
                              point_in_time=True,
                              cadence_seconds=86400, max_age_seconds=86400*45))
    rules.append(Rule(id="vn_cpi_high", indicator="vn_cpi", window=24, horizon=20))
    sources.append(SourceSpec(id="icb_strength", kind="sector", domain="sector", indicator="icb_strength",
                              entity="ICB", entity_column="entity", unit="percentage_points", group="relative_strength",
                              value_column="relative_strength_pct"))
    sources.append(SourceSpec(id="market_breadth", kind="sector", domain="market", indicator="market_breadth",
                              entity="VN_MARKET", unit="percent", group="breadth", value_column="above_ma50_pct",
                              filter_column="entity", filter_value="VN_MARKET"))
    rules.extend([Rule(id="icb_strength_high", indicator="icb_strength", objective="up"),
                  Rule(id="icb_strength_low", indicator="icb_strength", side="low"),
                  Rule(id="breadth_low", indicator="market_breadth", side="low")])
    sources.extend([
        SourceSpec(id="us_policy_rate", kind="macro", domain="macro", indicator="us_policy_rate",
                   entity="United States", unit="percent_per_year", group="global_rates",
                   method="global.fed_rate", value_column="close", cadence_seconds=86400,
                   max_age_seconds=86400*65),
        SourceSpec(id="usd_index", kind="macro", domain="macro", indicator="usd_index",
                   entity="DXY", unit="index_points", group="global_fx",
                   method="global.index", value_column="close", kwargs={"symbol": "DXY"},
                   cadence_seconds=3600, max_age_seconds=86400*4),
    ])
    rules.extend([
        Rule(id="us_policy_rate_high", indicator="us_policy_rate", window=24, horizon=20),
        Rule(id="us_policy_rate_low", indicator="us_policy_rate", window=24, horizon=20, side="low"),
        Rule(id="usd_index_high", indicator="usd_index", window=60),
        Rule(id="usd_index_low", indicator="usd_index", window=60, side="low"),
    ])
    # These remain disabled until a portfolio/watchlist or verified table is supplied.
    for identity, domain, group in (("company_earnings", "company", "fundamental"),
                                     ("company_disclosures", "company", "events")):
        sources.append(SourceSpec(id=identity, kind="csv", domain=domain, indicator=identity,
                                  entity="UNCONFIGURED", unit="unconfigured", group=group, enabled=False))
    return Settings(sources=sources, rules=rules, holidays=VN_EQUITY_HOLIDAYS_2026,
                    local_model="qwen2.5:3b-16k")
