from datetime import date, datetime, timezone
from importlib import import_module
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase


def _load_models_module(test_case: TestCase):
    try:
        return import_module("settlementregistry.models")
    except ModuleNotFoundError as exc:
        test_case.fail(f"settlementregistry.models module missing: {exc}")


class SettlementRegistryModelTests(TestCase):
    def _create_policy(self, models_module, policy_code: str = "fleet-standard"):
        return models_module.SettlementPolicy.objects.create(
            policy_code=policy_code,
            name=policy_code.replace("-", " ").title(),
            status=models_module.SettlementPolicy.Status.ACTIVE,
        )

    def _create_version(
        self,
        models_module,
        *,
        policy=None,
        version_number: int = 1,
        status: str | None = None,
        published_at=None,
    ):
        policy = policy or self._create_policy(models_module, policy_code=f"policy-{version_number}")
        version_status = status or models_module.SettlementPolicyVersion.Status.DRAFT
        return models_module.SettlementPolicyVersion.objects.create(
            policy=policy,
            version_number=version_number,
            status=version_status,
            rule_payload={"base_rate": 1000 + version_number},
            published_at=published_at,
        )

    def test_initial_migration_file_exists(self):
        migration_path = Path(__file__).resolve().parents[1] / "migrations" / "0001_initial.py"

        self.assertTrue(migration_path.exists())

    def test_settlement_policy_can_be_created_and_loaded(self):
        models_module = _load_models_module(self)

        policy = self._create_policy(models_module)
        policy.description = "Default fleet settlement policy."
        policy.save(update_fields=["description"])

        loaded = models_module.SettlementPolicy.objects.get(policy_id=policy.policy_id)

        self.assertEqual(loaded.policy_code, "fleet-standard")
        self.assertEqual(loaded.name, "Fleet Standard")
        self.assertEqual(loaded.status, models_module.SettlementPolicy.Status.ACTIVE)

    def test_policy_version_belongs_to_policy(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module, policy_code="night-shift")
        version = self._create_version(models_module, policy=policy)

        self.assertEqual(version.policy_id, policy.policy_id)
        self.assertEqual(policy.versions.get().policy_version_id, version.policy_version_id)

    def test_policy_version_number_is_unique_per_policy(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module)
        self._create_version(models_module, policy=policy)

        duplicate = models_module.SettlementPolicyVersion(
            policy=policy,
            version_number=1,
            status=models_module.SettlementPolicyVersion.Status.DRAFT,
            rule_payload={"base_rate": 1200},
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_published_policy_version_requires_published_at(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module)
        version = models_module.SettlementPolicyVersion(
            policy=policy,
            version_number=2,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            rule_payload={"base_rate": 1000},
            published_at=None,
        )

        with self.assertRaises(ValidationError) as context:
            version.full_clean()

        self.assertIn("published_at", context.exception.message_dict)

    def test_non_published_policy_version_cannot_set_published_at(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module)
        version = models_module.SettlementPolicyVersion(
            policy=policy,
            version_number=3,
            status=models_module.SettlementPolicyVersion.Status.DRAFT,
            rule_payload={"base_rate": 1000},
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )

        with self.assertRaises(ValidationError) as context:
            version.full_clean()

        self.assertIn("published_at", context.exception.message_dict)

    def test_policy_assignment_requires_company_and_fleet_together(self):
        models_module = _load_models_module(self)
        version = self._create_version(
            models_module,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        assignment = models_module.SettlementPolicyAssignment(
            policy_version=version,
            company_id=uuid4(),
            fleet_id=None,
            effective_start_date=date(2026, 3, 24),
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_policy_assignment_rejects_non_published_policy_version(self):
        models_module = _load_models_module(self)
        version = self._create_version(models_module)
        assignment = models_module.SettlementPolicyAssignment(
            policy_version=version,
            company_id=uuid4(),
            fleet_id=uuid4(),
            effective_start_date=date(2026, 3, 24),
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError) as context:
            assignment.full_clean()

        self.assertIn("policy_version", context.exception.message_dict)

    def test_policy_assignment_allows_open_ended_effective_period(self):
        models_module = _load_models_module(self)
        version = self._create_version(
            models_module,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        assignment = models_module.SettlementPolicyAssignment(
            policy_version=version,
            company_id=uuid4(),
            fleet_id=uuid4(),
            effective_start_date=date(2026, 3, 24),
            effective_end_date=None,
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        assignment.full_clean()
        assignment.save()

        self.assertIsNone(assignment.effective_end_date)

    def test_policy_assignment_allows_half_open_boundary_between_assignments(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module, policy_code="half-open")
        version_one = self._create_version(
            models_module,
            policy=policy,
            version_number=1,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        version_two = self._create_version(
            models_module,
            policy=policy,
            version_number=2,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc),
        )
        company_id = uuid4()
        fleet_id = uuid4()
        models_module.SettlementPolicyAssignment.objects.create(
            policy_version=version_one,
            company_id=company_id,
            fleet_id=fleet_id,
            effective_start_date=date(2026, 3, 24),
            effective_end_date=date(2026, 4, 1),
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        second_assignment = models_module.SettlementPolicyAssignment(
            policy_version=version_two,
            company_id=company_id,
            fleet_id=fleet_id,
            effective_start_date=date(2026, 4, 1),
            effective_end_date=None,
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        second_assignment.full_clean()

    def test_policy_assignment_rejects_overlapping_active_assignment_for_same_scope(self):
        models_module = _load_models_module(self)
        policy = self._create_policy(models_module, policy_code="overlap-check")
        version_one = self._create_version(
            models_module,
            policy=policy,
            version_number=1,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        version_two = self._create_version(
            models_module,
            policy=policy,
            version_number=2,
            status=models_module.SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc),
        )
        company_id = uuid4()
        fleet_id = uuid4()
        models_module.SettlementPolicyAssignment.objects.create(
            policy_version=version_one,
            company_id=company_id,
            fleet_id=fleet_id,
            effective_start_date=date(2026, 3, 24),
            effective_end_date=None,
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )
        overlapping_assignment = models_module.SettlementPolicyAssignment(
            policy_version=version_two,
            company_id=company_id,
            fleet_id=fleet_id,
            effective_start_date=date(2026, 3, 25),
            effective_end_date=None,
            status=models_module.SettlementPolicyAssignment.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            overlapping_assignment.full_clean()
