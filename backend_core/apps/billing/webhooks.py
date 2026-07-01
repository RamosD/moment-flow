"""Stripe webhook skeleton: signature verification and idempotent processing.

This is intentionally a *skeleton*. No real checkout is performed and the Stripe
SDK is not a dependency — signature verification is implemented with the stdlib
so the structure is correct and secure without pulling Stripe in.

Security / idempotency contract:
  - When ``settings.STRIPE_WEBHOOK_SECRET`` is set, the ``Stripe-Signature``
    header is verified (HMAC-SHA256 over ``"{timestamp}.{payload}"``). An invalid
    or missing signature is rejected with 400.
  - When the secret is *not* configured, events are still accepted and stored but
    cannot be verified — this limitation is documented and surfaced in the
    response (``signature_verified: false``).
  - Every event is logged on ``BillingWebhookEvent`` and deduplicated on
    ``(provider, provider_event_id)`` so a Stripe retry is never reprocessed.
"""

import hashlib
import hmac
import time

from django.db import IntegrityError, transaction
from django.utils.timezone import now

from .models import BillingWebhookEvent, Subscription

# Stripe event types this skeleton recognises (minimal set).
HANDLED_EVENT_TYPES = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
}

# Map Stripe subscription statuses to our internal Subscription statuses.
STRIPE_STATUS_MAP = {
    "trialing": Subscription.Status.TRIALING,
    "active": Subscription.Status.ACTIVE,
    "past_due": Subscription.Status.PAST_DUE,
    "canceled": Subscription.Status.CANCELLED,
    "unpaid": Subscription.Status.UNPAID,
    "paused": Subscription.Status.PAUSED,
}

_DEFAULT_TOLERANCE_SECONDS = 300


class SignatureVerificationError(Exception):
    """Raised when a Stripe signature header cannot be verified."""


def _parse_signature_header(header: str) -> dict:
    """Parse a ``Stripe-Signature`` header into ``{t: ..., v1: [...]}``."""
    parsed = {"t": None, "v1": []}
    for part in (header or "").split(","):
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key, value = key.strip(), value.strip()
        if key == "t":
            parsed["t"] = value
        elif key == "v1":
            parsed["v1"].append(value)
    return parsed


def verify_stripe_signature(
    payload: bytes, sig_header: str, secret: str, tolerance: int = _DEFAULT_TOLERANCE_SECONDS
) -> bool:
    """Return ``True`` when ``sig_header`` is a valid signature for ``payload``.

    Implements Stripe's scheme: ``signed_payload = "{t}.{payload}"`` and
    ``v1 = HMAC_SHA256(secret, signed_payload)``. Raises
    ``SignatureVerificationError`` on a malformed header or timestamp.
    """
    if not secret:
        raise SignatureVerificationError("No webhook secret configured.")

    parsed = _parse_signature_header(sig_header)
    timestamp, signatures = parsed["t"], parsed["v1"]
    if not timestamp or not signatures:
        raise SignatureVerificationError("Malformed Stripe-Signature header.")

    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise SignatureVerificationError("Invalid timestamp in signature.") from exc

    if tolerance and abs(time.time() - timestamp_int) > tolerance:
        raise SignatureVerificationError("Timestamp outside the tolerance window.")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        secret.encode(), signed_payload, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


@transaction.atomic
def log_and_process_event(
    *, provider_event_id, event_type, payload, signature_verified
):
    """Persist the event idempotently and process it. Returns ``(event, created)``.

    A duplicate ``(provider, provider_event_id)`` is detected and *not*
    reprocessed; the stored event is returned with ``created=False``.
    """
    existing = BillingWebhookEvent.objects.filter(
        provider=BillingWebhookEvent.Provider.STRIPE,
        provider_event_id=provider_event_id,
    ).first()
    if existing is not None:
        return existing, False

    try:
        with transaction.atomic():
            event = BillingWebhookEvent.objects.create(
                provider=BillingWebhookEvent.Provider.STRIPE,
                provider_event_id=provider_event_id,
                event_type=event_type or "",
                status=BillingWebhookEvent.Status.RECEIVED,
                payload=payload or {},
                metadata={"signature_verified": signature_verified},
            )
    except IntegrityError:
        existing = BillingWebhookEvent.objects.filter(
            provider=BillingWebhookEvent.Provider.STRIPE,
            provider_event_id=provider_event_id,
        ).first()
        if existing is not None:
            return existing, False
        raise

    _apply_event(event)
    return event, True


def _apply_event(event: BillingWebhookEvent) -> None:
    """Best-effort processing of a stored event (skeleton)."""
    try:
        if event.event_type in HANDLED_EVENT_TYPES:
            if event.event_type.startswith("customer.subscription."):
                _sync_subscription_from_event(event)
            event.status = BillingWebhookEvent.Status.PROCESSED
        else:
            event.status = BillingWebhookEvent.Status.IGNORED
        event.processed_at = now()
        event.save(update_fields=["status", "processed_at"])
    except Exception as exc:  # noqa: BLE001 — record, never crash the webhook
        event.status = BillingWebhookEvent.Status.FAILED
        event.error_message = str(exc)[:2000]
        event.processed_at = now()
        event.save(update_fields=["status", "error_message", "processed_at"])


def _sync_subscription_from_event(event: BillingWebhookEvent) -> None:
    """Update a local Subscription from a Stripe subscription event, if matched.

    Mapping Stripe customers/subscriptions to local workspaces requires data we do
    not store yet, so this only updates an *existing* subscription matched by
    ``provider_subscription_id``. Unmatched events are stored and ignored — a
    clear, documented limitation of the skeleton.
    """
    obj = (event.payload or {}).get("data", {}).get("object", {})
    provider_subscription_id = obj.get("id")
    if not provider_subscription_id:
        return

    subscription = Subscription.objects.filter(
        provider=Subscription.Provider.STRIPE,
        provider_subscription_id=provider_subscription_id,
    ).first()
    if subscription is None:
        return

    if event.event_type == "customer.subscription.deleted":
        subscription.status = Subscription.Status.CANCELLED
    else:
        mapped = STRIPE_STATUS_MAP.get(obj.get("status"))
        if mapped:
            subscription.status = mapped
    subscription.cancel_at_period_end = bool(obj.get("cancel_at_period_end", False))
    subscription.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
