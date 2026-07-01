"""Smoke test: every required factory builds a valid, tenant-consistent object."""

import pytest

from tests import factories


@pytest.mark.django_db
def test_all_factories_build():
    objs = {
        "user": factories.UserFactory(),
        "workspace": factories.WorkspaceFactory(),
        "permission": factories.PermissionFactory(),
        "role": factories.RoleFactory(),
        "member": factories.WorkspaceMemberFactory(),
        "asset": factories.AssetFactory(),
        "artist": factories.ArtistFactory(),
        "track": factories.TrackFactory(),
        "platform_link": factories.TrackPlatformLinkFactory(),
        "campaign": factories.CampaignFactory(),
        "goal": factories.CampaignGoalFactory(),
        "template": factories.TemplateFactory(),
        "template_version": factories.TemplateVersionFactory(),
        "pack": factories.ContentPackFactory(),
        "pack_request": factories.ContentPackRequestFactory(),
        "output": factories.ContentOutputFactory(),
        "smart_link": factories.SmartLinkFactory(),
        "destination": factories.SmartLinkDestinationFactory(),
        "plan": factories.PlanFactory(),
        "subscription": factories.SubscriptionFactory(),
        "usage": factories.UsageEventFactory(),
        "credit": factories.CreditLedgerEntryFactory(),
        "report": factories.ReportFactory(),
        "media_kit": factories.MediaKitFactory(),
    }
    for name, obj in objs.items():
        assert obj.pk is not None, name

    # Tenant consistency across factory-built graphs.
    assert objs["track"].workspace_id == objs["track"].artist.workspace_id
    assert (
        objs["destination"].workspace_id == objs["destination"].smart_link.workspace_id
    )
    assert objs["pack_request"].workspace_id == objs["pack_request"].campaign.workspace_id
