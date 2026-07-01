"""Credit ledger: grant, reserve, consume, release, refund and idempotency."""

from decimal import Decimal

import pytest

from apps.billing.exceptions import InsufficientCredits
from apps.billing.models import CreditLedgerEntry
from apps.billing.services import (
    consume_credits,
    get_credit_balance,
    grant_credits,
    refund_credits,
    release_reserved_credits,
    reserve_credits,
)
from apps.billing.tests.conftest import ws_header

CREDITS_URL = "/api/v1/billing/credits/"


@pytest.mark.django_db
class TestCreditLifecycle:
    def test_grant_increases_balance(self, workspace):
        grant_credits(workspace, 100, reason="welcome")
        assert get_credit_balance(workspace) == Decimal("100")

    def test_full_lifecycle(self, workspace):
        grant_credits(workspace, 100)
        assert get_credit_balance(workspace) == Decimal("100")

        reserve_credits(workspace, 30)
        assert get_credit_balance(workspace) == Decimal("70")

        # Cancel the reservation → credits returned.
        release_reserved_credits(workspace, 30)
        assert get_credit_balance(workspace) == Decimal("100")

        # Direct consume reduces the available balance.
        consume_credits(workspace, 20)
        assert get_credit_balance(workspace) == Decimal("80")

        # A technical failure can be refunded.
        refund_credits(workspace, 20, reason="render failed")
        assert get_credit_balance(workspace) == Decimal("100")

    def test_settle_reserved_does_not_double_charge(self, workspace):
        grant_credits(workspace, 50)
        reserve_credits(workspace, 50)
        assert get_credit_balance(workspace) == Decimal("0")
        # Finalizing the reservation must NOT deduct again.
        consume_credits(workspace, 50, settle_reserved=True)
        assert get_credit_balance(workspace) == Decimal("0")

    def test_balance_is_reconstructible_from_ledger(self, workspace):
        grant_credits(workspace, 100)
        consume_credits(workspace, 40)
        total = sum(
            e.amount for e in CreditLedgerEntry.objects.filter(workspace=workspace)
        )
        assert total == get_credit_balance(workspace) == Decimal("60")

    def test_reserve_without_balance_raises(self, workspace):
        with pytest.raises(InsufficientCredits):
            reserve_credits(workspace, 10)

    def test_consume_over_balance_raises(self, workspace):
        grant_credits(workspace, 5)
        with pytest.raises(InsufficientCredits):
            consume_credits(workspace, 10)


@pytest.mark.django_db
class TestCreditIdempotency:
    def test_grant_idempotent(self, workspace):
        grant_credits(workspace, 100, idempotency_key="grant-1")
        grant_credits(workspace, 100, idempotency_key="grant-1")
        assert get_credit_balance(workspace) == Decimal("100")
        assert CreditLedgerEntry.objects.filter(workspace=workspace).count() == 1

    def test_consume_idempotent_no_double_charge(self, workspace):
        grant_credits(workspace, 100)
        consume_credits(workspace, 30, idempotency_key="consume-1")
        consume_credits(workspace, 30, idempotency_key="consume-1")
        assert get_credit_balance(workspace) == Decimal("70")


@pytest.mark.django_db
class TestCreditBalanceAPI:
    def test_returns_balance_and_entries(self, client_for, owner, workspace):
        grant_credits(workspace, 100, reason="welcome")
        resp = client_for(owner).get(CREDITS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        assert float(resp.data["balance"]) == 100.0
        assert len(resp.data["recent_entries"]) == 1
