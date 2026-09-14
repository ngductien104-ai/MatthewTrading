"""Explicit source adapters. Unknown vendor schemas become coverage gaps, not guesses."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .models import Observation, SourceSpec

VN = ZoneInfo("Asia/Ho_Chi_Minh")


class SourceSchemaError(ValueError):
    """A query succeeded but its columns do not match the configured contract."""

    def __init__(self, missing, columns):
        self.columns = [str(c) for c in columns]
        self.missing = sorted(missing)
        super().__init__(f"Missing columns {self.missing}; available: {self.columns}")


def stamp(value):
    dt = pd.Timestamp(value)
    if pd.isna(dt):
        raise ValueError("Missing source timestamp")
    return dt.tz_localize(VN).tz_convert("UTC").to_pydatetime() if dt.tzinfo is None else dt.tz_convert("UTC").to_pydatetime()


def in_session(now, holidays=()):
    local = now.astimezone(VN)
    return (local.weekday() < 5 and local.date().isoformat() not in holidays
            and (time(9) <= local.time().replace(tzinfo=None) <= time(11, 30)
                 or time(13) <= local.time().replace(tzinfo=None) <= time(15, 15)))


def is_trading_day(day: date, holidays=()) -> bool:
    return day.weekday() < 5 and day.isoformat() not in holidays


def latest_completed_session(now: datetime, holidays=()) -> datetime:
    """Return the latest Vietnamese equity close expected by ``now``.

    The calendar is deliberately configuration-driven. Weekends and the
    supplied full-day exchange holidays are skipped; Saturday make-up office
    days are never assumed to be trading days.
    """
    local = now.astimezone(VN)
    day = local.date()
    close = datetime.combine(day, time(15, 15), VN)
    if local < close or not is_trading_day(day, holidays):
        day -= timedelta(days=1)
    for _ in range(370):
        if is_trading_day(day, holidays):
            return datetime.combine(day, time(15, 15), VN).astimezone(timezone.utc)
        day -= timedelta(days=1)
    raise ValueError("No completed trading session found in configured calendar")


def session_freshness(spec: SourceSpec, latest: datetime | None, now: datetime, holidays=()) -> dict:
    """Evaluate EOD freshness independently from a coarse max-age threshold."""
    if spec.kind not in {"price", "sector"} or spec.kwargs.get("interval", "1D") != "1D":
        return {"session_fresh": None, "expected_session_close": None}
    expected = latest_completed_session(now, holidays)
    actual = latest.astimezone(timezone.utc) if latest else None
    return {"session_fresh": actual is not None and actual >= expected,
            "expected_session_close": expected.isoformat()}


def source_frame(spec: SourceSpec, now) -> pd.DataFrame:
    if spec.kind == "csv":
        return pd.read_csv(Path(spec.path))
    if spec.kind == "sector":
        from .sector import frame
        return frame(now)
    if spec.kind == "price":
        from vndata.price import ohlcv
        interval = spec.kwargs.get("interval", "1D")
        days = int(spec.kwargs.get("history_days", 3650 if interval == "1D" else 7))
        frame = ohlcv(spec.entity, (now - timedelta(days=days)).date().isoformat(),
                      now.astimezone(VN).date().isoformat(), interval=interval, allow_fallback=False)
        frame = frame.reset_index()
        if spec.date_column not in frame:
            frame = frame.rename(columns={frame.columns[0]: spec.date_column})
        return frame
    if spec.kind == "macro":
        from vndata.macro import series
        domain, method = spec.method.split(".", 1)
        return series(domain, method, **spec.kwargs)
    if spec.kind == "fundamental":
        from vndata.fundamental import statement, ratios
        return ratios(spec.entity, **spec.kwargs) if spec.method == "ratios" else statement(
            spec.entity, which=spec.method, **spec.kwargs)
    from vndata.news import company_news
    return company_news(spec.entity, **spec.kwargs)


def collect(spec: SourceSpec, now) -> tuple[list[Observation], dict]:
    frame = source_frame(spec, now)
    meta = {"id": spec.id, "indicator": spec.indicator, "entity": spec.entity,
            "domain": spec.domain, "source": spec.kind, "checked_at": now.isoformat(),
            "columns": [str(c) for c in frame.columns], "rows": len(frame)}
    if spec.filter_column:
        if spec.filter_column not in frame:
            raise SourceSchemaError({spec.filter_column}, frame.columns)
        frame = frame[frame[spec.filter_column].astype(str) == str(spec.filter_value)]
    required = {spec.date_column, spec.value_column}
    required.update(c for c in (spec.published_column, spec.closed_column, spec.entity_column) if c)
    if not required.issubset(frame):
        raise SourceSchemaError(required-set(frame), frame.columns)
    out = []
    for row in frame.to_dict("records"):
        value = pd.to_numeric(row[spec.value_column], errors="coerce")
        if pd.isna(value):
            continue
        raw_date = row[spec.date_column]
        if spec.kind == "fundamental":
            # Normalized statements use quarterly/annual periods, not publication dates.
            raw_date = pd.Period(str(raw_date), freq="Q" if "Q" in str(raw_date).upper() else "Y").end_time
        observed = stamp(raw_date)
        closed = True
        if spec.kind == "price" and spec.kwargs.get("interval", "1D") != "1D":
            interval = spec.kwargs["interval"]
            if interval not in {"1m", "5m", "15m"}:
                raise ValueError("Supported intraday intervals: 1m, 5m, 15m")
            observed += timedelta(minutes=int(interval[:-1]))
            closed = now >= observed
        elif spec.kind in {"price", "sector"}:
            # A vendor daily bar is provisional until the close; never label it a minute bar.
            local_date = observed.astimezone(VN).date()
            end = datetime.combine(local_date, time(15, 15), VN).astimezone(timezone.utc)
            closed = now >= end
            observed = end if closed else now
        elif spec.closed_column:
            closed = str(row[spec.closed_column]).lower() in {"true", "1"}
        published = stamp(row[spec.published_column]) if spec.published_column else observed
        if published > now or observed > now:
            continue
        # Hash changes in vendor content, even if the provider supplies no revision ID.
        revision = hashlib.sha256(str(value).encode()).hexdigest()[:16]
        entity = str(row[spec.entity_column]) if spec.entity_column else spec.entity
        out.append(Observation(indicator=spec.indicator, entity=entity, observed_at=observed,
                               published_at=published, received_at=now, value=float(value),
                               source=spec.id, unit=spec.unit, closed=closed, revision=revision,
                               point_in_time=False, group=spec.group))
    meta.update(status="available" if out else "unavailable",
                first_observed=min((o.observed_at.isoformat() for o in out), default=None),
                last_observed=max((o.observed_at.isoformat() for o in out), default=None),
                limitation="Retrospective feed; historical vintages not certified")
    if out and (now-max(o.published_at for o in out)).total_seconds() > spec.max_age_seconds:
        meta["status"] = "stale"
    return out, meta
