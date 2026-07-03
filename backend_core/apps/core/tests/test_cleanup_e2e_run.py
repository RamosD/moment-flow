"""Tests for the `cleanup_e2e_run` management command (STG-HARD-006)."""

import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.audit.models import AuditEvent
from apps.campaign_actions.models import CampaignAction
from apps.campaigns.models import Campaign
from apps.catalogue.models import Artist
from apps.integrations_bridge.models import ExternalJobReference
from apps.workspaces.models import Workspace

User = get_user_model()


def _seed(run_id, password="probe-pass", monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setenv("E2E_PASSWORD", password)
    out = StringIO()
    call_command("seed_e2e_run", f"--run-id={run_id}", stdout=out)
    return json.loads(out.getvalue().strip().splitlines()[-1])


def _cleanup(run_id, *, dry_run=False, yes=True, input_answer=None, monkeypatch=None):
    args = [f"--run-id={run_id}"]
    if dry_run:
        args.append("--dry-run")
    if yes:
        args.append("--yes")
    elif input_answer is not None and monkeypatch is not None:
        monkeypatch.setattr("builtins.input", lambda *_a, **_kw: input_answer)
    out = StringIO()
    call_command("cleanup_e2e_run", *args, stdout=out)
    return json.loads(out.getvalue().strip().splitlines()[-1])


@pytest.mark.django_db
class TestCleanupE2ERun:
    def test_rejects_empty_run_id(self):
        with pytest.raises(CommandError):
            call_command("cleanup_e2e_run", "--run-id=", "--yes")

    def test_rejects_whitespace_only_run_id(self):
        with pytest.raises(CommandError):
            call_command("cleanup_e2e_run", "--run-id=   ", "--yes")

    def test_nonexistent_run_id_is_a_no_op_not_an_error(self):
        result = _cleanup("never-seeded-xyz", yes=True)
        assert result["found"] is False
        assert result["workspace_id"] is None

    def test_dry_run_deletes_nothing(self, monkeypatch):
        seeded = _seed("cln-dry", monkeypatch=monkeypatch)
        result = _cleanup("cln-dry", dry_run=True)

        assert result["found"] is True
        assert result["dry_run"] is True
        assert result["workspace_id"] == seeded["workspace_id"]
        assert result["counts"]["campaigns"] == 1
        assert result["counts"]["artists"] == 1
        assert result["counts"]["users"] == 1

        # Nothing was actually deleted.
        assert Workspace.objects.filter(id=seeded["workspace_id"]).exists()
        assert User.objects.filter(email=seeded["email"]).exists()

    def test_real_cleanup_removes_the_full_namespaced_dataset(self, monkeypatch):
        seeded = _seed("cln-real", monkeypatch=monkeypatch)
        workspace = Workspace.objects.get(id=seeded["workspace_id"])
        campaign = Campaign.objects.get(id=seeded["campaign_id"])

        # Extra rows that don't cascade the same way — exercise both paths.
        action = CampaignAction.objects.create(
            workspace=workspace,
            campaign=campaign,
            title="probe action",
            action_type=CampaignAction.ActionType.MANUAL_TASK,
        )
        job = ExternalJobReference.objects.create(
            workspace=workspace,
            job_type=ExternalJobReference.JobType.REPORT_GENERATION,
        )
        audit = AuditEvent.objects.create(
            workspace=workspace, action="probe.audit", actor_type="system"
        )

        result = _cleanup("cln-real", yes=True)

        assert result["found"] is True
        assert result["dry_run"] is False
        assert result["workspace_id"] == seeded["workspace_id"]
        assert result["counts"]["campaign_actions"] == 1
        assert result["counts"]["external_jobs"] == 1
        # >=1, not ==1: create_workspace() itself may already record its own
        # "workspace.created" audit event before the probe one added above.
        assert result["counts"]["audit_events"] >= 1

        assert not Workspace.all_objects.filter(id=seeded["workspace_id"]).exists()
        assert not Campaign.all_objects.filter(id=seeded["campaign_id"]).exists()
        assert not Artist.all_objects.filter(id=seeded["artist_id"]).exists()
        assert not User.objects.filter(email=seeded["email"]).exists()
        assert not CampaignAction.objects.filter(id=action.id).exists()
        # The two SET_NULL relations must be truly gone, not orphaned with a
        # null workspace_id — that would defeat the whole point of this command.
        assert not ExternalJobReference.objects.filter(id=job.id).exists()
        assert not AuditEvent.objects.filter(id=audit.id).exists()

    def test_other_run_id_is_untouched(self, monkeypatch):
        keep = _seed("cln-keep", monkeypatch=monkeypatch)
        _seed("cln-remove", monkeypatch=monkeypatch)

        _cleanup("cln-remove", yes=True)

        assert Workspace.objects.filter(id=keep["workspace_id"]).exists()
        assert User.objects.filter(email=keep["email"]).exists()
        assert Campaign.objects.filter(id=keep["campaign_id"]).exists()
        assert Artist.objects.filter(id=keep["artist_id"]).exists()

    def test_rerun_after_cleanup_reseeds_cleanly(self, monkeypatch):
        first = _seed("cln-reseed", monkeypatch=monkeypatch)
        _cleanup("cln-reseed", yes=True)
        second = _seed("cln-reseed", monkeypatch=monkeypatch)

        assert second["workspace_id"] != first["workspace_id"]
        assert Workspace.objects.filter(id=second["workspace_id"]).exists()
        assert not Workspace.all_objects.filter(id=first["workspace_id"]).exists()

    def test_interactive_confirmation_mismatch_aborts_without_deleting(self, monkeypatch):
        seeded = _seed("cln-confirm-no", monkeypatch=monkeypatch)

        with pytest.raises(CommandError):
            _cleanup(
                "cln-confirm-no",
                yes=False,
                input_answer="not-the-run-id",
                monkeypatch=monkeypatch,
            )

        assert Workspace.objects.filter(id=seeded["workspace_id"]).exists()

    def test_interactive_confirmation_match_deletes(self, monkeypatch):
        seeded = _seed("cln-confirm-yes", monkeypatch=monkeypatch)

        _cleanup(
            "cln-confirm-yes",
            yes=False,
            input_answer="cln-confirm-yes",
            monkeypatch=monkeypatch,
        )

        assert not Workspace.all_objects.filter(id=seeded["workspace_id"]).exists()

    def test_mismatched_ownership_refuses_to_guess(self, monkeypatch):
        run_id = "cln-mismatch"
        # A workspace named like a run-id's, but created by someone else, plus
        # a same-run-id user who never owned it — an artificial collision that
        # should never happen from seed_e2e_run itself, but the command must
        # still refuse rather than delete the wrong workspace.
        other_user = User.objects.create(
            email="unrelated-owner@example.local", full_name="Someone else"
        )
        Workspace.objects.create(
            name=f"E2E Workspace {run_id}", slug=f"e2e-mismatch-slug", created_by=other_user
        )
        User.objects.create(email=f"e2e-{run_id}@example.local", full_name="Run owner")

        with pytest.raises(CommandError):
            _cleanup(run_id, yes=True)
