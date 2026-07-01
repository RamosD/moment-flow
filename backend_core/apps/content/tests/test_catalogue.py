"""Template/pack catalogue: listing, seed, global vs workspace scope."""

import pytest

from apps.content.models import ContentPack, Template
from apps.content.tests.conftest import ws_header

TEMPLATES_URL = "/api/v1/templates/"
PACKS_URL = "/api/v1/content-packs/"


def _results(response):
    data = response.data
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
class TestCatalogueListing:
    def test_templates_are_listable(self, client_for, owner, workspace):
        resp = client_for(owner).get(TEMPLATES_URL, **ws_header(workspace))
        assert resp.status_code == 200
        keys = {t["template_key"] for t in _results(resp)}
        assert {"system_post", "system_media_kit"}.issubset(keys)

    def test_packs_are_listable_with_templates(self, client_for, owner, workspace):
        resp = client_for(owner).get(PACKS_URL, **ws_header(workspace))
        assert resp.status_code == 200
        packs = {p["pack_key"]: p for p in _results(resp)}
        assert {"release_pack", "milestone_pack", "weekly_growth_pack", "auto_media_kit"}.issubset(
            packs.keys()
        )
        # release_pack exposes its template links.
        assert len(packs["release_pack"]["pack_templates"]) == 3


@pytest.mark.django_db
class TestGlobalVsWorkspace:
    def test_workspace_template_only_visible_in_its_workspace(
        self, client_for, owner, workspace, other_owner, other_workspace
    ):
        Template.objects.create(
            workspace=workspace,
            template_key="ws_custom",
            name="WS Custom",
            template_type=Template.TemplateType.POST,
            status=Template.Status.ACTIVE,
        )
        # Visible (global + this workspace) for the owner.
        resp_a = client_for(owner).get(TEMPLATES_URL, **ws_header(workspace))
        keys_a = {t["template_key"] for t in _results(resp_a)}
        assert "ws_custom" in keys_a
        assert "system_post" in keys_a

        # Not visible in another workspace (but globals still are).
        resp_b = client_for(other_owner).get(TEMPLATES_URL, **ws_header(other_workspace))
        keys_b = {t["template_key"] for t in _results(resp_b)}
        assert "ws_custom" not in keys_b
        assert "system_post" in keys_b

    def test_seeded_packs_are_global(self, seeded):
        assert ContentPack.objects.filter(
            pack_key="release_pack", workspace__isnull=True
        ).exists()
