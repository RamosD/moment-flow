"""Critical public API contracts for CampaignAction."""

import pytest
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from rest_framework.test import APIClient

from apps.campaign_actions.models import CampaignAction
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.rbac.models import Role
from apps.workspaces.models import Workspace, WorkspaceMember

User = get_user_model()

BASE_URL = "/api/v1/campaign-actions/"


def results(response):
    return response.data["results"]


def create_campaign(workspace, suffix):
    artist = Artist.objects.create(
        workspace=workspace,
        name=f"API Artist {suffix}",
        slug=f"api-artist-{suffix}",
    )
    return Campaign.objects.create(
        workspace=workspace,
        artist=artist,
        name=f"API Campaign {suffix}",
        slug=f"api-campaign-{suffix}",
    )


def create_action(workspace, campaign, **overrides):
    values = {
        "workspace": workspace,
        "campaign": campaign,
        "title": "API Action",
        "action_type": CampaignAction.ActionType.MANUAL_TASK,
    }
    values.update(overrides)
    return CampaignAction.objects.create(**values)


def recommendation_payload(campaign, ref="recommendation-ref"):
    return {
        "campaign": str(campaign.id),
        "title": "Recommendation action",
        "action_type": CampaignAction.ActionType.REPORT_REQUEST,
        "recommendation_ref": ref,
        "recommendation_snapshot": {"title": "Recommendation"},
    }


@pytest.mark.django_db
class TestCampaignActionCrud:
    def test_list_is_workspace_scoped_and_paginated(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        mine = create_action(workspace, campaign, title="Mine")
        foreign_workspace = Workspace.objects.create(
            name="Foreign API Workspace",
            slug="foreign-api-workspace",
        )
        foreign_campaign = create_campaign(foreign_workspace, "foreign-list")
        foreign = create_action(
            foreign_workspace,
            foreign_campaign,
            title="Foreign",
        )

        response = client_for_owner.get(BASE_URL, **workspace_header)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert {item["id"] for item in results(response)} == {str(mine.id)}
        assert str(foreign.id) not in {item["id"] for item in results(response)}

    def test_create_detail_and_patch(
        self, client_for_owner, workspace_header, workspace, campaign, owner
    ):
        create = client_for_owner.post(
            BASE_URL,
            {
                "campaign": str(campaign.id),
                "title": "Manual action",
                "description": "Before",
                "action_type": CampaignAction.ActionType.MANUAL_TASK,
                "priority": CampaignAction.Priority.LOW,
                "metadata": {"source_note": "test"},
            },
            format="json",
            **workspace_header,
        )
        assert create.status_code == 201, create.data

        action = CampaignAction.objects.get(id=create.data["id"])
        assert action.workspace_id == workspace.id
        assert action.created_by_id == owner.id
        assert action.updated_by_id == owner.id

        detail = client_for_owner.get(
            f"{BASE_URL}{action.id}/",
            **workspace_header,
        )
        assert detail.status_code == 200
        assert detail.data["title"] == "Manual action"

        update = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {
                "title": "Updated action",
                "description": "After",
                "priority": CampaignAction.Priority.HIGH,
                "metadata": {"updated": True},
            },
            format="json",
            **workspace_header,
        )
        assert update.status_code == 200, update.data
        action.refresh_from_db()
        assert action.title == "Updated action"
        assert action.description == "After"
        assert action.priority == CampaignAction.Priority.HIGH
        assert action.metadata == {"updated": True}

    def test_detail_from_other_workspace_is_404(
        self, client_for_owner, workspace_header
    ):
        foreign_workspace = Workspace.objects.create(
            name="Foreign Detail Workspace",
            slug="foreign-detail-workspace",
        )
        foreign_campaign = create_campaign(foreign_workspace, "foreign-detail")
        foreign = create_action(foreign_workspace, foreign_campaign)

        response = client_for_owner.get(
            f"{BASE_URL}{foreign.id}/",
            **workspace_header,
        )

        assert response.status_code == 404

    def test_put_and_delete_are_not_supported(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        action = create_action(workspace, campaign)
        url = f"{BASE_URL}{action.id}/"

        assert (
            client_for_owner.put(url, {}, format="json", **workspace_header).status_code
            == 405
        )
        assert client_for_owner.delete(url, **workspace_header).status_code == 405


@pytest.mark.django_db
class TestCampaignActionAccess:
    def test_authentication_is_required(self, workspace_header):
        response = APIClient().get(BASE_URL, **workspace_header)
        assert response.status_code == 401

    def test_workspace_header_is_required(self, client_for_owner):
        response = client_for_owner.get(BASE_URL)
        assert response.status_code == 400
        assert "X-Workspace-ID" in response.data

    def test_campaign_from_other_workspace_is_rejected(
        self, client_for_owner, workspace_header
    ):
        foreign_workspace = Workspace.objects.create(
            name="Foreign Campaign Workspace",
            slug="foreign-campaign-workspace",
        )
        foreign_campaign = create_campaign(foreign_workspace, "foreign-create")

        response = client_for_owner.post(
            BASE_URL,
            {
                "campaign": str(foreign_campaign.id),
                "title": "Invalid campaign",
                "action_type": CampaignAction.ActionType.MANUAL_TASK,
            },
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "campaign" in response.data

    def test_viewer_can_list_but_cannot_create(
        self, client_for_owner, workspace_header, workspace, campaign
    ):
        create_action(workspace, campaign)
        viewer = User.objects.create_user(
            email="campaign-actions-viewer@example.com",
            password="pass-12345",
        )
        role = Role.objects.get(workspace__isnull=True, key="viewer")
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=viewer,
            role=role,
            role_key="viewer",
            joined_at=now(),
        )
        client = APIClient()
        client.force_authenticate(viewer)

        assert client.get(BASE_URL, **workspace_header).status_code == 200
        denied = client.post(
            BASE_URL,
            {
                "campaign": str(campaign.id),
                "title": "Denied",
                "action_type": CampaignAction.ActionType.MANUAL_TASK,
            },
            format="json",
            **workspace_header,
        )
        assert denied.status_code == 403


@pytest.mark.django_db
class TestCampaignActionValidation:
    @pytest.mark.parametrize(
        ("field_name", "invalid_value"),
        [
            ("action_type", "not_an_action_type"),
            ("status", "not_a_status"),
        ],
    )
    def test_invalid_choices_are_rejected(
        self,
        field_name,
        invalid_value,
        client_for_owner,
        workspace_header,
        campaign,
    ):
        payload = {
            "campaign": str(campaign.id),
            "title": "Invalid choice",
            "action_type": CampaignAction.ActionType.MANUAL_TASK,
            field_name: invalid_value,
        }

        response = client_for_owner.post(
            BASE_URL,
            payload,
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert field_name in response.data

    def test_dismiss_without_reason_is_rejected(
        self, client_for_owner, workspace_header, campaign
    ):
        response = client_for_owner.post(
            BASE_URL,
            {
                "campaign": str(campaign.id),
                "title": "Dismiss without reason",
                "action_type": CampaignAction.ActionType.DISMISS,
                "recommendation_ref": "dismiss-without-reason",
                "recommendation_snapshot": {"title": "Dismiss me"},
            },
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "dismiss_reason" in response.data

    def test_active_duplicate_is_rejected_but_failed_retry_is_allowed(
        self, client_for_owner, workspace_header, campaign
    ):
        payload = recommendation_payload(campaign, "duplicate-ref")

        first = client_for_owner.post(
            BASE_URL,
            payload,
            format="json",
            **workspace_header,
        )
        assert first.status_code == 201

        duplicate = client_for_owner.post(
            BASE_URL,
            payload,
            format="json",
            **workspace_header,
        )
        assert duplicate.status_code == 400
        assert "recommendation_ref" in duplicate.data

        failed = client_for_owner.patch(
            f"{BASE_URL}{first.data['id']}/",
            {"status": CampaignAction.Status.FAILED},
            format="json",
            **workspace_header,
        )
        assert failed.status_code == 200

        retry = client_for_owner.post(
            BASE_URL,
            payload,
            format="json",
            **workspace_header,
        )
        assert retry.status_code == 201, retry.data


@pytest.mark.django_db
class TestCampaignActionFilters:
    def test_contract_filters_return_only_matching_ids(
        self, client_for_owner, workspace_header, workspace, campaign, owner
    ):
        other_campaign = Campaign.objects.create(
            workspace=workspace,
            artist=campaign.artist,
            name="Filter Campaign",
            slug="filter-campaign",
        )
        manual = create_action(
            workspace,
            campaign,
            title="Manual",
            created_by=owner,
        )
        report = create_action(
            workspace,
            campaign,
            title="Report",
            action_type=CampaignAction.ActionType.REPORT_REQUEST,
            status=CampaignAction.Status.COMPLETED,
            recommendation_ref="filter-target-ref",
            recommendation_snapshot={"title": "Target"},
            created_by=owner,
        )
        failed = create_action(
            workspace,
            campaign,
            title="Failed content",
            action_type=CampaignAction.ActionType.CONTENT_PACK,
            status=CampaignAction.Status.FAILED,
            recommendation_ref="failed-ref",
            recommendation_snapshot={"title": "Failed"},
            created_by=owner,
        )
        other = create_action(
            workspace,
            other_campaign,
            title="Other campaign",
            action_type=CampaignAction.ActionType.REPORT_REQUEST,
            status=CampaignAction.Status.FAILED,
            recommendation_ref="other-ref",
            recommendation_snapshot={"title": "Other"},
            created_by=owner,
        )

        cases = (
            ("campaign", campaign.id, {manual.id, report.id, failed.id}),
            ("recommendation_ref", "filter-target-ref", {report.id}),
            ("status", CampaignAction.Status.FAILED, {failed.id, other.id}),
            (
                "action_type",
                CampaignAction.ActionType.REPORT_REQUEST,
                {report.id, other.id},
            ),
            ("created_by", owner.id, {manual.id, report.id, failed.id, other.id}),
        )

        for field_name, value, expected_ids in cases:
            response = client_for_owner.get(
                BASE_URL,
                {field_name: str(value), "ordering": "created_at"},
                **workspace_header,
            )
            assert response.status_code == 200, response.data
            actual_ids = {item["id"] for item in results(response)}
            assert actual_ids == {str(value) for value in expected_ids}
