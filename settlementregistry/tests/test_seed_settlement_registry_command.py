from datetime import date, datetime, timezone
from importlib import import_module
from unittest.mock import Mock

from django.core.management import call_command
from django.test import TestCase


def _load_models_module(test_case: TestCase):
    try:
        return import_module("settlementregistry.models")
    except ModuleNotFoundError as exc:
        test_case.fail(f"settlementregistry.models module missing: {exc}")


def _load_seed_module(test_case: TestCase):
    try:
        return import_module("settlementregistry.management.commands.seed_settlement_registry")
    except ModuleNotFoundError as exc:
        test_case.fail(f"seed_settlement_registry command module missing: {exc}")


class SeedSettlementRegistryCommandTests(TestCase):
    def test_seed_command_creates_policy_version_and_assignment(self):
        models_module = _load_models_module(self)
        seed_module = _load_seed_module(self)

        call_command("seed_settlement_registry", stdout=Mock())

        policy = models_module.SettlementPolicy.objects.get(policy_id=seed_module.SAMPLE_POLICY_ID)
        version = models_module.SettlementPolicyVersion.objects.get(
            policy_version_id=seed_module.SAMPLE_POLICY_VERSION_ID
        )
        assignment = models_module.SettlementPolicyAssignment.objects.get(
            assignment_id=seed_module.SAMPLE_ASSIGNMENT_ID
        )

        self.assertEqual(policy.policy_code, "fleet-standard")
        self.assertEqual(version.policy_id, policy.policy_id)
        self.assertEqual(version.status, models_module.SettlementPolicyVersion.Status.PUBLISHED)
        self.assertEqual(
            version.published_at,
            datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(str(assignment.company_id), "30000000-0000-0000-0000-000000000001")
        self.assertEqual(str(assignment.fleet_id), "40000000-0000-0000-0000-000000000001")
        self.assertEqual(assignment.effective_start_date, date(2026, 3, 24))
        self.assertIsNone(assignment.effective_end_date)

    def test_seed_command_is_idempotent(self):
        models_module = _load_models_module(self)
        seed_module = _load_seed_module(self)

        call_command("seed_settlement_registry", stdout=Mock())
        assignment = models_module.SettlementPolicyAssignment.objects.get(
            assignment_id=seed_module.SAMPLE_ASSIGNMENT_ID
        )
        assignment.status = models_module.SettlementPolicyAssignment.Status.INACTIVE
        assignment.effective_end_date = date(2026, 3, 31)
        assignment.save(update_fields=["status", "effective_end_date"])

        call_command("seed_settlement_registry", stdout=Mock())

        self.assertEqual(models_module.SettlementPolicy.objects.count(), 1)
        self.assertEqual(models_module.SettlementPolicyVersion.objects.count(), 1)
        self.assertEqual(models_module.SettlementPolicyAssignment.objects.count(), 1)

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, models_module.SettlementPolicyAssignment.Status.ACTIVE)
        self.assertEqual(assignment.effective_start_date, date(2026, 3, 24))
        self.assertIsNone(assignment.effective_end_date)
