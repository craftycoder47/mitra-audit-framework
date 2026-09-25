"""Fail-closed audit primitives for multi-source evidence.

This module is intentionally independent from any production system. It accepts
plain dictionaries, performs deterministic checks, and returns an explainable
stage-by-stage result.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class AuditState(str, Enum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNPROVEN = "UNPROVEN"


class SyncGrade(str, Enum):
    PARTIAL_STRONG = "PARTIAL_STRONG"
    PARTIAL_TYPICAL = "PARTIAL_TYPICAL"
    PARTIAL_WEAK = "PARTIAL_WEAK"
    FAILED = "FAILED"
    UNPROVEN = "UNPROVEN"


@dataclass(frozen=True)
class StageResult:
    state: AuditState
    reason: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class AuditResult:
    overall: AuditState
    stages: dict[str, StageResult]
    economics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["overall"] = self.overall.value
        for value in data["stages"].values():
            value["state"] = value["state"].value
        return data


def _finite_non_negative(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0:
        return None
    return number


def theoretical_margin_pct(odds: Mapping[str, Any]) -> float:
    """Return the theoretical three-way margin percentage.

    Formula: (1 / sum(1 / odd_i) - 1) * 100.
    Positive values indicate a theoretical cross-source surplus before any
    additional costs. The function does not claim executability.
    """
    if len(odds) < 2:
        raise ValueError("at least two outcomes are required")

    parsed: list[float] = []
    for label, raw in odds.items():
        try:
            odd = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid odd for {label!r}") from exc
        if not isfinite(odd) or odd <= 1.0:
            raise ValueError(f"odd for {label!r} must be finite and > 1.0")
        parsed.append(odd)

    implied = sum(1.0 / odd for odd in parsed)
    return (1.0 / implied - 1.0) * 100.0


def _real_stage(payload: Mapping[str, Any]) -> StageResult:
    same_event = payload.get("same_event")
    same_rules = payload.get("same_rules")
    evidence = {"same_event": same_event, "same_rules": same_rules}

    if same_event is False or same_rules is False:
        return StageResult(AuditState.FAILED, "event or settlement/rules mismatch", evidence)
    if same_event is not True or same_rules is not True:
        return StageResult(AuditState.UNPROVEN, "event/rules identity is not fully evidenced", evidence)
    return StageResult(AuditState.PASS, "event and rules identity are evidenced", evidence)


def _sync_stage(payload: Mapping[str, Any]) -> StageResult:
    span = _finite_non_negative(payload.get("source_span_s"))
    stale = _finite_non_negative(payload.get("max_stale_s"))
    hard = _finite_non_negative(payload.get("hard_stale_s", 60.0))
    evidence = {"source_span_s": span, "max_stale_s": stale, "hard_stale_s": hard}

    if span is None or stale is None or hard is None:
        evidence["grade"] = SyncGrade.UNPROVEN.value
        return StageResult(AuditState.UNPROVEN, "timing evidence is missing or invalid", evidence)
    if stale > hard:
        evidence["grade"] = SyncGrade.FAILED.value
        return StageResult(AuditState.FAILED, "hard staleness limit exceeded", evidence)
    if span <= 10.0 and stale <= 20.0:
        grade = SyncGrade.PARTIAL_STRONG
    elif span <= 30.0 and stale <= 45.0:
        grade = SyncGrade.PARTIAL_TYPICAL
    else:
        grade = SyncGrade.PARTIAL_WEAK
    evidence["grade"] = grade.value
    return StageResult(
        AuditState.PARTIAL,
        "timing is measured, but timestamps alone do not prove simultaneous executability",
        evidence,
    )


def _stakeability_stage(payload: Mapping[str, Any]) -> StageResult:
    raw = payload.get("stakeability")
    if not isinstance(raw, Mapping):
        return StageResult(AuditState.UNPROVEN, "stakeability evidence is absent", {})

    available = raw.get("quotes_available")
    accepted = raw.get("acceptance_verified")
    capacity = raw.get("capacity_verified")
    evidence = {
        "quotes_available": available,
        "acceptance_verified": accepted,
        "capacity_verified": capacity,
    }

    if available is False:
        return StageResult(AuditState.FAILED, "required quote is unavailable", evidence)
    if available is not True:
        return StageResult(AuditState.UNPROVEN, "quote availability is not evidenced", evidence)
    if accepted is True and capacity is True:
        return StageResult(AuditState.PASS, "acceptance and capacity are evidenced", evidence)
    if accepted is False or capacity is False:
        return StageResult(AuditState.FAILED, "acceptance or capacity check failed", evidence)
    return StageResult(AuditState.PARTIAL, "quotes exist but acceptance/capacity are not fully verified", evidence)


def _cost_stage(payload: Mapping[str, Any]) -> StageResult:
    raw = payload.get("costs")
    if not isinstance(raw, Mapping):
        return StageResult(AuditState.UNPROVEN, "cost evidence is absent", {})

    known = raw.get("known")
    extra = _finite_non_negative(raw.get("extra_cost_pct"))
    evidence = {"known": known, "extra_cost_pct": extra}

    if known is not True or extra is None:
        return StageResult(AuditState.UNPROVEN, "all extra costs are not evidenced", evidence)
    return StageResult(AuditState.PASS, "declared extra costs are explicit", evidence)


def _db_stage(payload: Mapping[str, Any]) -> StageResult:
    raw = payload.get("db")
    if not isinstance(raw, Mapping):
        return StageResult(AuditState.UNPROVEN, "database comparison evidence is absent", {})

    present = raw.get("record_present")
    formula_match = raw.get("formula_match")
    evidence = {"record_present": present, "formula_match": formula_match}

    if present is False or formula_match is False:
        return StageResult(AuditState.FAILED, "stored record disagrees with reconstructed evidence", evidence)
    if present is not True or formula_match is not True:
        return StageResult(AuditState.UNPROVEN, "database agreement is not fully evidenced", evidence)
    return StageResult(AuditState.PASS, "stored record agrees with reconstructed evidence", evidence)


def _overall(stages: Mapping[str, StageResult]) -> AuditState:
    states = {stage.state for stage in stages.values()}
    if AuditState.FAILED in states:
        return AuditState.FAILED
    if AuditState.UNPROVEN in states:
        return AuditState.UNPROVEN
    if AuditState.PARTIAL in states:
        return AuditState.PARTIAL
    return AuditState.PASS


def audit_payload(payload: Mapping[str, Any]) -> AuditResult:
    """Audit one synthetic/anonymised multi-source payload.

    Order is deliberately fixed: REAL -> SYNC -> STAKEABILITY -> COSTS -> DB.
    No stage silently converts missing evidence into PASS.
    """
    raw_odds = payload.get("best_outcome_odds")
    economics: dict[str, Any] = {"theoretical_margin_pct": None, "net_after_extra_cost_pct": None}

    if isinstance(raw_odds, Mapping):
        try:
            margin = theoretical_margin_pct(raw_odds)
        except ValueError as exc:
            economics["error"] = str(exc)
        else:
            economics["theoretical_margin_pct"] = round(margin, 6)
            raw_costs = payload.get("costs")
            if isinstance(raw_costs, Mapping):
                extra = _finite_non_negative(raw_costs.get("extra_cost_pct"))
                if extra is not None:
                    economics["net_after_extra_cost_pct"] = round(margin - extra, 6)

    stages = {
        "REAL": _real_stage(payload),
        "SYNC": _sync_stage(payload),
        "STAKEABILITY": _stakeability_stage(payload),
        "COSTS": _cost_stage(payload),
        "DB": _db_stage(payload),
    }
    return AuditResult(overall=_overall(stages), stages=stages, economics=economics)
