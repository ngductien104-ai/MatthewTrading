"""Purged walk-forward event studies with a fixed, pre-registered objective."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .detection import feature
from .models import ResearchProtocol, Rule, Validation, digest


def backtest(frame: pd.DataFrame, rule: Rule, *, bootstrap=2000,
             protocol: ResearchProtocol | None = None) -> dict:
    """Input: one point-in-time value per decision and adjusted target close.

    Rows must already be joined as-of publication AND receipt, using historical
    constituents. A vintage audit is required for promotion; retrospective
    vendor downloads may be explored but cannot certify a rule.
    """
    protocol = protocol or ResearchProtocol(hypothesis_id=rule.id, family_id=rule.id,
                                            variant_id=rule.fingerprint)
    required = {"time", "value", "target_close", "published_at", "received_at", "point_in_time"}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"Missing research columns: {sorted(missing)}")
    data = frame.copy()
    for column in ("time", "published_at", "received_at"):
        data[column] = pd.to_datetime(data[column], utc=True, errors="raise")
    if data.time.duplicated().any() or not data.time.is_monotonic_increasing:
        raise ValueError("Decision times must be unique and sorted")
    if (data.published_at > data.time).any() or (data.received_at > data.time).any():
        raise ValueError("Lookahead: data not available at decision time")
    for column in ("value", "target_close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if not np.isfinite(data[["value", "target_close"]].to_numpy()).all() or (data.target_close <= 0).any():
        raise ValueError("Research values must be finite; adjusted closes must be positive")
    dataset_hash = digest(data.to_json(date_format="iso", orient="records"))
    horizon = rule.horizon
    minimum = rule.window + 6
    split = max(minimum, len(data) // 2)
    if len(data) - split < 3 * (horizon + 10):
        raise ValueError("Insufficient history for three purged out-of-sample windows")
    x = feature(data.value.to_numpy(), rule.family)
    eligible_rows = (data["event_eligible"].map(
        lambda value: value is True or str(value).lower() == "true").to_numpy()
        if "event_eligible" in data else np.ones(len(data), dtype=bool))
    prices = data.target_close.to_numpy()
    sign = 1 if rule.objective == "up" else -1
    edges = np.linspace(split, len(data), 4, dtype=int)
    events, baseline, windows = [], [], []
    last_event = -horizon - 1
    for fold, (start, stop) in enumerate(zip(edges[:-1], edges[1:])):
        fold_events, fold_base = [], []
        # Embargo each boundary and keep labels inside the same test window.
        for i in range(start + horizon, stop - horizon):
            outcome = sign * (prices[i+horizon] / prices[i] - 1)
            if (i - start - horizon) % (horizon + 1) == 0:
                fold_base.append(float(outcome))
            past = x[i-rule.window:i]
            threshold = np.quantile(past, rule.quantile if rule.side == "high" else 1-rule.quantile)
            hit = (x[i] > threshold if rule.side == "high" else x[i] < threshold) and eligible_rows[i]
            if hit and i - last_event > horizon:
                last_event = i
                path = prices[i+1:i+horizon+1] / prices[i] - 1
                fold_events.append({"time": data.time.iloc[i].isoformat(), "fold": fold,
                                    "return": float(outcome), "threshold": float(threshold),
                                    "adverse_excursion": float(min(0, np.min(sign * path)))})
        events.extend(fold_events)
        baseline.extend(fold_base)
        windows.append({"fold": fold, "events": len(fold_events), "baseline": fold_base,
                        "outcomes": [e["return"] for e in fold_events]})
    limits = []
    pit = bool(data.point_in_time.map(lambda v: v is True or str(v).lower() == "true").all())
    if not pit:
        limits.append("Publication/vintage history is unverified")
    if protocol.synthetic:
        limits.append("Synthetic dataset cannot certify a production rule")
    for column in ("adjusted_target", "historical_universe"):
        if column not in data or not data[column].map(lambda v: v is True or str(v).lower() == "true").all():
            limits.append(f"Missing audit: {column}")
    rng = np.random.default_rng(42)
    active = [w for w in windows if w["outcomes"] and w["baseline"]]
    low = high = false_rate = None
    if events and active:
        # Resample within chronological folds; weight by independent event counts.
        boot = np.zeros(bootstrap)
        count = sum(len(w["outcomes"]) for w in active)
        for w in active:
            outcomes, base = np.array(w["outcomes"]), np.array(w["baseline"])
            delta = (rng.choice(outcomes, (bootstrap, len(outcomes))).mean(axis=1)
                     - rng.choice(base, (bootstrap, len(base))).mean(axis=1))
            boot += delta * len(outcomes) / count
        adjusted_alpha = protocol.alpha / protocol.variants_tested
        low, high = (float(v) for v in np.quantile(
            boot, [adjusted_alpha / 2, 1 - adjusted_alpha / 2]))
        false_rate = float(np.mean([e["return"] <= 0 for e in events]))
    evidence = digest({"dataset_hash": dataset_hash, "rule": rule.fingerprint,
                       "protocol": protocol.model_dump(mode="json")})
    validation = Validation(rule_version=rule.fingerprint, objective=rule.objective, horizon=horizon,
                            independent_events=len(events), windows=len(active),
                            improvement_ci_low=low, improvement_ci_high=high,
                            false_positive_rate=false_rate, point_in_time=pit,
                            limitations=limits, evidence_hash=evidence, dataset_hash=dataset_hash,
                            multiple_testing_method=protocol.multiple_testing_method,
                            variants_tested=protocol.variants_tested, holdout_id=protocol.holdout_id,
                            synthetic=protocol.synthetic)
    return {"validation": validation.model_dump(mode="json"), "eligible": validation.eligible,
            "events": events, "windows": windows, "baseline_mean": float(np.mean(baseline)) if baseline else None,
            "returns_quantiles": [float(v) for v in np.quantile([e["return"] for e in events], [.1,.5,.9])] if events else [],
            "lead_time": "Not estimated: requires an independently defined event onset label",
            "protocol": protocol.model_dump(mode="json"),
            "multiple_testing": {
                "method": protocol.multiple_testing_method,
                "variants_tested": protocol.variants_tested,
                "family_alpha": protocol.alpha,
                "per_variant_alpha": protocol.alpha / protocol.variants_tested,
                "holdout_id": protocol.holdout_id,
            }}
