"""Point-in-time research datasets with explicit feature and audit manifests."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from .models import DatasetManifest, FeatureSpec, Observation, digest


def build_dataset(observations: list[Observation], target: pd.DataFrame, feature: FeatureSpec,
                  *, entity: str, target_entity: str, target_time="time", target_close="close",
                  horizons=(1, 5, 20), adjusted_target=False, historical_universe=False,
                  synthetic=False) -> tuple[pd.DataFrame, DatasetManifest]:
    """As-of join observations onto trading sessions without publication look-ahead.

    Rows remain at the target's trading-session cadence so a 5-row horizon is
    five sessions. ``event_eligible`` is true only on the first session where a
    new vintage was knowable, preventing monthly releases from becoming many
    pseudo-independent daily events after forward filling.
    """
    relevant = [o for o in observations if o.indicator == feature.indicator
                and o.entity == entity and o.closed]
    if not relevant:
        raise ValueError("No closed observations match feature indicator/entity")
    if any(o.unit != feature.unit for o in relevant):
        raise ValueError("Feature unit does not match observation unit")
    horizons = sorted(set(int(h) for h in horizons))
    if not horizons or horizons[0] < 1:
        raise ValueError("Research horizons must be positive")

    prices = target.copy()
    missing = {target_time, target_close} - set(prices)
    if missing:
        raise ValueError(f"Missing target columns: {sorted(missing)}")
    prices[target_time] = pd.to_datetime(prices[target_time], utc=True, errors="raise")
    prices[target_close] = pd.to_numeric(prices[target_close], errors="raise")
    prices = prices.sort_values(target_time).reset_index(drop=True)
    if prices[target_time].duplicated().any():
        raise ValueError("Target session timestamps must be unique")
    if not np.isfinite(prices[target_close]).all() or (prices[target_close] <= 0).any():
        raise ValueError("Target closes must be finite and positive")

    vintages = sorted(relevant, key=lambda o: (max(o.published_at, o.received_at), o.observed_at))
    target_times = prices[target_time].tolist()
    rows, cursor, current = [], 0, None
    for index, decision in enumerate(target_times):
        changed = False
        while cursor < len(vintages) and max(vintages[cursor].published_at,
                                              vintages[cursor].received_at) <= decision.to_pydatetime():
            current = vintages[cursor]
            cursor += 1
            changed = True
        if current is None:
            continue
        row = {
            "time": decision,
            "value": current.value,
            "target_close": float(prices.loc[index, target_close]),
            "observed_at": current.observed_at,
            "published_at": current.published_at,
            "received_at": current.received_at,
            "point_in_time": current.point_in_time,
            "adjusted_target": bool(adjusted_target),
            "historical_universe": bool(historical_universe),
            "event_eligible": changed,
            "source": current.source,
            "revision": current.revision,
        }
        for horizon in horizons:
            future = index + horizon
            row[f"target_return_{horizon}"] = (
                float(prices.loc[future, target_close] / prices.loc[index, target_close] - 1)
                if future < len(prices) else np.nan
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("No target session occurs after an observation became available")
    serial = frame.to_json(orient="records", date_format="iso")
    manifest = DatasetManifest(
        dataset_hash=digest(serial), feature_id=feature.id, feature_version=feature.version,
        feature_hash=feature.fingerprint, indicator=feature.indicator, entity=entity,
        target_entity=target_entity, rows=len(frame), start=frame.time.iloc[0].isoformat(),
        end=frame.time.iloc[-1].isoformat(), horizons=horizons,
        point_in_time=bool(frame.point_in_time.all()), adjusted_target=bool(adjusted_target),
        historical_universe=bool(historical_universe), synthetic=bool(synthetic),
    )
    return frame, manifest


def write_dataset(frame: pd.DataFrame, manifest: DatasetManifest, output: Path) -> tuple[Path, Path]:
    """Atomically write a CSV and adjacent immutable manifest."""
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    token = uuid.uuid4().hex
    csv_tmp = output.with_name(f".{output.name}.{token}.tmp")
    manifest_tmp = manifest_path.with_name(f".{manifest_path.name}.{token}.tmp")
    frame.to_csv(csv_tmp, index=False)
    manifest_tmp.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    os.replace(csv_tmp, output)
    os.replace(manifest_tmp, manifest_path)
    return output, manifest_path


def read_manifest(path: Path) -> DatasetManifest:
    return DatasetManifest.model_validate_json(path.read_text(encoding="utf-8"))
