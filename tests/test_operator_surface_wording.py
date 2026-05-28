from __future__ import annotations

import unittest

from src.operator_surface_wording import (
    DISPLAY_WORDING,
    allocation_status_label,
    execution_mode_evidence,
    includes_degraded_state,
    margin_of_safety_evidence,
    operator_boundary_note,
    valuation_evidence_note,
)


class OperatorSurfaceWordingTests(unittest.TestCase):
    def test_internal_terms_have_safer_display_wording(self) -> None:
        self.assertEqual(
            DISPLAY_WORDING["BUYABLE"],
            "Reviewable candidate; operator review required; not an order instruction",
        )
        self.assertEqual(
            DISPLAY_WORDING["eligible_for_purchase"],
            "Passes local screening; operator review required",
        )
        self.assertIn("Heuristic fair-value estimate", DISPLAY_WORDING["fair_value_estimate"])
        self.assertIn("not certainty", DISPLAY_WORDING["margin_of_safety_pct"])
        self.assertIn("Possible valuation discount", DISPLAY_WORDING["Unterbewertung"])

    def test_allocation_and_execution_wording_preserves_operator_boundary(self) -> None:
        label = allocation_status_label("ELIGIBLE_NOT_FUNDED", "BUY")
        self.assertIn("Reviewable candidate", label)
        self.assertIn("not an order instruction", label)
        self.assertNotIn("Kaufbar", label)

        execution = execution_mode_evidence("SAVINGS_PLAN_NEW", "eligible_for_new_plan")
        self.assertIn("Execution-mode evidence", execution)
        self.assertIn("operator review required", execution)
        self.assertIn("no order is placed", execution)
        self.assertNotIn("Empfohlene Ausfuehrung", execution)

    def test_valuation_comment_rewrites_discount_and_preserves_degraded_state_visibility(self) -> None:
        note = valuation_evidence_note("Die hybride Fair-Value-Sicht signalisiert Unterbewertung. REVIEW")
        self.assertIn("Valuation evidence note", note)
        self.assertIn("Possible valuation discount based on current inputs", note)
        self.assertIn("heuristic fair-value evidence only", note)
        self.assertIn("REVIEW", note)
        self.assertNotIn("Unterbewertung", note)
        self.assertTrue(includes_degraded_state(note))

    def test_margin_and_boundary_wording_are_non_automating(self) -> None:
        margin = margin_of_safety_evidence("12.345")
        boundary = operator_boundary_note()
        self.assertIn("Indicative margin-of-safety field; not certainty", margin)
        self.assertIn("12.3%", margin)
        self.assertIn("Human Operator remains final authority", boundary)
        self.assertIn("not investment advice", boundary)
        self.assertIn("no order is placed", boundary)


if __name__ == "__main__":
    unittest.main()
