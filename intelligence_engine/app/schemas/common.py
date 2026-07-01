"""Common schemas and controlled vocabularies for the Intelligence Engine.

These types are the shared building blocks of every internal contract
(docs/gestao/fundamentos/backlog.md, sections 6.3–6.5). The controlled
vocabularies (Literals) are aligned with the real Backend Core entities so the
engine never recommends or references something Django cannot act on:

  - `EntityType`        → backlog section 6.3 entity types;
  - `ContentPackKey`    → `apps.content.ContentPack.PackType`;
  - `OutputType`        → `apps.content.Template.TemplateType`;
  - `ActionType`/`MomentType` → backlog sections 7.4/7.5.

Design notes:
  - Request envelopes forbid unknown fields (`extra="forbid"`) so typos and
    contract drift fail loudly, mirroring the renderer's strict job envelope.
  - The opaque `data` bundle (see `app.schemas.campaign`) is the one place that
    stays permissive, so Django payloads can evolve without breaking the engine.
  - `confidence` is modelled as a constrained float 0.0–1.0 (`ConfidenceScore`)
    to match the numeric examples in the backlog (0.82, 0.74). The qualitative
    bands are expressed by `Priority`, `Severity` and `Grade`.
"""

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

# --- Controlled vocabularies (backlog sections 6–7) ---------------------------

EntityType = Literal[
    "campaign",
    "artist",
    "track",
    "content_pack_request",
    "report",
    "media_kit",
]

ResponseStatus = Literal["completed", "failed"]
CampaignHealth = Literal["good", "warning", "critical", "unknown"]
Grade = Literal["A", "B", "C", "D", "unknown"]
Priority = Literal["low", "medium", "high"]
Severity = Literal["low", "medium", "high"]

ActionType = Literal[
    "create_release_post",
    "create_story",
    "create_milestone_post",
    "create_weekly_growth_post",
    "create_media_kit",
    "create_report",
    "improve_smart_link",
    "wait_for_more_data",
    "no_action",
]

MomentType = Literal[
    "release_window",
    "weekly_growth",
    "milestone_reached",
    "low_engagement",
    "content_gap",
    "report_due",
    "media_kit_missing",
    "smart_link_activity",
]

# Aligned with apps.content.ContentPack.PackType in the Backend Core.
ContentPackKey = Literal[
    "release_pack",
    "milestone_pack",
    "weekly_growth_pack",
    "monthly_recap_pack",
    "comeback_pack",
    "ranking_pack",
    "auto_media_kit",
    "label_reporting_pack",
]

# Aligned with apps.content.Template.TemplateType in the Backend Core.
OutputType = Literal[
    "post",
    "story",
    "carousel",
    "carousel_slide",
    "card",
    "thumbnail",
    "report",
    "media_kit",
    "reel",
    "short",
    "widget",
    "embed",
]

# --- Constrained scalars ------------------------------------------------------

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Score = Annotated[int, Field(ge=0, le=100)]
ConfidenceScore = Annotated[float, Field(ge=0.0, le=1.0)]
Weight = Annotated[float, Field(ge=0.0, le=1.0)]


def _validate_payload_version(value: str) -> str:
    if not value.startswith("1.0"):
        raise ValueError("payload_version must start with '1.0' for this MVP contract")
    return value


# Required, and pinned to the 1.0 contract family (backlog section 6.3).
PayloadVersion = Annotated[NonEmptyStr, AfterValidator(_validate_payload_version)]


# --- Shared models ------------------------------------------------------------


class EntityRef(BaseModel):
    """Reference to a Backend Core entity the request is about."""

    model_config = ConfigDict(extra="forbid")

    type: EntityType
    id: NonEmptyStr


class Explanation(BaseModel):
    """A human-readable, machine-traceable justification for a result."""

    model_config = ConfigDict(extra="forbid")

    code: NonEmptyStr
    message: NonEmptyStr
    weight: Weight | None = None


class Warning(BaseModel):  # noqa: A001 - matches the backlog contract field name
    """A non-fatal signal, typically raised when input data is insufficient."""

    model_config = ConfigDict(extra="forbid")

    code: NonEmptyStr
    message: NonEmptyStr
    details: dict[str, Any] = Field(default_factory=dict)


class BaseIntelligenceRequest(BaseModel):
    """Common envelope for every internal request (backlog section 6.3).

    Specific endpoints subclass this and add a typed `data` bundle. Unknown
    top-level fields are rejected so contract drift surfaces as a clear 422.
    """

    model_config = ConfigDict(extra="forbid")

    payload_version: PayloadVersion
    workspace_id: NonEmptyStr
    request_id: NonEmptyStr
    entity: EntityRef
    context: dict[str, Any] = Field(default_factory=dict)
