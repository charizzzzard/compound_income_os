"""Operator-facing wording helpers for review evidence surfaces.

The helpers in this module only transform display text. They do not change
scoring, ranking, valuation, portfolio, or buy/sell semantics.
"""

from __future__ import annotations

from typing import Any


DISPLAY_WORDING = {
    "BUYABLE": "Reviewable candidate; operator review required; not an order instruction",
    "eligible_for_purchase": "Passes local screening; operator review required",
    "valuation_comment": "Valuation evidence note",
    "fair_value_estimate": "Heuristic fair-value estimate based on available inputs",
    "margin_of_safety_pct": "Indicative margin-of-safety field; not certainty",
    "Unterbewertung": "Possible valuation discount based on current inputs",
}

DEGRADED_STATE_TERMS = (
    "MISSING",
    "MISSING_DATA",
    "REVIEW",
    "STALE",
    "CONFLICT",
    "UNKNOWN",
    "BLOCKED",
)


def operator_boundary_note() -> str:
    return (
        "Operator note: review evidence only; Human Operator remains final authority; "
        "not investment advice; no order is placed."
    )


def allocation_status_label(status: str, target_action: str = "") -> str:
    normalized = (status or "").strip().upper()
    action = (target_action or "").strip().upper()
    if action == "HOLD_CASH":
        return "Cash-hold review evidence; operator review required"
    if normalized == "SELECTED_THIS_MONTH":
        return "Selected for operator review this month; not an order instruction"
    if normalized == "ELIGIBLE_NOT_FUNDED":
        return "Reviewable candidate; not funded this month; not an order instruction"
    if normalized == "NOT_ELIGIBLE":
        return "Not reviewable for allocation in this run"
    if normalized:
        return f"{normalized}; operator review required"
    return "Review state unavailable; operator review required"


def execution_mode_evidence(mode: str, reason: str = "") -> str:
    mode_text = (mode or "UNKNOWN").strip() or "UNKNOWN"
    reason_text = (reason or "").strip()
    if reason_text:
        return (
            f"Execution-mode evidence: {mode_text} ({reason_text}); "
            "operator review required; no order is placed."
        )
    return (
        f"Execution-mode evidence: {mode_text}; "
        "operator review required; no order is placed."
    )


def valuation_evidence_note(comment: Any) -> str:
    text = str(comment or "").strip()
    if not text:
        text = "No valuation evidence note provided."

    replacements = {
        "Die hybride Fair-Value-Sicht signalisiert Unterbewertung.": (
            "Possible valuation discount based on current inputs; "
            "heuristic fair-value evidence only."
        ),
        "Unterbewertung": "possible valuation discount based on current inputs",
        "hybride Fair-Value-Sicht": "heuristic fair-value view",
        "hybriden Fair-Value-Spanne": "heuristic fair-value range",
        "geschaetzten Fair Value": "heuristic fair-value estimate based on available inputs",
        "Fair Value bleibt konservativ angesetzt": (
            "heuristic fair-value estimate remains conservative because inputs are missing"
        ),
    }
    for risky, safe in replacements.items():
        text = text.replace(risky, safe)

    return f"{DISPLAY_WORDING['valuation_comment']}: {text}"


def fair_value_estimate_label() -> str:
    return DISPLAY_WORDING["fair_value_estimate"]


def margin_of_safety_label() -> str:
    return DISPLAY_WORDING["margin_of_safety_pct"]


def margin_of_safety_evidence(value: Any) -> str:
    try:
        numeric = float(value)
        formatted = f"{numeric:.1f}%"
    except (TypeError, ValueError):
        formatted = "UNKNOWN"
    return f"{margin_of_safety_label()}: {formatted}"


def includes_degraded_state(text: str) -> bool:
    upper = (text or "").upper()
    return any(term in upper for term in DEGRADED_STATE_TERMS)
