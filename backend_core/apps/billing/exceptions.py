"""Billing-specific API exceptions with clear, actionable messages.

These are raised inside product flows (artist/track/campaign/smart-link/content
pack creation). They return explicit HTTP statuses so a client always knows *why*
an action was refused — never a silent block.
"""

from rest_framework.exceptions import APIException


class QuotaExceeded(APIException):
    """Raised when a workspace action would exceed its plan limit."""

    status_code = 402
    default_detail = "Plan limit reached."
    default_code = "quota_exceeded"


class InsufficientCredits(APIException):
    """Raised when a workspace lacks the credits required for an action."""

    status_code = 402
    default_detail = "Not enough credits for this action."
    default_code = "insufficient_credits"
