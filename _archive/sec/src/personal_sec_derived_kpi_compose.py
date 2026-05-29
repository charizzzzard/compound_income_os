from __future__ import annotations

import argparse
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from src.common import read_csv_rows, resolve_repo_path, write_csv_rows

DEFAULT_APPROVAL_APPLIED = "data/raw/private/fundamentals/personal_sec_companyfacts_concept_approval_applied.csv"
DEFAULT_UNLOCK_MATRIX = "data/raw/private/fundamentals/personal_sec_companyfacts_concept_recipe_unlock_matrix_after_human_decisions.csv"
DEFAULT_CONCEPT_CANDIDATES = "data/processed/personal_sec_kpi_extraction_concept_candidates.csv"
DEFAULT_GAP_MATRIX = "data/processed/personal_sec_kpi_extraction_gap_matrix.csv"
DEFAULT_OUTPUT_DIR = "data/processed"
DEFAULT_REPORT_DIR = "reports/2026-04-27"
DEFAULT_FACT_SOURCE_AUDIT = "data/processed/personal_sec_derived_kpi_fact_source_audit.csv"

PROPOSALS_OUTPUT = "personal_sec_derived_kpi_proposals.csv"
PROPOSAL_INPUTS_OUTPUT = "personal_sec_derived_kpi_proposal_inputs.csv"
REJECTIONS_OUTPUT = "personal_sec_derived_kpi_rejections.csv"
SUMMARY_OUTPUT = "personal_sec_derived_kpi_summary.csv"
REPORT_OUTPUT = "personal_sec_derived_kpi_compose_report.md"

PROPOSAL_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "derived_value",
    "derived_value_unit",
    "derived_value_format",
    "fiscal_year_start",
    "fiscal_year_end",
    "periods_used",
    "source_sec_concepts",
    "source_units",
    "source_forms",
    "source_filed_dates",
    "calculation_method",
    "calculation_inputs_summary",
    "approval_source_status",
    "evidence_status",
    "proposal_status",
    "rejection_reason",
    "review_required",
    "no_imputation_confirmed",
    "source_artifact",
]

PROPOSAL_INPUT_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "formula_role",
    "sec_taxonomy",
    "sec_concept",
    "unit",
    "fiscal_year",
    "fiscal_period",
    "form",
    "filed_date",
    "frame",
    "value",
    "selected_for_calculation",
    "selection_reason",
    "source_artifact",
]

REJECTION_FIELDS = [
    "holding_name",
    "ticker",
    "isin",
    "kpi_field",
    "formula_recipe",
    "rejection_reason",
    "missing_or_invalid_roles",
    "invalid_periods",
    "invalid_units",
    "invalid_values",
    "next_action",
    "review_required",
]

SUMMARY_FIELDS = [
    "unlocked_recipes_total",
    "proposals_created",
    "proposals_ready_for_evidence_compose",
    "proposals_rejected",
    "proposals_review_required",
    "holdings_count",
    "compose_fact_source_artifact",
    "fact_source_mode",
    "matching_numeric_fact_count",
    "annual_fact_count",
    "annual_10k_fact_count",
    "no_network_confirmed",
    "no_score_change_confirmed",
    "no_master_mutation_confirmed",
    "no_imputation_confirmed",
]

REQUIRED_ROLES = {
    "gross_margin": ("gross_profit", "revenue"),
    "operating_margin": ("operating_income", "revenue"),
    "revenue_cagr_5y": ("revenue_series",),
    "eps_cagr_5y": ("eps_series",),
    "share_count_cagr_5y": ("share_count_series",),
}

FORMULA_RECIPES = {
    "gross_margin": "GROSS_MARGIN",
    "operating_margin": "OPERATING_MARGIN",
    "revenue_cagr_5y": "REVENUE_CAGR_5Y",
    "eps_cagr_5y": "EPS_CAGR_5Y",
    "share_count_cagr_5y": "SHARE_COUNT_CAGR_5Y",
}


@dataclass(frozen=True)
class Fact:
    row: dict[str, str]
    value: float

    @property
    def year(self) -> int:
        return fact_period_year(self.row)

    @property
    def unit(self) -> str:
        return self.row.get("unit", "")

    @property
    def concept(self) -> str:
        return self.row.get("sec_concept", "")


@dataclass(frozen=True)
class ComposeResult:
    proposals_path: Path
    proposal_inputs_path: Path
    rejections_path: Path
    summary_path: Path
    report_path: Path
    summary: dict[str, str]


@dataclass(frozen=True)
class FactSource:
    path: Path
    rows: list[dict[str, str]]
    mode: str


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def to_float_or_none(value: Any) -> float | None:
    text = clean_text(value).replace(",", "")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def bool_text(value: Any) -> bool:
    return clean_text(value).lower() in {"1", "true", "yes", "y"}


def fact_value(row: dict[str, str]) -> float | None:
    for key in ("value", "reported_value", "fact_value", "numeric_value", "val"):
        if key in row:
            parsed = to_float_or_none(row.get(key))
            if parsed is not None:
                return parsed
    if not bool_text(row.get("value_present")) or not bool_text(row.get("value_is_numeric")):
        return None
    return None


def first_present(row: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        if key in row and clean_text(row.get(key)):
            return clean_text(row.get(key))
    return ""


def fiscal_year_value(row: dict[str, str]) -> str:
    year = first_present(row, ("fiscal_year", "fy", "fiscalYear", "end_year"))
    if year:
        return year
    frame = first_present(row, ("frame",)).upper()
    if frame.startswith("CY") and len(frame) >= 6 and frame[2:6].isdigit():
        return frame[2:6]
    return ""


def fact_period_year(row: dict[str, str]) -> int:
    frame = first_present(row, ("frame",)).upper()
    if frame.startswith("CY") and len(frame) >= 6 and frame[2:6].isdigit():
        return int(frame[2:6])
    period_end = first_present(row, ("period_end", "end"))
    if len(period_end) >= 4 and period_end[:4].isdigit():
        return int(period_end[:4])
    return int(float(row.get("fiscal_year", "0") or 0))


def normalize_fact_row(row: dict[str, str], source_artifact: str) -> dict[str, str]:
    return {
        "holding_name": first_present(row, ("holding_name", "company_name", "snapshot_company_name")),
        "ticker": first_present(row, ("ticker", "holding_ticker")),
        "isin": first_present(row, ("isin", "holding_isin")),
        "kpi_field": first_present(row, ("kpi_field", "kpi_name", "target_field")),
        "sec_taxonomy": first_present(row, ("sec_taxonomy", "taxonomy")),
        "sec_concept": first_present(row, ("sec_concept", "concept", "candidate_sec_concept")),
        "unit": first_present(row, ("unit", "reported_unit", "candidate_unit")),
        "fiscal_year": fiscal_year_value(row),
        "fiscal_period": first_present(row, ("fiscal_period", "fp", "fiscalPeriod")),
        "form": first_present(row, ("form", "filing_form")),
        "filed_date": first_present(row, ("filed_date", "filing_date", "source_as_of_date")),
        "frame": first_present(row, ("frame",)),
        "period_end": first_present(row, ("period_end", "end")),
        "value": first_present(row, ("value", "reported_value", "fact_value", "numeric_value", "val")),
        "value_present": first_present(row, ("value_present",)),
        "value_is_numeric": first_present(row, ("value_is_numeric",)),
        "source_artifact": first_present(row, ("source_artifact",)) or source_artifact,
    }


def is_annual_fact(row: dict[str, str]) -> bool:
    period = clean_text(row.get("fiscal_period")).upper()
    form = clean_text(row.get("form")).upper()
    return period == "FY" and ("10-K" in form)


def latest_date_key(value: str) -> str:
    return clean_text(value)


def artifact_label(path: Path) -> str:
    try:
        return path.relative_to(resolve_repo_path(".")).as_posix()
    except ValueError:
        return path.as_posix()


def approved_concepts(approval_rows: list[dict[str, str]]) -> dict[tuple[str, str, str, str], set[str]]:
    concepts: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for row in approval_rows:
        if clean_text(row.get("approval_status")).upper() != "APPROVED":
            continue
        key = (
            clean_text(row.get("holding_name")),
            clean_text(row.get("isin")),
            clean_text(row.get("kpi_field")),
            clean_text(row.get("formula_role")),
        )
        concepts[key].add(clean_text(row.get("candidate_sec_concept")))
    return concepts


def unlocked_recipe_rows(unlock_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in unlock_rows
        if clean_text(row.get("fully_approved_after_human_decisions")).lower() == "true"
        and clean_text(row.get("kpi_field")) in REQUIRED_ROLES
    ]


def role_concept_for(
    concepts: dict[tuple[str, str, str, str], set[str]],
    recipe: dict[str, str],
    role: str,
) -> tuple[str | None, str]:
    key = (clean_text(recipe.get("holding_name")), clean_text(recipe.get("isin")), clean_text(recipe.get("kpi_field")), role)
    selected = sorted(concept for concept in concepts.get(key, set()) if concept)
    if not selected:
        return None, "MISSING_APPROVED_CONCEPT"
    if len(selected) > 1:
        return None, "MULTIPLE_APPROVED_CONCEPTS"
    return selected[0], ""


def candidate_facts(
    candidate_rows: list[dict[str, str]],
    *,
    holding_name: str,
    isin: str,
    kpi_field: str,
    concept: str,
) -> list[Fact]:
    facts: list[Fact] = []
    for row in candidate_rows:
        if clean_text(row.get("holding_name")) != holding_name and clean_text(row.get("isin")) != isin:
            continue
        if clean_text(row.get("isin")) != isin:
            continue
        row_kpi = clean_text(row.get("kpi_field"))
        if row_kpi and row_kpi != kpi_field:
            continue
        if clean_text(row.get("sec_concept")) != concept:
            continue
        value = fact_value(row)
        if value is None:
            continue
        facts.append(Fact(row=row, value=value))
    return facts


def dedupe_annual_facts(facts: list[Fact]) -> tuple[list[Fact], str]:
    annual = [fact for fact in facts if is_annual_fact(fact.row)]
    if not annual:
        return [], "NO_ANNUAL_10K_FACTS"
    by_year: dict[int, list[Fact]] = defaultdict(list)
    for fact in annual:
        try:
            by_year[fact.year].append(fact)
        except ValueError:
            return [], "INVALID_FISCAL_YEAR"
    selected: list[Fact] = []
    for year in sorted(by_year):
        rows = sorted(by_year[year], key=lambda fact: latest_date_key(fact.row.get("filed_date", "")), reverse=True)
        latest_date = latest_date_key(rows[0].row.get("filed_date", ""))
        latest_rows = [fact for fact in rows if latest_date_key(fact.row.get("filed_date", "")) == latest_date]
        values = {fact.value for fact in latest_rows}
        if len(values) > 1:
            return [], "CONFLICTING_FACT_VALUES_AFTER_DEDUPE"
        selected.append(latest_rows[0])
    return selected, ""


def units_compatible(facts: Iterable[Fact]) -> bool:
    units = {fact.unit for fact in facts if fact.unit}
    return len(units) <= 1


def input_row(recipe: dict[str, str], role: str, fact: Fact, reason: str) -> dict[str, str]:
    row = fact.row
    return {
        "holding_name": clean_text(recipe.get("holding_name")),
        "ticker": clean_text(recipe.get("ticker")),
        "isin": clean_text(recipe.get("isin")),
        "kpi_field": clean_text(recipe.get("kpi_field")),
        "formula_recipe": clean_text(recipe.get("formula_recipe")) or FORMULA_RECIPES.get(clean_text(recipe.get("kpi_field")), ""),
        "formula_role": role,
        "sec_taxonomy": clean_text(row.get("sec_taxonomy")),
        "sec_concept": clean_text(row.get("sec_concept")),
        "unit": clean_text(row.get("unit")),
        "fiscal_year": clean_text(row.get("fiscal_year")),
        "fiscal_period": clean_text(row.get("fiscal_period")),
        "form": clean_text(row.get("form")),
        "filed_date": clean_text(row.get("filed_date")),
        "frame": clean_text(row.get("frame")),
        "value": str(fact.value),
        "selected_for_calculation": "True",
        "selection_reason": reason,
        "source_artifact": clean_text(row.get("source_artifact")),
    }


def proposal_row(
    recipe: dict[str, str],
    *,
    value: float,
    unit: str,
    fmt: str,
    start_year: int,
    end_year: int,
    facts: list[Fact],
    method: str,
    inputs_summary: str,
) -> dict[str, str]:
    return {
        "holding_name": clean_text(recipe.get("holding_name")),
        "ticker": clean_text(recipe.get("ticker")),
        "isin": clean_text(recipe.get("isin")),
        "kpi_field": clean_text(recipe.get("kpi_field")),
        "formula_recipe": clean_text(recipe.get("formula_recipe")) or FORMULA_RECIPES.get(clean_text(recipe.get("kpi_field")), ""),
        "derived_value": f"{value:.10g}",
        "derived_value_unit": unit,
        "derived_value_format": fmt,
        "fiscal_year_start": str(start_year),
        "fiscal_year_end": str(end_year),
        "periods_used": ";".join(str(fact.year) for fact in facts),
        "source_sec_concepts": ";".join(sorted({fact.concept for fact in facts})),
        "source_units": ";".join(sorted({fact.unit for fact in facts if fact.unit})),
        "source_forms": ";".join(sorted({clean_text(fact.row.get("form")) for fact in facts if clean_text(fact.row.get("form"))})),
        "source_filed_dates": ";".join(sorted({clean_text(fact.row.get("filed_date")) for fact in facts if clean_text(fact.row.get("filed_date"))})),
        "calculation_method": method,
        "calculation_inputs_summary": inputs_summary,
        "approval_source_status": "APPROVED_COMPANYFACTS_CONCEPTS_ONLY",
        "evidence_status": "PROPOSAL_ONLY_NOT_APPLIED",
        "proposal_status": "READY_FOR_EVIDENCE_COMPOSE",
        "rejection_reason": "",
        "review_required": "False",
        "no_imputation_confirmed": "True",
        "source_artifact": ";".join(sorted({clean_text(fact.row.get("source_artifact")) for fact in facts if clean_text(fact.row.get("source_artifact"))})),
    }


def rejection_row(
    recipe: dict[str, str],
    reason: str,
    *,
    invalid_roles: str = "",
    invalid_periods: str = "",
    invalid_units: str = "",
    invalid_values: str = "",
) -> dict[str, str]:
    return {
        "holding_name": clean_text(recipe.get("holding_name")),
        "ticker": clean_text(recipe.get("ticker")),
        "isin": clean_text(recipe.get("isin")),
        "kpi_field": clean_text(recipe.get("kpi_field")),
        "formula_recipe": clean_text(recipe.get("formula_recipe")) or FORMULA_RECIPES.get(clean_text(recipe.get("kpi_field")), ""),
        "rejection_reason": reason,
        "missing_or_invalid_roles": invalid_roles,
        "invalid_periods": invalid_periods,
        "invalid_units": invalid_units,
        "invalid_values": invalid_values,
        "next_action": "SEC_DERIVED_KPI_CALCULATION_GAP_REVIEW",
        "review_required": "True",
    }


def compose_margin(
    recipe: dict[str, str],
    candidate_rows: list[dict[str, str]],
    concepts: dict[tuple[str, str, str, str], set[str]],
    numerator_role: str,
) -> tuple[dict[str, str] | None, list[dict[str, str]], dict[str, str] | None]:
    kpi = clean_text(recipe.get("kpi_field"))
    holding = clean_text(recipe.get("holding_name"))
    isin = clean_text(recipe.get("isin"))
    numerator_concept, numerator_error = role_concept_for(concepts, recipe, numerator_role)
    revenue_concept, revenue_error = role_concept_for(concepts, recipe, "revenue")
    if numerator_error or revenue_error:
        return None, [], rejection_row(recipe, "MISSING_OR_AMBIGUOUS_APPROVED_ROLE", invalid_roles=";".join(x for x in [numerator_error, revenue_error] if x))
    numerator_facts, numerator_dedupe_error = dedupe_annual_facts(candidate_facts(candidate_rows, holding_name=holding, isin=isin, kpi_field=kpi, concept=numerator_concept or ""))
    revenue_facts, revenue_dedupe_error = dedupe_annual_facts(candidate_facts(candidate_rows, holding_name=holding, isin=isin, kpi_field=kpi, concept=revenue_concept or ""))
    if numerator_dedupe_error or revenue_dedupe_error:
        return None, [], rejection_row(recipe, "INVALID_OR_MISSING_ANNUAL_FACTS", invalid_periods=";".join(x for x in [numerator_dedupe_error, revenue_dedupe_error] if x))
    years = sorted({fact.year for fact in numerator_facts}.intersection({fact.year for fact in revenue_facts}))
    if not years:
        return None, [], rejection_row(recipe, "NO_COMMON_FISCAL_YEAR", invalid_periods="no shared annual fiscal year")
    year = max(years)
    numerator_fact = next(fact for fact in numerator_facts if fact.year == year)
    revenue_fact = next(fact for fact in revenue_facts if fact.year == year)
    if numerator_fact.unit != revenue_fact.unit:
        return None, [], rejection_row(recipe, "UNIT_CONFLICT", invalid_units=f"{numerator_fact.unit};{revenue_fact.unit}")
    if revenue_fact.value <= 0:
        return None, [], rejection_row(recipe, "NON_POSITIVE_DENOMINATOR", invalid_values="revenue<=0")
    facts = [numerator_fact, revenue_fact]
    value = numerator_fact.value / revenue_fact.value
    inputs = [input_row(recipe, numerator_role, numerator_fact, "latest common annual numerator"), input_row(recipe, "revenue", revenue_fact, "latest common annual denominator")]
    method = "gross_profit / revenue" if kpi == "gross_margin" else "operating_income / revenue"
    proposal = proposal_row(recipe, value=value, unit="ratio", fmt="decimal_ratio", start_year=year, end_year=year, facts=facts, method=method, inputs_summary=f"{numerator_role}={numerator_fact.value}; revenue={revenue_fact.value}")
    return proposal, inputs, None


def compose_cagr(
    recipe: dict[str, str],
    candidate_rows: list[dict[str, str]],
    concepts: dict[tuple[str, str, str, str], set[str]],
    role: str,
) -> tuple[dict[str, str] | None, list[dict[str, str]], dict[str, str] | None]:
    kpi = clean_text(recipe.get("kpi_field"))
    holding = clean_text(recipe.get("holding_name"))
    isin = clean_text(recipe.get("isin"))
    concept, concept_error = role_concept_for(concepts, recipe, role)
    if concept_error:
        return None, [], rejection_row(recipe, "MISSING_OR_AMBIGUOUS_APPROVED_ROLE", invalid_roles=concept_error)
    facts, dedupe_error = dedupe_annual_facts(candidate_facts(candidate_rows, holding_name=holding, isin=isin, kpi_field=kpi, concept=concept or ""))
    if dedupe_error:
        return None, [], rejection_row(recipe, "INVALID_OR_MISSING_ANNUAL_FACTS", invalid_periods=dedupe_error)
    if not units_compatible(facts):
        return None, [], rejection_row(recipe, "UNIT_CONFLICT", invalid_units="mixed units")
    if len({fact.concept for fact in facts}) > 1:
        return None, [], rejection_row(recipe, "CONCEPT_MIXING_NOT_ALLOWED", invalid_roles="mixed concepts")
    by_year = {fact.year: fact for fact in facts}
    years = sorted(by_year)
    if len(years) < 2:
        return None, [], rejection_row(recipe, "PERIOD_WINDOW_INSUFFICIENT", invalid_periods="fewer than two annual facts")
    latest_year = max(years)
    preferred_start = latest_year - 5
    if preferred_start in by_year:
        start_year = preferred_start
    else:
        eligible = [year for year in years if latest_year - year >= 4]
        if not eligible:
            return None, [], rejection_row(recipe, "PERIOD_WINDOW_INSUFFICIENT", invalid_periods="years_between<4")
        start_year = min(eligible)
    earliest = by_year[start_year]
    latest = by_year[latest_year]
    years_between = latest_year - start_year
    if earliest.value <= 0 or latest.value <= 0:
        reason = "EPS_CAGR_NON_POSITIVE_ENDPOINT" if kpi == "eps_cagr_5y" else "CAGR_NON_POSITIVE_ENDPOINT"
        return None, [], rejection_row(recipe, reason, invalid_values=f"start={earliest.value};latest={latest.value}")
    value = (latest.value / earliest.value) ** (1 / years_between) - 1
    selected_facts = [earliest, latest]
    inputs = [
        input_row(recipe, role, earliest, "earliest annual CAGR endpoint"),
        input_row(recipe, role, latest, "latest annual CAGR endpoint"),
    ]
    method = f"({role}_latest / {role}_earliest) ** (1 / years_between) - 1"
    proposal = proposal_row(recipe, value=value, unit="ratio", fmt="decimal_cagr", start_year=start_year, end_year=latest_year, facts=selected_facts, method=method, inputs_summary=f"start={earliest.value}; latest={latest.value}; years_between={years_between}")
    return proposal, inputs, None


def compose_recipe(
    recipe: dict[str, str],
    candidate_rows: list[dict[str, str]],
    concepts: dict[tuple[str, str, str, str], set[str]],
) -> tuple[dict[str, str] | None, list[dict[str, str]], dict[str, str] | None]:
    kpi = clean_text(recipe.get("kpi_field"))
    if kpi == "gross_margin":
        return compose_margin(recipe, candidate_rows, concepts, "gross_profit")
    if kpi == "operating_margin":
        return compose_margin(recipe, candidate_rows, concepts, "operating_income")
    if kpi == "revenue_cagr_5y":
        return compose_cagr(recipe, candidate_rows, concepts, "revenue_series")
    if kpi == "eps_cagr_5y":
        return compose_cagr(recipe, candidate_rows, concepts, "eps_series")
    if kpi == "share_count_cagr_5y":
        return compose_cagr(recipe, candidate_rows, concepts, "share_count_series")
    return None, [], rejection_row(recipe, "UNSUPPORTED_KPI_FIELD", invalid_roles=kpi)


def fact_source_counts(
    fact_rows: list[dict[str, str]],
    recipes: list[dict[str, str]],
    concepts: dict[tuple[str, str, str, str], set[str]],
) -> dict[str, int]:
    matching_numeric = 0
    annual = 0
    annual_10k = 0
    for recipe in recipes:
        for role in REQUIRED_ROLES.get(clean_text(recipe.get("kpi_field")), ()):
            concept, error = role_concept_for(concepts, recipe, role)
            if error or not concept:
                continue
            facts = candidate_facts(
                fact_rows,
                holding_name=clean_text(recipe.get("holding_name")),
                isin=clean_text(recipe.get("isin")),
                kpi_field=clean_text(recipe.get("kpi_field")),
                concept=concept,
            )
            matching_numeric += len(facts)
            annual += sum(1 for fact in facts if clean_text(fact.row.get("fiscal_period")).upper() == "FY" or clean_text(fact.row.get("frame")).upper().startswith("CY"))
            annual_10k += sum(1 for fact in facts if is_annual_fact(fact.row))
    return {
        "matching_numeric_fact_count": matching_numeric,
        "annual_fact_count": annual,
        "annual_10k_fact_count": annual_10k,
    }


def recommended_sec_facts_from_audit() -> Path | None:
    audit_path = resolve_repo_path(DEFAULT_FACT_SOURCE_AUDIT)
    if not audit_path.exists():
        return None
    rows = read_csv_rows(audit_path)
    recommended = sorted(
        {
            clean_text(row.get("recommended_source_artifact"))
            for row in rows
            if clean_text(row.get("source_usable_for_compose")).lower() == "true"
            and clean_text(row.get("recommended_source_artifact"))
            and "data/raw/private" not in clean_text(row.get("recommended_source_artifact")).replace("\\", "/").lower()
        }
    )
    if not recommended:
        return None
    return resolve_repo_path(recommended[0])


def load_fact_source(sec_facts: str | Path | None, concept_candidates: str | Path) -> FactSource:
    if sec_facts:
        path = resolve_repo_path(sec_facts)
        if not path.exists():
            raise RuntimeError("MISSING_SEC_FACT_INPUTS")
        raw_rows = read_csv_rows(path)
        return FactSource(path=path, rows=[normalize_fact_row(row, artifact_label(path)) for row in raw_rows], mode="NORMALIZED_FACTS")
    candidate_path = resolve_repo_path(concept_candidates)
    default_candidate_path = resolve_repo_path(DEFAULT_CONCEPT_CANDIDATES)
    recommended = recommended_sec_facts_from_audit() if candidate_path == default_candidate_path else None
    if recommended and recommended.exists():
        raw_rows = read_csv_rows(recommended)
        return FactSource(path=recommended, rows=[normalize_fact_row(row, artifact_label(recommended)) for row in raw_rows], mode="NORMALIZED_FACTS")
    if not candidate_path.exists():
        raise RuntimeError("MISSING_SEC_FACT_INPUTS")
    raw_rows = read_csv_rows(candidate_path)
    mode = "CANDIDATE_METADATA_ONLY"
    return FactSource(path=candidate_path, rows=[normalize_fact_row(row, artifact_label(candidate_path)) for row in raw_rows], mode=mode)


def build_report(summary: dict[str, str], proposals: list[dict[str, str]], rejections: list[dict[str, str]]) -> str:
    by_holding: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in proposals:
        by_holding[row["holding_name"]].append(row)
    rejection_by_holding: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rejections:
        rejection_by_holding[row["holding_name"]].append(row)
    lines = [
        "# SEC Derived KPI Compose Report",
        "",
        "## Executive Summary",
        f"- unlocked_recipes_total: {summary['unlocked_recipes_total']}",
        f"- proposals_created: {summary['proposals_created']}",
        f"- proposals_ready_for_evidence_compose: {summary['proposals_ready_for_evidence_compose']}",
        f"- proposals_rejected: {summary['proposals_rejected']}",
        f"- proposals_review_required: {summary['proposals_review_required']}",
        "",
        "## Scope",
        "Approved SEC CompanyFacts concept roles were used to create proposal-only derived KPI artifacts. No evidence apply, master mutation, score change, network fetch, or imputation was performed.",
        "",
        "## Inputs Used",
        "- private approval-applied input: present, path omitted from public report",
        f"- compose_fact_source_artifact: `{summary.get('compose_fact_source_artifact', '')}`",
        f"- fact_source_mode: `{summary.get('fact_source_mode', '')}`",
        f"- matching_numeric_fact_count: `{summary.get('matching_numeric_fact_count', '0')}`",
        f"- annual_fact_count: `{summary.get('annual_fact_count', '0')}`",
        f"- annual_10k_fact_count: `{summary.get('annual_10k_fact_count', '0')}`",
        "- processed gap matrix",
        "- private recipe unlock matrix: present, path omitted from public report",
        "",
        "## KPI Proposals by Holding",
    ]
    for holding in sorted(set(by_holding) | set(rejection_by_holding)):
        lines.append(f"### {holding}")
        for row in by_holding.get(holding, []):
            lines.append(f"- {row['kpi_field']}: {row['derived_value']} ({row['proposal_status']})")
        for row in rejection_by_holding.get(holding, []):
            lines.append(f"- {row['kpi_field']}: rejected/review required - {row['rejection_reason']}")
    lines.extend(
        [
            "",
            "## Rejections / Review Required",
        ]
    )
    if rejections:
        for row in rejections:
            lines.append(f"- {row['holding_name']} {row['kpi_field']}: {row['rejection_reason']}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Calculation Rules",
            "- gross_margin = gross_profit / revenue",
            "- operating_margin = operating_income / revenue",
            "- CAGR metrics require positive annual endpoints and at least four years between endpoints.",
            "- Annual facts prefer FY 10-K / 10-K/A candidates and dedupe same fiscal year by latest filed_date.",
            "",
            "## Guardrail Confirmation",
            "- no_network_confirmed=True",
            "- no_score_change_confirmed=True",
            "- no_master_mutation_confirmed=True",
            "- no_imputation_confirmed=True",
            "",
            "## Next Recommended Patch",
            "SEC DERIVED KPI EVIDENCE COMPOSE / REVIEWED PROPOSALS ONLY / NO SCORE CHANGES" if proposals else "SEC DERIVED KPI CALCULATION GAP REVIEW / PERIOD UNIT FACT SELECTION",
        ]
    )
    return "\n".join(lines) + "\n"


def run_personal_sec_derived_kpi_compose(
    *,
    approval_applied: str | Path = DEFAULT_APPROVAL_APPLIED,
    unlock_matrix: str | Path = DEFAULT_UNLOCK_MATRIX,
    concept_candidates: str | Path = DEFAULT_CONCEPT_CANDIDATES,
    sec_facts: str | Path | None = None,
    gap_matrix: str | Path = DEFAULT_GAP_MATRIX,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> ComposeResult:
    approval_path = resolve_repo_path(approval_applied)
    unlock_path = resolve_repo_path(unlock_matrix)
    gap_path = resolve_repo_path(gap_matrix)
    if not approval_path.exists():
        raise RuntimeError("MISSING_PRIVATE_APPROVAL_APPLIED")
    if not unlock_path.exists() or not gap_path.exists():
        raise RuntimeError("MISSING_SEC_FACT_INPUTS")

    approval_rows = read_csv_rows(approval_path)
    unlock_rows = read_csv_rows(unlock_path)
    fact_source = load_fact_source(sec_facts, concept_candidates)
    fact_rows = fact_source.rows
    _gap_rows = read_csv_rows(gap_path)
    if not fact_rows:
        raise RuntimeError("MISSING_SEC_FACT_INPUTS")

    concepts = approved_concepts(approval_rows)
    recipes = unlocked_recipe_rows(unlock_rows)
    source_counts = fact_source_counts(fact_rows, recipes, concepts)
    proposals: list[dict[str, str]] = []
    proposal_inputs: list[dict[str, str]] = []
    rejections: list[dict[str, str]] = []

    for recipe in recipes:
        proposal, inputs, rejection = compose_recipe(recipe, fact_rows, concepts)
        if proposal:
            proposals.append(proposal)
            proposal_inputs.extend(inputs)
        if rejection:
            rejections.append(rejection)

    output_root = resolve_repo_path(output_dir)
    report_root = resolve_repo_path(report_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)

    summary = {
        "unlocked_recipes_total": str(len(recipes)),
        "proposals_created": str(len(proposals)),
        "proposals_ready_for_evidence_compose": str(sum(1 for row in proposals if row["proposal_status"] == "READY_FOR_EVIDENCE_COMPOSE")),
        "proposals_rejected": str(len(rejections)),
        "proposals_review_required": str(len(rejections)),
        "holdings_count": str(len({row.get("holding_name", "") for row in recipes})),
        "compose_fact_source_artifact": artifact_label(fact_source.path),
        "fact_source_mode": fact_source.mode if any(source_counts.values()) or fact_source.mode != "CANDIDATE_METADATA_ONLY" else "CANDIDATE_METADATA_ONLY",
        "matching_numeric_fact_count": str(source_counts["matching_numeric_fact_count"]),
        "annual_fact_count": str(source_counts["annual_fact_count"]),
        "annual_10k_fact_count": str(source_counts["annual_10k_fact_count"]),
        "no_network_confirmed": "True",
        "no_score_change_confirmed": "True",
        "no_master_mutation_confirmed": "True",
        "no_imputation_confirmed": "True",
    }

    proposals_path = write_csv_rows(output_root / PROPOSALS_OUTPUT, PROPOSAL_FIELDS, proposals)
    proposal_inputs_path = write_csv_rows(output_root / PROPOSAL_INPUTS_OUTPUT, PROPOSAL_INPUT_FIELDS, proposal_inputs)
    rejections_path = write_csv_rows(output_root / REJECTIONS_OUTPUT, REJECTION_FIELDS, rejections)
    summary_path = write_csv_rows(output_root / SUMMARY_OUTPUT, SUMMARY_FIELDS, [summary])
    report_path = report_root / REPORT_OUTPUT
    report_path.write_text(build_report(summary, proposals, rejections), encoding="utf-8")

    return ComposeResult(
        proposals_path=proposals_path,
        proposal_inputs_path=proposal_inputs_path,
        rejections_path=rejections_path,
        summary_path=summary_path,
        report_path=report_path,
        summary=summary,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose SEC-derived KPI evidence proposals from approved CompanyFacts concepts.")
    parser.add_argument("--approval-applied", default=DEFAULT_APPROVAL_APPLIED)
    parser.add_argument("--unlock-matrix", default=DEFAULT_UNLOCK_MATRIX)
    parser.add_argument("--concept-candidates", default=DEFAULT_CONCEPT_CANDIDATES)
    parser.add_argument("--sec-facts", default=None)
    parser.add_argument("--gap-matrix", default=DEFAULT_GAP_MATRIX)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_personal_sec_derived_kpi_compose(
        approval_applied=args.approval_applied,
        unlock_matrix=args.unlock_matrix,
        concept_candidates=args.concept_candidates,
        sec_facts=args.sec_facts,
        gap_matrix=args.gap_matrix,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
    )
    print(f"proposals_path={result.proposals_path}")
    print(f"proposal_inputs_path={result.proposal_inputs_path}")
    print(f"rejections_path={result.rejections_path}")
    print(f"summary_path={result.summary_path}")
    print(f"report_path={result.report_path}")
    print(f"proposals_ready_for_evidence_compose={result.summary['proposals_ready_for_evidence_compose']}")


if __name__ == "__main__":
    main()
