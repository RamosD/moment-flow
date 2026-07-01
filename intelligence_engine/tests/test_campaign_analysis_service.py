"""Unit tests for CampaignAnalysisService (IE-004).

Each test drives the service directly (no HTTP) and asserts deterministic,
explainable behaviour for one rule or edge case.
"""

from app.schemas.campaign import CampaignAnalysisRequest
from app.services.campaign_analysis import CampaignAnalysisService

service = CampaignAnalysisService()


def _request(data: dict | None = None, context: dict | None = None) -> CampaignAnalysisRequest:
    return CampaignAnalysisRequest(
        payload_version="1.0",
        workspace_id="ws-1",
        request_id="req-1",
        entity={"type": "campaign", "id": "campaign-1"},
        context=context or {},
        data=data or {},
    )


def _analyse(data: dict | None = None, context: dict | None = None):
    return service.analyse(_request(data, context))


def _explanation_codes(response) -> set[str]:
    return {explanation.code for explanation in response.explanations}


def _warning_codes(response) -> set[str]:
    return {warning.code for warning in response.warnings}


# --- R0: insufficient data ----------------------------------------------------


def test_empty_bundle_is_unknown_with_warning() -> None:
    response = _analyse({})

    assert response.result.campaign_health == "unknown"
    assert "insufficient_data" in _warning_codes(response)
    assert response.result.strengths == []
    assert response.result.opportunities == []
    # status envelope is still a normal completed response (not an error).
    assert response.status == "completed"


# --- R1 / R2: content outputs -------------------------------------------------


def test_completed_content_outputs_is_a_strength() -> None:
    response = _analyse(
        {"campaign": {"status": "active"}, "content_outputs": [{"status": "completed"}]}
    )

    assert "has_content_outputs" in _explanation_codes(response)
    assert any("produced content" in s for s in response.result.strengths)


def test_no_content_outputs_is_a_content_gap_opportunity() -> None:
    response = _analyse({"campaign": {"status": "draft"}})

    assert "content_gap" in _explanation_codes(response)
    assert any("content" in o.lower() for o in response.result.opportunities)


def test_queued_outputs_do_not_count_as_completed() -> None:
    response = _analyse(
        {"campaign": {"status": "draft"}, "content_outputs": [{"status": "queued"}]}
    )

    assert "content_gap" in _explanation_codes(response)
    assert "has_content_outputs" not in _explanation_codes(response)


# --- R1b: recency depends on reference_date -----------------------------------


def test_recent_output_adds_recency_strength() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
        },
        {"reference_date": "2026-06-24"},
    )

    assert "recent_content_outputs" in _explanation_codes(response)


def test_stale_output_has_no_recency_strength() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-01-01"}],
        },
        {"reference_date": "2026-06-24"},
    )

    assert "has_content_outputs" in _explanation_codes(response)
    assert "recent_content_outputs" not in _explanation_codes(response)


def test_recency_is_skipped_without_reference_date() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
        }
    )

    assert "has_content_outputs" in _explanation_codes(response)
    assert "recent_content_outputs" not in _explanation_codes(response)


# --- R3 / R4: smart links -----------------------------------------------------


def test_smart_link_activity_is_a_strength() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {"total_clicks": 500, "clicks_last_7_days": 30},
        }
    )

    assert "smart_link_activity" in _explanation_codes(response)


def test_smart_link_zero_activity_is_a_weakness() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {"total_clicks": 0, "active_links": 0},
        }
    )

    assert "smart_link_no_activity" in _explanation_codes(response)
    assert response.result.weaknesses


def test_missing_smart_link_stats_is_a_warning_not_a_weakness() -> None:
    response = _analyse({"campaign": {"status": "draft"}})

    assert "smart_link_stats_missing" in _warning_codes(response)
    assert "smart_link_no_activity" not in _explanation_codes(response)


# --- R5 / R6: reports and media kits ------------------------------------------


def test_no_completed_report_is_report_due() -> None:
    response = _analyse({"campaign": {"status": "draft"}})

    assert "report_due" in _explanation_codes(response)


def test_recent_completed_report_clears_report_due() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "previous_reports": [{"status": "completed", "period_end": "2026-06-10"}],
        },
        {"reference_date": "2026-06-24"},
    )

    assert "report_due" not in _explanation_codes(response)


def test_stale_completed_report_is_still_report_due() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "previous_reports": [{"status": "completed", "period_end": "2026-01-01"}],
        },
        {"reference_date": "2026-06-24"},
    )

    assert "report_due" in _explanation_codes(response)


def test_usable_media_kit_clears_media_kit_missing() -> None:
    response = _analyse({"campaign": {"status": "active"}, "media_kits": [{"status": "published"}]})

    assert "media_kit_missing" not in _explanation_codes(response)


def test_missing_media_kit_is_an_opportunity() -> None:
    response = _analyse({"campaign": {"status": "draft"}})

    assert "media_kit_missing" in _explanation_codes(response)


# --- R7: risk and health ------------------------------------------------------


def test_active_campaign_without_traction_is_critical() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {"total_clicks": 0, "active_links": 0},
        }
    )

    assert "active_campaign_no_traction" in _explanation_codes(response)
    assert response.result.risks
    assert response.result.campaign_health == "critical"


def test_healthy_campaign_is_good() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed"}],
            "smart_link_stats": {"total_clicks": 500, "clicks_last_7_days": 40},
            "previous_reports": [{"status": "completed"}],
            "media_kits": [{"status": "published"}],
        }
    )

    assert response.result.campaign_health == "good"
    assert response.result.strengths
    assert response.result.risks == []
    assert response.result.weaknesses == []


# --- consistency checks: warn, never raise ------------------------------------


def test_inconsistent_campaign_dates_warns() -> None:
    response = _analyse(
        {"campaign": {"status": "active", "start_date": "2026-06-10", "end_date": "2026-06-01"}}
    )

    assert "inconsistent_campaign_dates" in _warning_codes(response)


def test_negative_smart_link_counts_warn_and_are_not_activity() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "smart_link_stats": {"total_clicks": -5, "active_links": -1},
        }
    )

    assert "negative_smart_link_stats" in _warning_codes(response)
    assert "smart_link_activity" not in _explanation_codes(response)


def test_future_content_output_warns() -> None:
    response = _analyse(
        {
            "campaign": {"status": "active"},
            "content_outputs": [{"status": "completed", "created_at": "2026-12-31"}],
        },
        {"reference_date": "2026-06-24"},
    )

    assert "future_content_output_date" in _warning_codes(response)


def test_invalid_reference_date_warns_and_does_not_raise() -> None:
    response = _analyse({"campaign": {"status": "draft"}}, {"reference_date": "31-12-2026"})

    assert "invalid_reference_date" in _warning_codes(response)
    assert response.result.campaign_health in {"warning", "good", "critical", "unknown"}


def test_unknown_extra_data_fields_are_tolerated() -> None:
    # Permissive bundle: Django may enrich the payload without breaking us.
    response = _analyse(
        {"campaign": {"status": "active", "future_field": "kept"}, "brand_new_section": {"x": 1}}
    )

    assert response.status == "completed"


# --- determinism --------------------------------------------------------------


def test_same_input_produces_identical_output() -> None:
    data = {
        "campaign": {"status": "active"},
        "content_outputs": [{"status": "completed", "created_at": "2026-06-20"}],
        "smart_link_stats": {"total_clicks": 500, "clicks_last_7_days": 40},
    }
    context = {"reference_date": "2026-06-24"}

    first = service.analyse(_request(data, context)).model_dump()
    second = service.analyse(_request(data, context)).model_dump()

    assert first == second


def test_metadata_echoes_payload_version_without_timestamp() -> None:
    response = _analyse({"campaign": {"status": "draft"}})

    assert response.metadata.payload_version == "1.0"
    # generated_at stays None so the response is byte-for-byte reproducible.
    assert response.metadata.generated_at is None
