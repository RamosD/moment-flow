"""Response envelopes for the Intelligence Engine (backlog sections 6.4–6.5).

`IntelligenceResponse` is generic over its `result` payload, so each endpoint
gets a concrete, fully-typed response (and a distinct OpenAPI schema) without
repeating the common envelope fields. `ErrorResponse` mirrors the runtime error
body produced by `app.core.errors.AppError.to_response_body`, so the documented
error contract and the actual responses stay in lockstep.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.constants import SERVICE_NAME, SERVICE_VERSION
from app.schemas.common import Explanation, ResponseStatus, Warning


class ResponseMetadata(BaseModel):
    """Free-form, extensible metadata attached to every response."""

    model_config = ConfigDict(extra="allow")

    generated_at: datetime | None = None
    payload_version: str | None = None


class IntelligenceResponse[ResultT](BaseModel):
    """Common success envelope; `result` is specialised per endpoint."""

    status: ResponseStatus = "completed"
    engine: str = SERVICE_NAME
    engine_version: str = SERVICE_VERSION
    request_id: str
    workspace_id: str
    result: ResultT
    explanations: list[Explanation] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)


# --- Error contract (mirrors app.core.errors) ---------------------------------


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorMetadata(BaseModel):
    engine: str = SERVICE_NAME
    engine_version: str = SERVICE_VERSION


class ErrorResponse(BaseModel):
    """Normalised error body (backlog section 6.5)."""

    status: Literal["failed"] = "failed"
    error: ErrorDetail
    metadata: ErrorMetadata = Field(default_factory=ErrorMetadata)
