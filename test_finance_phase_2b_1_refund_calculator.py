"""
Finance OS Phase 2B.1–2B.2 Test
RefundCalculatorService: policy/manual/currency guards
"""

from datetime import datetime

from app.services.refund_calculator import RefundCalculatorService


def test_refund_calculator_policy_percent():
    svc = RefundCalculatorService(currency="EUR")
    booking = {
        "currency": "EUR",
        "amounts": {"sell": 1000.0},
        "policy_snapshot": {
            "cancellation_policy": {"type": "percent", "value": 20.0}
        },
    }
    now = datetime.utcnow()
    comp = svc.compute_refund(booking, now, mode="policy_first")

    assert comp.gross_sell == 1000.0
    assert comp.basis == "policy"
    assert comp.penalty == 200.0
    assert comp.refundable == 800.0
    assert comp.policy_ref["type"] == "percent"


def test_refund_calculator_policy_fixed():
    svc = RefundCalculatorService(currency="EUR")
    booking = {
        "currency": "EUR",
        "amounts": {"sell": 500.0},
        "policy_snapshot": {
            "cancellation_policy": {"type": "fixed", "fixed": 100.0}
        },
    }
    now = datetime.utcnow()
    comp = svc.compute_refund(booking, now, mode="policy_first")

    assert comp.gross_sell == 500.0
    assert comp.basis == "policy"
    assert comp.penalty == 100.0
    assert comp.refundable == 400.0


def test_refund_calculator_policy_nights_mvp():
    svc = RefundCalculatorService(currency="EUR")
    booking = {
        "currency": "EUR",
        "amounts": {"sell": 750.0},
        "policy_snapshot": {"cancellation_policy": {"type": "nights", "nights": 1}},
    }
    now = datetime.utcnow()
    comp = svc.compute_refund(booking, now, mode="policy_first")

    # MVP: nights>=1 -> full penalty
    assert comp.penalty == 750.0
    assert comp.refundable == 0.0
    assert comp.basis == "policy"


def test_refund_calculator_manual_when_no_policy():
    svc = RefundCalculatorService(currency="EUR")
    booking = {
        "currency": "EUR",
        "amounts": {"sell": 600.0},
        # no policy_snapshot
    }
    now = datetime.utcnow()
    comp = svc.compute_refund(booking, now, mode="policy_first", manual_requested_amount=350.0)

    assert comp.basis == "manual"
    assert comp.gross_sell == 600.0
    assert comp.refundable == 350.0
    assert comp.penalty == 250.0


def test_refund_calculator_currency_not_supported():
    svc = RefundCalculatorService(currency="EUR")
    booking = {"currency": "USD", "amounts": {"sell": 1000.0}}
    now = datetime.utcnow()

    try:
        svc.compute_refund(booking, now, mode="policy_first")
        assert False, "Expected currency_not_supported"
    except ValueError as e:
        assert "currency_not_supported" in str(e)

