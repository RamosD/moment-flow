"""CampaignAction lifecycle rules through PATCH and semantic actions."""

import pytest

from apps.campaign_actions.models import CampaignAction

BASE_URL = "/api/v1/campaign-actions/"


def create_action(workspace, campaign, **overrides):
    values = {
        "workspace": workspace,
        "campaign": campaign,
        "title": "Action",
        "action_type": CampaignAction.ActionType.MANUAL_TASK,
    }
    values.update(overrides)
    return CampaignAction.objects.create(**values)


@pytest.mark.django_db
class TestPatchTransitions:
    def test_invalid_status_is_rejected(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"status": "not_a_status"},
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "status" in response.data

    @pytest.mark.parametrize(
        ("initial_status", "target_status"),
        [
            (CampaignAction.Status.PENDING, CampaignAction.Status.IN_PROGRESS),
            (CampaignAction.Status.PENDING, CampaignAction.Status.FAILED),
            (CampaignAction.Status.IN_PROGRESS, CampaignAction.Status.COMPLETED),
            (CampaignAction.Status.IN_PROGRESS, CampaignAction.Status.FAILED),
            (CampaignAction.Status.IN_PROGRESS, CampaignAction.Status.CANCELLED),
        ],
    )
    def test_allowed_operational_transitions(
        self,
        initial_status,
        target_status,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
    ):
        action = create_action(workspace, campaign, status=initial_status)

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"status": target_status},
            format="json",
            **workspace_header,
        )

        assert response.status_code == 200
        action.refresh_from_db()
        assert action.status == target_status

    def test_complete_sets_completed_at(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"status": CampaignAction.Status.COMPLETED},
            format="json",
            **workspace_header,
        )

        assert response.status_code == 200
        action.refresh_from_db()
        assert action.status == CampaignAction.Status.COMPLETED
        assert action.completed_at is not None
        assert action.cancelled_at is None

    def test_cancel_sets_cancelled_at(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"status": CampaignAction.Status.CANCELLED},
            format="json",
            **workspace_header,
        )

        assert response.status_code == 200
        action.refresh_from_db()
        assert action.status == CampaignAction.Status.CANCELLED
        assert action.cancelled_at is not None
        assert action.completed_at is None

    def test_dismiss_requires_reason_and_persists_it(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)
        url = f"{BASE_URL}{action.id}/"

        invalid = client_for_owner.patch(
            url,
            {"status": CampaignAction.Status.DISMISSED},
            format="json",
            **workspace_header,
        )
        assert invalid.status_code == 400
        assert "dismiss_reason" in invalid.data

        valid = client_for_owner.patch(
            url,
            {
                "status": CampaignAction.Status.DISMISSED,
                "dismiss_reason": "  Not relevant now  ",
            },
            format="json",
            **workspace_header,
        )
        assert valid.status_code == 200
        action.refresh_from_db()
        assert action.status == CampaignAction.Status.DISMISSED
        assert action.dismiss_reason == "Not relevant now"

    @pytest.mark.parametrize(
        "terminal_status",
        [
            CampaignAction.Status.COMPLETED,
            CampaignAction.Status.FAILED,
            CampaignAction.Status.DISMISSED,
            CampaignAction.Status.CANCELLED,
        ],
    )
    def test_terminal_states_cannot_reopen(
        self,
        terminal_status,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
    ):
        action = create_action(
            workspace,
            campaign,
            status=terminal_status,
            dismiss_reason="Reason"
            if terminal_status == CampaignAction.Status.DISMISSED
            else "",
        )

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"status": CampaignAction.Status.PENDING},
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "status" in response.data

    def test_in_progress_cannot_be_dismissed(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(
            workspace,
            campaign,
            status=CampaignAction.Status.IN_PROGRESS,
        )

        response = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {
                "status": CampaignAction.Status.DISMISSED,
                "dismiss_reason": "Too late",
            },
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "status" in response.data


@pytest.mark.django_db
class TestSemanticTransitionActions:
    @pytest.mark.parametrize(
        ("operation", "expected_status", "timestamp_field"),
        [
            ("mark-reviewed", CampaignAction.Status.COMPLETED, "completed_at"),
            ("complete", CampaignAction.Status.COMPLETED, "completed_at"),
            ("cancel", CampaignAction.Status.CANCELLED, "cancelled_at"),
        ],
    )
    def test_no_body_semantic_actions(
        self,
        operation,
        expected_status,
        timestamp_field,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
    ):
        action = create_action(workspace, campaign)

        response = client_for_owner.post(
            f"{BASE_URL}{action.id}/{operation}/",
            **workspace_header,
        )

        assert response.status_code == 200
        action.refresh_from_db()
        assert action.status == expected_status
        assert getattr(action, timestamp_field) is not None

    def test_dismiss_action_requires_body_and_is_idempotent(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)
        url = f"{BASE_URL}{action.id}/dismiss/"

        invalid = client_for_owner.post(url, {}, format="json", **workspace_header)
        assert invalid.status_code == 400

        first = client_for_owner.post(
            url,
            {"dismiss_reason": "No longer useful"},
            format="json",
            **workspace_header,
        )
        assert first.status_code == 200

        second = client_for_owner.post(
            url,
            {"dismiss_reason": "No longer useful"},
            format="json",
            **workspace_header,
        )
        assert second.status_code == 200
        action.refresh_from_db()
        assert action.status == CampaignAction.Status.DISMISSED
        assert action.dismiss_reason == "No longer useful"

    def test_repeated_complete_preserves_timestamp(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)
        url = f"{BASE_URL}{action.id}/complete/"

        assert client_for_owner.post(url, **workspace_header).status_code == 200
        action.refresh_from_db()
        completed_at = action.completed_at

        assert client_for_owner.post(url, **workspace_header).status_code == 200
        action.refresh_from_db()
        assert action.completed_at == completed_at

    def test_invalid_semantic_transition_returns_400(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(
            workspace,
            campaign,
            status=CampaignAction.Status.COMPLETED,
        )

        response = client_for_owner.post(
            f"{BASE_URL}{action.id}/cancel/",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "status" in response.data


@pytest.mark.django_db
class TestSemanticCreation:
    def test_mark_reviewed_type_defaults_to_completed(
        self, client_for_owner, workspace_header, campaign
    ):
        response = client_for_owner.post(
            BASE_URL,
            {
                "campaign": str(campaign.id),
                "title": "Reviewed recommendation",
                "action_type": CampaignAction.ActionType.MARK_REVIEWED,
                "recommendation_ref": "rec-reviewed",
                "recommendation_snapshot": {"title": "Review me"},
            },
            format="json",
            **workspace_header,
        )

        assert response.status_code == 201
        action = CampaignAction.objects.get(id=response.data["id"])
        assert action.status == CampaignAction.Status.COMPLETED
        assert action.completed_at is not None

    def test_dismiss_type_defaults_to_dismissed(
        self, client_for_owner, workspace_header, campaign
    ):
        response = client_for_owner.post(
            BASE_URL,
            {
                "campaign": str(campaign.id),
                "title": "Dismiss recommendation",
                "action_type": CampaignAction.ActionType.DISMISS,
                "recommendation_ref": "rec-dismiss",
                "recommendation_snapshot": {"title": "Dismiss me"},
                "dismiss_reason": "Not aligned",
            },
            format="json",
            **workspace_header,
        )

        assert response.status_code == 201
        action = CampaignAction.objects.get(id=response.data["id"])
        assert action.status == CampaignAction.Status.DISMISSED
        assert action.dismiss_reason == "Not aligned"
