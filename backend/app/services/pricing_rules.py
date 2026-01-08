from __future__ import annotations

"""Pricing rules service (P1.2 MVP)

- Collection: pricing_rules
- Purpose: resolve markup_percent for a given quote item based on
  organization, agency, product and check-in date.

In this first iteration we keep the matching logic deliberately simple and
evaluate rules in Python (rule count is expected to be low).
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from app.errors import AppError


@dataclass
class PricingRule:
    id: Any
    organization_id: str
    status: str
    priority: int
    scope: dict
    validity: dict
    action: dict
    updated_at: Optional[datetime]


class PricingRulesService:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def resolve_markup_percent(
        self,
        organization_id: str,
        *,
        agency_id: Optional[str],
        product_id: Optional[str],
        product_type: Optional[str],
        check_in: date,
    ) -> float:
        """Resolve markup_percent for a quote item.

        Matching rules:
        - organization_id + status="active"
        - validity.from <= check_in < validity.to  (if validity present)
        - scope fields (agency_id, product_id, product_type) must match
          when present on the rule

        Selection:
        - Order by priority desc, then updated_at desc (or _id desc as tie-breaker)
        - First rule wins

        Fallback:
        - If no rule matches, return default 10.0 (demo behaviour)
        """

        # Fetch candidate rules for this org. We keep the Mongo filter coarse
        # and apply detailed matching in Python.
        cursor = self.db.pricing_rules.find(
            {
                "organization_id": organization_id,
                "status": "active",
            }
        )
        docs = await cursor.to_list(length=1000)
        if not docs:
            return 10.0

        # Normalise input
        item_date = check_in
        if isinstance(item_date, datetime):
            item_date = item_date.date()

        candidates: list[PricingRule] = []
        for doc in docs:
            rule = self._from_doc(doc)
            if self._matches(rule, agency_id=agency_id, product_id=product_id, product_type=product_type, check_in=item_date):
                candidates.append(rule)

        if not candidates:
            return 10.0

        selected = self._select_best(candidates)
        value = self._extract_markup_percent(selected)
        return value

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _from_doc(self, doc: dict) -> PricingRule:
        return PricingRule(
            id=doc.get("_id"),
            organization_id=str(doc.get("organization_id")),
            status=str(doc.get("status") or "inactive"),
            priority=int(doc.get("priority") or 0),
            scope=doc.get("scope") or {},
            validity=doc.get("validity") or {},
            action=doc.get("action") or {},
            updated_at=doc.get("updated_at"),
        )

    def _matches(
        self,
        rule: PricingRule,
        *,
        agency_id: Optional[str],
        product_id: Optional[str],
        product_type: Optional[str],
        check_in: date,
    ) -> bool:
        # Status guard (should already be filtered at query level)
        if rule.status != "active":
            return False

        # Validity window (optional on rule)
        validity = rule.validity or {}
        v_from = validity.get("from")
        v_to = validity.get("to")

        try:
            if v_from:
                # Stored as YYYY-MM-DD string
                d_from = date.fromisoformat(v_from)
                if check_in < d_from:
                    return False
            if v_to:
                d_to = date.fromisoformat(v_to)
                if check_in >= d_to:
                    return False
        except ValueError:
            # Malformed dates -> treat rule as invalid
            return False

        # Scope matching
        scope = rule.scope or {}

        rule_agency = scope.get("agency_id")
        if rule_agency and agency_id and str(rule_agency) != str(agency_id):
            return False

        rule_product = scope.get("product_id")
        if rule_product and product_id and str(rule_product) != str(product_id):
            return False

        rule_type = scope.get("product_type")
        if rule_type and product_type and str(rule_type).lower() != str(product_type).lower():
            return False

        return True

    def _select_best(self, rules: list[PricingRule]) -> PricingRule:
        # Highest priority wins; tie-breaker on updated_at (desc), then _id desc as fallback
        def sort_key(r: PricingRule):
            ts = r.updated_at or datetime.min
            return (-r.priority, -int(ts.timestamp()), str(r.id))

        return sorted(rules, key=sort_key)[0]

    def _extract_markup_percent(self, rule: PricingRule) -> float:
        action = rule.action or {}
        action_type = action.get("type")
        if action_type != "markup_percent":
            raise AppError(
                500,
                "pricing_rule_unsupported_action",
                f"Unsupported pricing rule action type: {action_type}",
                {"rule_id": str(rule.id)},
            )

        try:
            value = float(action.get("value"))
        except (TypeError, ValueError):
            raise AppError(
                500,
                "pricing_rule_invalid_value",
                "Pricing rule action.value must be a number",
                {"rule_id": str(rule.id)},
            )

        if not (0.0 <= value <= 100.0):
            raise AppError(
                500,
                "pricing_rule_invalid_value",
                "Pricing rule markup_percent must be between 0 and 100",
                {"rule_id": str(rule.id), "value": value},
            )

        return value
