"""factory-boy factories for the ChartRex backend core.

Conventions:
  - Child entities derive ``workspace`` from their parent via ``SelfAttribute`` so
    a factory-built graph is always tenant-consistent (e.g. a Track shares its
    Artist's workspace).
  - Slugs / keys use ``Sequence`` to satisfy uniqueness constraints.
  - ``UserFactory`` goes through the manager's ``create_user`` so passwords are
    hashed.

These build model graphs directly (bypassing the API), which is exactly what the
multi-tenancy / RBAC / billing regression tests need.
"""

from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from apps.billing.models import (
    CreditLedgerEntry,
    Plan,
    Subscription,
    UsageEvent,
)
from apps.campaigns.models import Campaign, CampaignGoal
from apps.catalogue.models import Artist, Track, TrackPlatformLink
from apps.content.models import (
    ContentOutput,
    ContentPack,
    ContentPackRequest,
    Template,
    TemplateVersion,
)
from apps.core.models import Asset
from apps.links.models import SmartLink, SmartLinkDestination
from apps.rbac.models import Permission, Role
from apps.reports.models import MediaKit, Report
from apps.workspaces.models import Workspace, WorkspaceMember

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Use the manager so the password is hashed.
        password = kwargs.pop("password", "pass-12345")
        return model_class.objects.create_user(password=password, **kwargs)


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Sequence(lambda n: f"Workspace {n}")
    slug = factory.Sequence(lambda n: f"workspace-{n}")
    workspace_type = Workspace.WorkspaceType.ARTIST
    status = Workspace.Status.ACTIVE


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission
        django_get_or_create = ("key",)

    key = factory.Sequence(lambda n: f"domain:action{n}")
    name = factory.Sequence(lambda n: f"Permission {n}")
    domain = "domain"


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role

    workspace = None
    key = factory.Sequence(lambda n: f"role-{n}")
    name = factory.Sequence(lambda n: f"Role {n}")
    is_system = False


class WorkspaceMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role_key = "viewer"
    status = WorkspaceMember.Status.ACTIVE


class AssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Asset

    workspace = factory.SubFactory(WorkspaceFactory)
    asset_type = Asset.AssetType.OTHER
    storage_provider = Asset.StorageProvider.LOCAL
    file_name = factory.Sequence(lambda n: f"file-{n}.png")


class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Artist

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Artist {n}")
    slug = factory.Sequence(lambda n: f"artist-{n}")
    status = Artist.Status.ACTIVE


class TrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Track

    artist = factory.SubFactory(ArtistFactory)
    workspace = factory.SelfAttribute("artist.workspace")
    title = factory.Sequence(lambda n: f"Track {n}")
    slug = factory.Sequence(lambda n: f"track-{n}")
    track_type = Track.TrackType.SINGLE
    status = Track.Status.RELEASED


class TrackPlatformLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackPlatformLink

    track = factory.SubFactory(TrackFactory)
    workspace = factory.SelfAttribute("track.workspace")
    platform = TrackPlatformLink.Platform.CUSTOM
    external_id = factory.Sequence(lambda n: f"ext-{n}")
    url = factory.Sequence(lambda n: f"https://example.com/track/{n}")
    status = TrackPlatformLink.Status.VALID


class CampaignFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campaign

    artist = factory.SubFactory(ArtistFactory)
    workspace = factory.SelfAttribute("artist.workspace")
    name = factory.Sequence(lambda n: f"Campaign {n}")
    slug = factory.Sequence(lambda n: f"campaign-{n}")
    campaign_type = Campaign.CampaignType.SINGLE_RELEASE
    status = Campaign.Status.ACTIVE


class CampaignGoalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CampaignGoal

    campaign = factory.SubFactory(CampaignFactory)
    workspace = factory.SelfAttribute("campaign.workspace")
    goal_type = CampaignGoal.GoalType.VIEWS
    status = CampaignGoal.Status.ACTIVE


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Template

    workspace = None  # global by default
    template_key = factory.Sequence(lambda n: f"template-{n}")
    name = factory.Sequence(lambda n: f"Template {n}")
    template_type = Template.TemplateType.POST
    status = Template.Status.ACTIVE


class TemplateVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TemplateVersion

    template = factory.SubFactory(TemplateFactory)
    version = factory.Sequence(lambda n: f"1.0.{n}")
    renderer_type = TemplateVersion.RendererType.HTML_SVG
    status = TemplateVersion.Status.ACTIVE


class ContentPackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentPack

    workspace = None  # global by default
    pack_key = factory.Sequence(lambda n: f"pack-{n}")
    name = factory.Sequence(lambda n: f"Pack {n}")
    pack_type = ContentPack.PackType.RELEASE_PACK
    status = ContentPack.Status.ACTIVE


class ContentPackRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentPackRequest

    campaign = factory.SubFactory(CampaignFactory)
    workspace = factory.SelfAttribute("campaign.workspace")
    content_pack = factory.SubFactory(ContentPackFactory)
    requested_by = factory.SubFactory(UserFactory)
    status = ContentPackRequest.Status.QUEUED


class ContentOutputFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentOutput

    campaign = factory.SubFactory(CampaignFactory)
    workspace = factory.SelfAttribute("campaign.workspace")
    template = factory.SubFactory(TemplateFactory)
    output_type = "post"
    status = ContentOutput.Status.QUEUED


class SmartLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SmartLink

    campaign = factory.SubFactory(CampaignFactory)
    workspace = factory.SelfAttribute("campaign.workspace")
    slug = factory.Sequence(lambda n: f"smartlink-{n}")
    title = factory.Sequence(lambda n: f"Smart Link {n}")
    status = SmartLink.Status.ACTIVE


class SmartLinkDestinationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SmartLinkDestination

    smart_link = factory.SubFactory(SmartLinkFactory)
    workspace = factory.SelfAttribute("smart_link.workspace")
    platform = SmartLinkDestination.Platform.YOUTUBE
    label = factory.Sequence(lambda n: f"Destination {n}")
    url = factory.Sequence(lambda n: f"https://youtube.com/watch?v=vid{n}")
    sort_order = factory.Sequence(lambda n: n)
    is_active = True


class PlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ("plan_key",)

    plan_key = factory.Sequence(lambda n: f"plan-{n}")
    name = factory.Sequence(lambda n: f"Plan {n}")
    billing_interval = Plan.BillingInterval.MONTH
    base_price = Decimal("0")
    currency = "USD"
    status = Plan.Status.ACTIVE
    is_public = True


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    workspace = factory.SubFactory(WorkspaceFactory)
    plan = factory.SubFactory(PlanFactory)
    provider = Subscription.Provider.MANUAL
    status = Subscription.Status.ACTIVE


class UsageEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UsageEvent

    workspace = factory.SubFactory(WorkspaceFactory)
    event_type = UsageEvent.EventType.ARTIST_CREATED
    quantity = Decimal("1")


class CreditLedgerEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreditLedgerEntry

    workspace = factory.SubFactory(WorkspaceFactory)
    transaction_type = CreditLedgerEntry.TransactionType.GRANT
    amount = Decimal("10")
    balance_after = Decimal("10")


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    workspace = factory.SubFactory(WorkspaceFactory)
    report_type = Report.ReportType.MONTHLY_REPORT
    title = factory.Sequence(lambda n: f"Report {n}")
    status = Report.Status.QUEUED


class MediaKitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaKit

    artist = factory.SubFactory(ArtistFactory)
    workspace = factory.SelfAttribute("artist.workspace")
    title = factory.Sequence(lambda n: f"Media Kit {n}")
    status = MediaKit.Status.DRAFT
