"""TEMPORARY internal debug endpoints (IE-002).

These three routes exist only to exercise the authentication
(`require_internal_token`) and normalised error contract (`AppError`,
`RequestValidationError`, unexpected exceptions) introduced in this phase,
because no real internal endpoint (`/analysis/campaign`, `/scoring/campaign`,
...) exists yet — those land in IE-004 onward.

They are intentionally minimal and carry no business logic:

  - `GET  /internal/_debug/ping`  — returns 200 once authenticated.
  - `POST /internal/_debug/echo`  — exercises payload validation (422 on a
    missing/invalid body via `invalid_payload`).
  - `GET  /internal/_debug/boom`  — deliberately raises an unhandled
    exception to exercise the generic `internal_error` (500) contract.

DELETE THIS MODULE once a real protected endpoint exists and exercises the
same auth/error machinery in its own tests.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_internal_token

router = APIRouter(
    prefix="/internal/_debug",
    tags=["internal-debug-temporary"],
    dependencies=[Depends(require_internal_token)],
)


class EchoPayload(BaseModel):
    message: str


@router.get("/ping")
def ping() -> dict[str, bool | str]:
    return {"status": "ok", "authenticated": True}


@router.post("/echo")
def echo(payload: EchoPayload) -> dict[str, str]:
    return {"echo": payload.message}


@router.get("/boom")
def boom() -> None:
    raise RuntimeError("Deliberate failure for internal_error contract testing.")
