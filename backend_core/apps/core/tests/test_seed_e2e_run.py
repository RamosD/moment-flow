"""Tests for the `seed_e2e_run` management command (STG-PRE-009)."""

import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.workspaces.models import Workspace

User = get_user_model()


def _run(run_id, password=None, monkeypatch=None):
    if monkeypatch is not None:
        if password is None:
            monkeypatch.delenv("E2E_PASSWORD", raising=False)
        else:
            monkeypatch.setenv("E2E_PASSWORD", password)
    out = StringIO()
    call_command("seed_e2e_run", f"--run-id={run_id}", stdout=out)
    return json.loads(out.getvalue().strip().splitlines()[-1])


@pytest.mark.django_db
class TestSeedE2ERun:
    def test_requires_e2e_password(self, monkeypatch):
        monkeypatch.delenv("E2E_PASSWORD", raising=False)
        with pytest.raises(CommandError):
            call_command("seed_e2e_run", "--run-id=missing-pw")

    def test_creates_namespaced_dataset(self, monkeypatch):
        result = _run("t1", password="probe-pass-1", monkeypatch=monkeypatch)

        assert result["email"] == "e2e-t1@example.local"
        user = User.objects.get(email=result["email"])
        assert user.check_password("probe-pass-1")

        workspace = Workspace.objects.get(id=result["workspace_id"])
        assert workspace.name == "E2E Workspace t1"

        artist = Artist.objects.get(id=result["artist_id"])
        assert artist.workspace_id == workspace.id

        campaign = Campaign.objects.get(id=result["campaign_id"])
        assert campaign.workspace_id == workspace.id
        assert campaign.status == Campaign.Status.ACTIVE

    def test_rerun_with_same_run_id_is_idempotent(self, monkeypatch):
        first = _run("t2", password="probe-pass-1", monkeypatch=monkeypatch)
        second = _run("t2", password="probe-pass-2", monkeypatch=monkeypatch)

        assert first["workspace_id"] == second["workspace_id"]
        assert first["artist_id"] == second["artist_id"]
        assert first["campaign_id"] == second["campaign_id"]
        assert Workspace.objects.filter(name="E2E Workspace t2").count() == 1

        # The password is still updated on rerun (last write wins).
        user = User.objects.get(email=first["email"])
        assert user.check_password("probe-pass-2")

    def test_different_run_ids_never_collide(self, monkeypatch):
        first = _run("t3-a", password="probe-pass-1", monkeypatch=monkeypatch)
        second = _run("t3-b", password="probe-pass-1", monkeypatch=monkeypatch)

        assert first["workspace_id"] != second["workspace_id"]
        assert first["email"] != second["email"]
