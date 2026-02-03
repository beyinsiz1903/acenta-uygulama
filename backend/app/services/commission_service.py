from __future__ import annotations

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repositories.commission_rule_repository import CommissionRuleRepository


class CommissionService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._repo = CommissionRuleRepository(db)

    async def resolve_commission_rule(
        self,
        seller_tenant_id: str,
        buyer_tenant_id: Optional[str],
        product_id: Optional[str],
        tags: list[str],
    ) -> Optional[dict[str, Any]]:
        """Resolve the most specific active commission rule.

        Precedence:
        1) buyer-specific + product
        2) buyer-specific + tag
        3) buyer-specific + all
        4) default + product
        5) default + tag
        6) default + all
        Within same bucket, higher priority wins.
        """

        candidates = await self._repo.find_applicable_rules(
            seller_tenant_id=seller_tenant_id,
            buyer_tenant_id=buyer_tenant_id,
            product_id=product_id,
            tags=tags,
        )

        def score(rule: dict[str, Any]) -> tuple[int, int]:
            # bucket rank (lower is better), then priority (higher is better)
            buyer_match = 1 if rule.get("buyer_tenant_id") == buyer_tenant_id else 0
            scope_type = rule.get("scope_type")
            has_product = scope_type == "product" and product_id and rule.get("product_id") == product_id
            has_tag = scope_type == "tag" and rule.get("tag") in tags
            is_all = scope_type == "all"

            if buyer_match and has_product:
                bucket = 1
            elif buyer_match and has_tag:
                bucket = 2
            elif buyer_match and is_all:
                bucket = 3
            elif not buyer_match and has_product:
                bucket = 4
            elif not buyer_match and has_tag:
                bucket = 5
            else:
                bucket = 6

            priority = int(rule.get("priority") or 0)
            return (bucket, -priority)

        if not candidates:
            return None

        # Filter out rules that don't actually match scope
        filtered: list[dict[str, Any]] = []
        for r in candidates:
            scope_type = r.get("scope_type")
            if scope_type == "product" and (not product_id or r.get("product_id") != product_id):
                continue
            if scope_type == "tag" and (not tags or r.get("tag") not in tags):
                continue
            filtered.append(r)

        if not filtered:
            return None

        best = sorted(filtered, key=score)[0]
        return best

    def compute_commission(self, gross_amount: float, rule: dict[str, Any]) -> float:
        rule_type = rule.get("rule_type")
        value = float(rule.get("value") or 0.0)
        if rule_type == "percentage":
            return float(gross_amount) * (value / 100.0)
        if rule_type == "fixed":
            return value
        # Unknown type; treat as zero
        return 0.0

    def compute_net(self, gross_amount: float, commission_amount: float) -> float:
        return float(gross_amount) - float(commission_amount)
