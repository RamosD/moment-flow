"""Validation of CampaignAction links to existing product artefacts."""

import pytest

from apps.campaign_actions.models import CampaignAction
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.content.models import ContentOutput, ContentPack, ContentPackRequest, Template
from apps.reports.models import MediaKit, Report
from apps.workspaces.models import Workspace

BASE_URL = "/api/v1/campaign-actions/"


def create_campaign(workspace, suffix):
    artist = Artist.objects.create(
        workspace=workspace,
        name=f"Artist {suffix}",
        slug=f"artist-{suffix}",
    )
    return Campaign.objects.create(
        workspace=workspace,
        artist=artist,
        name=f"Campaign {suffix}",
        slug=f"campaign-{suffix}",
    )


def create_artifacts(workspace, campaign, suffix):
    content_pack = ContentPack.objects.create(
        pack_key=f"pack-{suffix}",
        name=f"Pack {suffix}",
        pack_type=ContentPack.PackType.RELEASE_PACK,
    )
    content_pack_request = ContentPackRequest.objects.create(
        workspace=workspace,
        campaign=campaign,
        content_pack=content_pack,
    )
    template = Template.objects.create(
        template_key=f"template-{suffix}",
        name=f"Template {suffix}",
        template_type=Template.TemplateType.POST,
    )
    content_output = ContentOutput.objects.create(
        workspace=workspace,
        campaign=campaign,
        content_pack_request=content_pack_request,
        template=template,
        output_type="post",
    )
    report = Report.objects.create(
        workspace=workspace,
        campaign=campaign,
        report_type=Report.ReportType.CAMPAIGN_REPORT,
        title=f"Report {suffix}",
    )
    media_kit = MediaKit.objects.create(
        workspace=workspace,
        campaign=campaign,
        artist=campaign.artist,
        title=f"Media Kit {suffix}",
    )
    return {
        "related_content_pack_request": content_pack_request,
        "related_content_output": content_output,
        "related_report": report,
        "related_media_kit": media_kit,
    }


def action_payload(campaign, action_type, ref, **relations):
    payload = {
        "campaign": str(campaign.id),
        "title": f"Action {ref}",
        "action_type": action_type,
    }
    if action_type != CampaignAction.ActionType.MANUAL_TASK:
        payload.update(
            recommendation_ref=ref,
            recommendation_snapshot={"title": f"Recommendation {ref}"},
        )
    payload.update({field: str(value.id) for field, value in relations.items()})
    return payload


@pytest.fixture
def artifact_world(workspace, campaign):
    same_campaign = create_artifacts(workspace, campaign, "same")
    other_campaign = create_campaign(workspace, "other")
    other_campaign_artifacts = create_artifacts(
        workspace, other_campaign, "other"
    )

    foreign_workspace = Workspace.objects.create(
        name="Foreign Workspace",
        slug="foreign-artifact-workspace",
    )
    foreign_campaign = create_campaign(foreign_workspace, "foreign")
    foreign_artifacts = create_artifacts(
        foreign_workspace, foreign_campaign, "foreign"
    )
    return {
        "same": same_campaign,
        "other_campaign": other_campaign_artifacts,
        "foreign": foreign_artifacts,
    }


@pytest.mark.django_db
class TestValidRelatedArtifacts:
    def test_each_action_type_accepts_its_existing_artifact(
        self,
        client_for_owner,
        workspace_header,
        campaign,
        artifact_world,
    ):
        same = artifact_world["same"]
        cases = (
            (
                CampaignAction.ActionType.CONTENT_PACK,
                {
                    "related_content_pack_request": same[
                        "related_content_pack_request"
                    ],
                    "related_content_output": same["related_content_output"],
                },
            ),
            (
                CampaignAction.ActionType.REPORT_REQUEST,
                {"related_report": same["related_report"]},
            ),
            (
                CampaignAction.ActionType.MEDIA_KIT_REQUEST,
                {"related_media_kit": same["related_media_kit"]},
            ),
        )

        for index, (action_type, relations) in enumerate(cases):
            response = client_for_owner.post(
                BASE_URL,
                action_payload(campaign, action_type, f"valid-{index}", **relations),
                format="json",
                **workspace_header,
            )
            assert response.status_code == 201, response.data

    @pytest.mark.parametrize(
        "action_type",
        [
            CampaignAction.ActionType.CONTENT_PACK,
            CampaignAction.ActionType.REPORT_REQUEST,
            CampaignAction.ActionType.MEDIA_KIT_REQUEST,
        ],
    )
    def test_related_artifact_is_optional_on_create(
        self,
        action_type,
        client_for_owner,
        workspace_header,
        campaign,
    ):
        response = client_for_owner.post(
            BASE_URL,
            action_payload(campaign, action_type, f"optional-{action_type}"),
            format="json",
            **workspace_header,
        )
        assert response.status_code == 201, response.data


@pytest.mark.django_db
class TestRelatedArtifactIsolation:
    @pytest.mark.parametrize(
        ("action_type", "field_name"),
        [
            (
                CampaignAction.ActionType.CONTENT_PACK,
                "related_content_pack_request",
            ),
            (CampaignAction.ActionType.CONTENT_PACK, "related_content_output"),
            (CampaignAction.ActionType.REPORT_REQUEST, "related_report"),
            (CampaignAction.ActionType.MEDIA_KIT_REQUEST, "related_media_kit"),
        ],
    )
    @pytest.mark.parametrize("scope", ["other_campaign", "foreign"])
    def test_wrong_campaign_or_workspace_is_rejected(
        self,
        action_type,
        field_name,
        scope,
        client_for_owner,
        workspace_header,
        campaign,
        artifact_world,
    ):
        artifact = artifact_world[scope][field_name]
        response = client_for_owner.post(
            BASE_URL,
            action_payload(
                campaign,
                action_type,
                f"{scope}-{field_name}",
                **{field_name: artifact},
            ),
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert field_name in response.data

    def test_report_and_media_kit_without_campaign_are_rejected(
        self,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
    ):
        report = Report.objects.create(
            workspace=workspace,
            campaign=None,
            report_type=Report.ReportType.CAMPAIGN_REPORT,
            title="Unscoped report",
        )
        media_kit = MediaKit.objects.create(
            workspace=workspace,
            campaign=None,
            artist=campaign.artist,
            title="Unscoped media kit",
        )

        for index, (action_type, field_name, artifact) in enumerate(
            (
                (
                    CampaignAction.ActionType.REPORT_REQUEST,
                    "related_report",
                    report,
                ),
                (
                    CampaignAction.ActionType.MEDIA_KIT_REQUEST,
                    "related_media_kit",
                    media_kit,
                ),
            )
        ):
            response = client_for_owner.post(
                BASE_URL,
                action_payload(
                    campaign,
                    action_type,
                    f"unscoped-{index}",
                    **{field_name: artifact},
                ),
                format="json",
                **workspace_header,
            )
            assert response.status_code == 400
            assert field_name in response.data


@pytest.mark.django_db
class TestActionTypeCompatibility:
    @pytest.mark.parametrize(
        ("action_type", "field_name"),
        [
            (CampaignAction.ActionType.CONTENT_PACK, "related_report"),
            (
                CampaignAction.ActionType.REPORT_REQUEST,
                "related_content_pack_request",
            ),
            (
                CampaignAction.ActionType.MEDIA_KIT_REQUEST,
                "related_content_output",
            ),
            (CampaignAction.ActionType.MANUAL_TASK, "related_media_kit"),
            (CampaignAction.ActionType.MARK_REVIEWED, "related_report"),
            (CampaignAction.ActionType.DISMISS, "related_report"),
        ],
    )
    def test_incompatible_relation_is_rejected(
        self,
        action_type,
        field_name,
        client_for_owner,
        workspace_header,
        campaign,
        artifact_world,
    ):
        artifact = artifact_world["same"][field_name]
        payload = action_payload(
            campaign,
            action_type,
            f"incompatible-{action_type}-{field_name}",
            **{field_name: artifact},
        )
        if action_type == CampaignAction.ActionType.DISMISS:
            payload["dismiss_reason"] = "Not relevant"

        response = client_for_owner.post(
            BASE_URL,
            payload,
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert field_name in response.data

    def test_output_must_match_linked_content_pack_request(
        self,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
        artifact_world,
    ):
        first_request = artifact_world["same"]["related_content_pack_request"]
        other_pack = ContentPack.objects.create(
            pack_key="mismatched-pack",
            name="Mismatched Pack",
            pack_type=ContentPack.PackType.RELEASE_PACK,
        )
        second_request = ContentPackRequest.objects.create(
            workspace=workspace,
            campaign=campaign,
            content_pack=other_pack,
        )
        mismatched_output = artifact_world["same"]["related_content_output"]
        mismatched_output.content_pack_request = second_request
        mismatched_output.save(update_fields=["content_pack_request", "updated_at"])

        response = client_for_owner.post(
            BASE_URL,
            action_payload(
                campaign,
                CampaignAction.ActionType.CONTENT_PACK,
                "mismatched-request",
                related_content_pack_request=first_request,
                related_content_output=mismatched_output,
            ),
            format="json",
            **workspace_header,
        )

        assert response.status_code == 400
        assert "related_content_output" in response.data

    def test_patch_uses_existing_action_type_for_compatibility(
        self,
        client_for_owner,
        workspace_header,
        workspace,
        campaign,
        artifact_world,
    ):
        action = CampaignAction.objects.create(
            workspace=workspace,
            campaign=campaign,
            title="Report action",
            action_type=CampaignAction.ActionType.REPORT_REQUEST,
            recommendation_ref="patch-report",
            recommendation_snapshot={"title": "Patch report"},
        )

        invalid = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {
                "related_media_kit": str(
                    artifact_world["same"]["related_media_kit"].id
                )
            },
            format="json",
            **workspace_header,
        )
        assert invalid.status_code == 400
        assert "related_media_kit" in invalid.data

        valid = client_for_owner.patch(
            f"{BASE_URL}{action.id}/",
            {"related_report": str(artifact_world["same"]["related_report"].id)},
            format="json",
            **workspace_header,
        )
        assert valid.status_code == 200, valid.data
