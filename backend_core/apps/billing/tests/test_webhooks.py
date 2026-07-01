"""Stripe webhook skeleton: idempotency, signature verification, processing."""

import hashlib
import hmac
import json
import time

import pytest
from rest_framework.test import APIClient

from apps.billing.models import BillingWebhookEvent, Subscription
from apps.billing.webhooks import log_and_process_event

WEBHOOK_URL = "/api/v1/billing/webhooks/stripe/"


def _signed_header(secret, body: bytes):
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.mark.django_db
class TestWebhookIdempotency:
    def test_duplicate_event_not_reprocessed(self):
        payload = {
            "id": "evt_dup",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_x", "status": "active"}},
        }
        first, c1 = log_and_process_event(
            provider_event_id="evt_dup",
            event_type=payload["type"],
            payload=payload,
            signature_verified=True,
        )
        second, c2 = log_and_process_event(
            provider_event_id="evt_dup",
            event_type=payload["type"],
            payload=payload,
            signature_verified=True,
        )
        assert c1 is True
        assert c2 is False
        assert first.id == second.id
        assert BillingWebhookEvent.objects.filter(provider_event_id="evt_dup").count() == 1
        assert first.status == BillingWebhookEvent.Status.PROCESSED

    def test_subscription_synced_from_event(self, workspace, subscribe):
        sub = subscribe(workspace, "artist_starter")
        sub.provider = Subscription.Provider.STRIPE
        sub.provider_subscription_id = "sub_sync"
        sub.save(update_fields=["provider", "provider_subscription_id"])

        log_and_process_event(
            provider_event_id="evt_sync",
            event_type="customer.subscription.updated",
            payload={"data": {"object": {"id": "sub_sync", "status": "past_due"}}},
            signature_verified=True,
        )
        sub.refresh_from_db()
        assert sub.status == Subscription.Status.PAST_DUE


@pytest.mark.django_db
class TestWebhookAPI:
    def test_accepts_without_secret_and_flags_unverified(self, settings):
        settings.STRIPE_WEBHOOK_SECRET = ""
        body = json.dumps(
            {"id": "evt_api_1", "type": "invoice.payment_succeeded", "data": {"object": {}}}
        )
        resp = APIClient().post(WEBHOOK_URL, data=body, content_type="application/json")
        assert resp.status_code == 200
        assert resp.data["received"] is True
        assert resp.data["duplicate"] is False
        assert resp.data["signature_verified"] is False

    def test_duplicate_via_api(self, settings):
        settings.STRIPE_WEBHOOK_SECRET = ""
        body = json.dumps(
            {"id": "evt_api_dup", "type": "invoice.payment_failed", "data": {"object": {}}}
        )
        client = APIClient()
        client.post(WEBHOOK_URL, data=body, content_type="application/json")
        resp = client.post(WEBHOOK_URL, data=body, content_type="application/json")
        assert resp.status_code == 200
        assert resp.data["duplicate"] is True
        assert BillingWebhookEvent.objects.filter(provider_event_id="evt_api_dup").count() == 1

    def test_rejects_invalid_signature(self, settings):
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        body = json.dumps(
            {"id": "evt_bad_sig", "type": "invoice.payment_succeeded", "data": {"object": {}}}
        )
        resp = APIClient().post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=deadbeef",
        )
        assert resp.status_code == 400
        assert not BillingWebhookEvent.objects.filter(provider_event_id="evt_bad_sig").exists()

    def test_accepts_valid_signature(self, settings):
        secret = "whsec_test"
        settings.STRIPE_WEBHOOK_SECRET = secret
        body = json.dumps(
            {"id": "evt_good_sig", "type": "invoice.payment_succeeded", "data": {"object": {}}}
        ).encode()
        header = _signed_header(secret, body)
        resp = APIClient().post(
            WEBHOOK_URL,
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        assert resp.status_code == 200
        assert resp.data["signature_verified"] is True
        assert BillingWebhookEvent.objects.filter(provider_event_id="evt_good_sig").exists()
