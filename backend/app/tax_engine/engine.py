"""Deterministic tax-calculation engine.

The engine loads rule-packs per financial year and runs a series of
pure transformations over normalised income/deduction data to produce
a tax-liability breakdown and calculation-step audit trail.

Wired in Phase 2 — this stub module raises NotImplementedError.
"""

from __future__ import annotations

# Public API surface (implemented in Phase 2):
# - calculate_tax(user_id, financial_year) -> TaxResult
# - load_rule_pack(financial_year, jurisdiction) -> RulePack
# - validate_brackets(rule_pack) -> bool
