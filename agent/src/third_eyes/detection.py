"""Deterministic rules; all calibration values strictly precede the candidate."""
from __future__ import annotations

import numpy as np

from .models import Indicator, Observation, Rule, Signal, digest


def feature(values: np.ndarray, family: str) -> np.ndarray:
    if family == "threshold":
        return values
    if family == "trend":
        return np.concatenate(([np.nan] * 4, [np.polyfit(np.arange(5), values[i-4:i+1], 1)[0]
                                               for i in range(4, len(values))]))
    # A change in direction/acceleration, rather than a discretionary LLM pattern.
    return np.concatenate(([np.nan] * 2, np.diff(values, n=2)))


def evaluate(history: list[Observation], rule: Rule, indicator: Indicator, snapshot: str, now) -> Signal | None:
    history = [o for o in history if o.observed_at <= now and o.published_at <= now
               and o.received_at <= now and (o.closed or not indicator.closed_only)]
    if len(history) < rule.window + 6:
        return None
    last = history[-1]
    if last.unit != indicator.unit or (now - last.published_at).total_seconds() > indicator.max_age_seconds:
        return None
    values = np.asarray([o.value for o in history], dtype=float)
    transformed = feature(values, rule.family)
    past = transformed[-rule.window-1:-1]
    if not np.isfinite(past).all():
        return None
    threshold = float(np.quantile(past, rule.quantile if rule.side == "high" else 1-rule.quantile))
    current = float(transformed[-1])
    hit = current > threshold if rule.side == "high" else current < threshold
    if not hit:
        return None
    trend = "rising" if values[-1] > values[-5] else "falling" if values[-1] < values[-5] else "flat"
    limits = [] if all(o.point_in_time for o in history) else ["Historical publication/vintage data not verified"]
    if last.observed_at.date() < now.date():
        limits.append("Delayed observation; inspect observed_at before using this signal")
    return Signal(
        id=digest([rule.fingerprint, last.entity, last.observed_at.isoformat()]),
        indicator=indicator.id, entity=last.entity, domain=indicator.domain, group=indicator.group,
        observed_at=last.observed_at, detected_at=now, value=last.value, threshold=threshold,
        trend=trend, pattern=rule.family, rule_id=rule.id, rule_version=rule.fingerprint,
        feature_value=current, threshold_unit=last.unit if rule.family == "threshold" else last.unit+"/observation",
        snapshot=snapshot, source=last.source, unit=last.unit, validation=rule.validation,
        direction="risk" if rule.objective == "down" else "opportunity", limitations=limits,
    )


def confirm(signals: list[Signal]) -> list[Signal]:
    for signal in signals:
        peers = [s.id for s in signals if s.id != signal.id and s.entity == signal.entity
                 and s.group != signal.group and s.direction == signal.direction
                 and s.state != "expired" and abs((s.observed_at-signal.observed_at).total_seconds()) <= 86400]
        signal.confirmation_ids = peers
        validated = (signal.rule_status == "validated" and signal.validation is not None
                     and signal.validation.eligible
                     and signal.validation.rule_version == signal.rule_version)
        signal.tier = "priority" if validated and peers and not signal.limitations else "radar"
        signal.severity = "elevated" if signal.tier == "priority" else "watch"
    return signals
