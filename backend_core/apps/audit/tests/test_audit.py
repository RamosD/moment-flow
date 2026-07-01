"""AuditEvent service, privacy hashing, read-only admin and integration hooks."""

import pytest
from django.contrib import admin as djadmin
from rest_framework.test import APIRequestFactory

from apps.audit.admin import AuditEventAdmin
from apps.audit.models import AuditEvent
from apps.audit.services import record_audit_event


@pytest.mark.django_db
class TestRecordAuditEvent:
    def test_actor_type_defaults_to_user_when_actor_given(self, workspace, owner):
        event = record_audit_event(
            action="thing.done",
            workspace=workspace,
            actor_user=owner,
            entity_type="thing",
            entity_id="abc",
        )
        assert event.actor_type == AuditEvent.ActorType.USER
        assert event.entity_id == "abc"

    def test_actor_type_defaults_to_system_without_actor(self, workspace):
        event = record_audit_event(action="job.ran", workspace=workspace)
        assert event.actor_type == AuditEvent.ActorType.SYSTEM

    def test_request_ip_and_ua_are_hashed_not_clear(self, workspace, owner):
        request = APIRequestFactory().post(
            "/x", HTTP_USER_AGENT="Mozilla/5.0", REMOTE_ADDR="203.0.113.7"
        )
        event = record_audit_event(
            action="x.y", workspace=workspace, actor_user=owner, request=request
        )
        # Never store the raw IP; SHA-256 hex is 64 chars.
        assert event.ip_address_hash and event.ip_address_hash != "203.0.113.7"
        assert len(event.ip_address_hash) == 64
        assert event.user_agent_hash and len(event.user_agent_hash) == 64


@pytest.mark.django_db
class TestAuditAdminReadOnly:
    def test_admin_is_read_only(self):
        admin_obj = AuditEventAdmin(AuditEvent, djadmin.site)
        assert admin_obj.has_add_permission(None) is False
        assert admin_obj.has_change_permission(None) is False
        assert admin_obj.has_delete_permission(None) is False


@pytest.mark.django_db
class TestAuditIntegration:
    def test_workspace_created_is_audited(self, workspace):
        # The ``workspace`` fixture goes through create_workspace().
        assert AuditEvent.objects.filter(
            action="workspace.created", workspace=workspace
        ).exists()

    def test_credit_grant_and_consume_are_audited(self, workspace):
        from apps.billing.services import consume_credits, grant_credits

        grant_credits(workspace, 50)
        consume_credits(workspace, 20)
        assert AuditEvent.objects.filter(
            action="credits.granted", workspace=workspace
        ).exists()
        assert AuditEvent.objects.filter(
            action="credits.consumed", workspace=workspace
        ).exists()

    def test_idempotent_grant_audited_once(self, workspace):
        from apps.billing.services import grant_credits

        grant_credits(workspace, 10, idempotency_key="g1")
        grant_credits(workspace, 10, idempotency_key="g1")
        assert (
            AuditEvent.objects.filter(
                action="credits.granted", workspace=workspace
            ).count()
            == 1
        )
