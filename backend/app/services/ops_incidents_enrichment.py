from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.schemas_ops_incidents import SupplierHealthBadgeOut


SUPPLIER_INCIDENT_TYPES = {"supplier_partial_failure", "supplier_all_failed"}


def extract_supplier_code_from_incident(incident: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """Best-effort extraction of supplier_code from an incident document.

    Precedence:
    1) incident.meta.failed_suppliers[0].supplier_code
    2) incident.meta.supplier_code
    3) None with note
    """

    notes: List[str] = []

    inc_type = incident.get("type")
    if inc_type not in SUPPLIER_INCIDENT_TYPES:
        return None, notes

    meta = incident.get("meta") or {}
    supplier_code: Optional[str] = None

    failed_suppliers = meta.get("failed_suppliers") or []
    if isinstance(failed_suppliers, list) and failed_suppliers:
        first = failed_suppliers[0] or {}
        supplier_code = first.get("supplier_code")

    if not supplier_code and meta.get("supplier_code"):
        supplier_code = meta.get("supplier_code")

    if not supplier_code:
        notes.append("supplier_code_not_available")

    return supplier_code, notes


async def attach_supplier_health_badges(
    db,
    *,
    organization_id: str,
    incidents: List[Dict[str, Any]],
    include_supplier_health: bool,
) -> List[Dict[str, Any]]:
    """Attach SupplierHealthBadgeOut to each incident dict (fail-open).

    Mutates and returns the same list of incident dicts.
    """

    if not include_supplier_health or not incidents:
        return incidents

    try:
        # Extract supplier codes with notes
        supplier_codes: List[str] = []
        codes_by_index: Dict[int, Optional[str]] = {}
        notes_by_index: Dict[int, List[str]] = {}

        for idx, inc in enumerate(incidents):
            code, notes = extract_supplier_code_from_incident(inc)
            codes_by_index[idx] = code
            notes_by_index[idx] = notes
            if code:
                supplier_codes.append(code)

        if not supplier_codes:
            return incidents

        # Bulk fetch health snapshots
        flt: Dict[str, Any] = {
            "organization_id": organization_id,
            "window_sec": 900,
            "supplier_code": {"$in": list(set(supplier_codes))},
        }
        cursor = db.supplier_health.find(flt, {"_id": 0})
        health_docs: Dict[str, Dict[str, Any]] = {}
        async for doc in cursor:
            code = doc.get("supplier_code")
            if code:
                health_docs[code] = doc

        # Attach badges
        for idx, inc in enumerate(incidents):
            code = codes_by_index.get(idx)
            notes = list(notes_by_index.get(idx) or [])

            if not code:
                if notes:
                    badge = SupplierHealthBadgeOut(
                        supplier_code="unknown",
                        window_sec=900,
                        success_rate=None,
                        error_rate=None,
                        avg_latency_ms=None,
                        p95_latency_ms=None,
                        last_error_codes=[],
                        circuit_state=None,
                        circuit_until=None,
                        reason_code=None,
                        consecutive_failures=None,
                        updated_at=None,
                        notes=notes,
                    )
                    inc["supplier_health"] = badge
                continue

            doc = health_docs.get(code)
            if not doc:
                notes.append("health_not_found")
                badge = SupplierHealthBadgeOut(
                    supplier_code=code,
                    window_sec=900,
                    success_rate=None,
                    error_rate=None,
                    avg_latency_ms=None,
                    p95_latency_ms=None,
                    last_error_codes=[],
                    circuit_state=None,
                    circuit_until=None,
                    reason_code=None,
                    consecutive_failures=None,
                    updated_at=None,
                    notes=notes,
                )
                inc["supplier_health"] = badge
                continue

            metrics = doc.get("metrics") or {}
            circuit = doc.get("circuit") or {}

            updated_at = doc.get("updated_at")
            updated_at_iso: Optional[str] = None
            if updated_at is not None:
                try:
                    updated_at_iso = updated_at.isoformat()
                except AttributeError:
                    # if stored as str already
                    updated_at_iso = str(updated_at)

            circuit_until = circuit.get("until")
            circuit_until_iso: Optional[str] = None
            if circuit_until is not None:
                try:
                    circuit_until_iso = circuit_until.isoformat()
                except AttributeError:
                    circuit_until_iso = str(circuit_until)

            badge = SupplierHealthBadgeOut(
                supplier_code=code,
                window_sec=doc.get("window_sec", 900),
                success_rate=metrics.get("success_rate"),
                error_rate=metrics.get("error_rate"),
                avg_latency_ms=metrics.get("avg_latency_ms"),
                p95_latency_ms=metrics.get("p95_latency_ms"),
                last_error_codes=metrics.get("last_error_codes") or [],
                circuit_state=circuit.get("state"),
                circuit_until=circuit_until_iso,
                reason_code=circuit.get("reason_code"),
                consecutive_failures=circuit.get("consecutive_failures"),
                updated_at=updated_at_iso,
                notes=notes,
            )
            inc["supplier_health"] = badge

        return incidents
    except Exception:
        # Fail-open: never break ops incidents listing due to enrichment
        return incidents
