"""Versioned contracts shared by collectors, replay, agents and the terminal."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str, allow_nan=False).encode()).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Observation(Contract):
    indicator: str
    entity: str
    observed_at: datetime
    published_at: datetime
    received_at: datetime
    value: float
    source: str
    unit: str
    revision: str = "original"
    closed: bool = True
    point_in_time: bool = False
    group: str = ""

    @field_validator("observed_at", "published_at", "received_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def dates(self):
        if self.published_at > self.received_at:
            raise ValueError("publication cannot be after receipt")
        if self.observed_at > self.published_at:
            raise ValueError("observation cannot be after publication")
        return self


class Indicator(Contract):
    id: str
    domain: Literal["macro", "market", "sector", "company"]
    group: str
    unit: str
    description: str
    cadence_seconds: int = Field(default=300, ge=60)
    max_age_seconds: int = Field(default=86400 * 5, ge=60)
    closed_only: bool = True


class Validation(Contract):
    rule_version: str
    objective: str
    horizon: int
    independent_events: int = 0
    windows: int = 0
    improvement_ci_low: float | None = None
    improvement_ci_high: float | None = None
    false_positive_rate: float | None = None
    point_in_time: bool = False
    limitations: list[str] = Field(default_factory=list)
    evidence_hash: str = ""
    dataset_hash: str = ""
    multiple_testing_method: Literal["single_hypothesis", "bonferroni"] = "single_hypothesis"
    variants_tested: int = Field(default=1, ge=1)
    holdout_id: str = ""
    synthetic: bool = False

    @property
    def eligible(self) -> bool:
        return (not self.synthetic and self.point_in_time and self.independent_events >= 30 and self.windows >= 3
                and self.improvement_ci_low is not None and self.improvement_ci_low > 0
                and bool(self.evidence_hash) and bool(self.dataset_hash) and not self.limitations)


class Rule(Contract):
    id: str
    indicator: str
    version: str = "1"
    family: Literal["threshold", "trend", "pattern"] = "threshold"
    window: int = Field(default=60, ge=10)
    quantile: float = Field(default=0.95, gt=0.5, lt=1)
    side: Literal["high", "low"] = "high"
    horizon: int = Field(default=5, ge=1)
    objective: Literal["up", "down"] = "down"
    validation: Validation | None = None

    @property
    def fingerprint(self) -> str:
        return digest(self.model_dump(exclude={"validation"}))


class Signal(Contract):
    id: str
    indicator: str
    entity: str
    domain: str
    group: str
    observed_at: datetime
    detected_at: datetime
    value: float
    threshold: float
    feature_value: float | None = None
    threshold_unit: str = ""
    trend: str
    pattern: str
    rule_id: str
    rule_version: str
    rule_status: Literal["candidate", "shadow", "validated", "retired"] = "candidate"
    snapshot: str
    source: str
    unit: str
    source_detail: dict = Field(default_factory=dict)
    tier: Literal["radar", "priority"] = "radar"
    severity: Literal["watch", "elevated"] = "watch"
    direction: Literal["risk", "opportunity", "mixed"] = "mixed"
    state: Literal["new", "updated", "expired"] = "new"
    acknowledged_at: str | None = None
    ai_status: Literal["pending", "running", "completed", "failed"] = "pending"
    ai_error: str | None = None
    analysis: dict | None = None
    validation: Validation | None = None
    confirmation_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    portfolio: dict = Field(default_factory=dict)


class SourceSpec(Contract):
    id: str
    kind: Literal["csv", "price", "macro", "fundamental", "news", "sector", "nso_cpi"]
    domain: Literal["macro", "market", "sector", "company"]
    indicator: str
    entity: str
    unit: str
    group: str
    path: str = ""
    method: str = ""
    date_column: str = "time"
    value_column: str = "value"
    published_column: str | None = None
    closed_column: str | None = None
    filter_column: str | None = None
    filter_value: str | None = None
    kwargs: dict = Field(default_factory=dict)
    cadence_seconds: int = Field(default=300, ge=60)
    max_age_seconds: int = Field(default=86400 * 5, ge=60)
    enabled: bool = True
    closed_only: bool = True
    entity_column: str | None = None
    point_in_time: bool = False


class Settings(Contract):
    state_dir: str = ".third-eyes"
    sources: list[SourceSpec] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)
    holidays: list[str] = Field(default_factory=list)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_base_seconds: float = Field(default=1.0, ge=0, le=300)
    retry_max_seconds: float = Field(default=30.0, ge=0, le=3600)
    retry_jitter_seconds: float = Field(default=0.5, ge=0, le=60)
    max_consecutive_failures: int = Field(default=5, ge=1, le=100)
    failure_cooldown_seconds: int = Field(default=300, ge=1, le=86400)
    log_max_bytes: int = Field(default=5_000_000, ge=1024)
    log_backup_count: int = Field(default=5, ge=1, le=100)
    excel_directory: str | None = None
    account_env: str = "ACCOUNT_LOOKUP_TOKEN"
    customer_env: str = "CUSTOMER_LOOKUP_TOKEN"
    local_model: str = ""
    local_url: str = "http://127.0.0.1:11434"
    ai_enabled: bool = True
    ai_batch_seconds: int = Field(default=300, ge=1)
    ai_timeout_seconds: int = Field(default=600, ge=1, le=600)
    research_csv: dict[str, str] = Field(default_factory=dict)
    research_horizons: list[int] = Field(default_factory=lambda: [1, 5, 20])
    watchlist: list[str] = Field(default_factory=list)

    @field_validator("holidays")
    @classmethod
    def valid_holidays(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("holiday dates must be unique")
        for value in values:
            date.fromisoformat(value)
        return sorted(values)

    @field_validator("research_horizons")
    @classmethod
    def valid_research_horizons(cls, values):
        if not values or any(value < 1 for value in values):
            raise ValueError("research horizons must be positive")
        return sorted(set(values))

    @model_validator(mode="after")
    def unique_ids(self):
        for entries in (self.sources, self.rules):
            if len({s.id for s in entries}) != len(entries):
                raise ValueError("duplicate source/rule ids")
        return self


class FeatureSpec(Contract):
    id: str
    indicator: str
    version: str = "1"
    family: Literal["threshold", "trend", "pattern"] = "threshold"
    unit: str
    description: str

    @property
    def fingerprint(self) -> str:
        return digest(self.model_dump())


class ResearchProtocol(Contract):
    hypothesis_id: str
    family_id: str
    variant_id: str
    variants_tested: int = Field(default=1, ge=1)
    holdout_id: str = ""
    multiple_testing_method: Literal["single_hypothesis", "bonferroni"] = "single_hypothesis"
    alpha: float = Field(default=0.05, gt=0, lt=0.5)
    synthetic: bool = False

    @model_validator(mode="after")
    def multiplicity_contract(self):
        if self.variants_tested > 1:
            if self.multiple_testing_method != "bonferroni":
                raise ValueError("Multiple variants require Bonferroni correction")
            if not self.holdout_id:
                raise ValueError("Multiple variants require an explicit holdout_id")
        return self


class DatasetManifest(Contract):
    schema_version: str = "1"
    dataset_hash: str
    feature_id: str
    feature_version: str
    feature_hash: str
    indicator: str
    entity: str
    target_entity: str
    rows: int = Field(ge=0)
    start: str | None = None
    end: str | None = None
    horizons: list[int]
    point_in_time: bool
    adjusted_target: bool
    historical_universe: bool
    synthetic: bool = False


class RuleRegistration(Contract):
    rule_id: str
    rule_version: str
    status: Literal["candidate", "shadow", "validated", "retired"] = "candidate"
    rule: dict
    certificate_id: str | None = None
    reason: str
    updated_at: str
