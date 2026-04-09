from datetime import date, datetime, timezone
from uuid import UUID

from django.core.management.base import BaseCommand

from settlementregistry.models import (
    SettlementPolicy,
    SettlementPolicyAssignment,
    SettlementPolicyVersion,
    GlobalSettlementConfig,
)

SAMPLE_POLICY_ID = UUID("83000000-0000-0000-0000-000000000001")
SAMPLE_POLICY_VERSION_ID = UUID("83000000-0000-0000-0000-000000000002")
SAMPLE_ASSIGNMENT_ID = UUID("83000000-0000-0000-0000-000000000003")
SAMPLE_COMPANY_ID = UUID("30000000-0000-0000-0000-000000000001")
SAMPLE_FLEET_ID = UUID("40000000-0000-0000-0000-000000000001")


class Command(BaseCommand):
    help = "Seed deterministic settlement registry bootstrap data."

    def handle(self, *args, **options):
        policy = SettlementPolicy.objects.update_or_create(
            policy_id=SAMPLE_POLICY_ID,
            defaults={
                "policy_code": "fleet-standard",
                "name": "Fleet Standard",
                "status": SettlementPolicy.Status.ACTIVE,
                "description": "Default seeded settlement policy.",
            },
        )[0]
        version = SettlementPolicyVersion.objects.update_or_create(
            policy_version_id=SAMPLE_POLICY_VERSION_ID,
            defaults={
                "policy": policy,
                "version_number": 1,
                "rule_payload": {"base_rate": 1000, "incentive_rate": 120},
                "status": SettlementPolicyVersion.Status.PUBLISHED,
                "published_at": datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
            },
        )[0]
        SettlementPolicyAssignment.objects.update_or_create(
            assignment_id=SAMPLE_ASSIGNMENT_ID,
            defaults={
                "policy_version": version,
                "company_id": SAMPLE_COMPANY_ID,
                "fleet_id": SAMPLE_FLEET_ID,
                "effective_start_date": date(2026, 3, 24),
                "effective_end_date": None,
                "status": SettlementPolicyAssignment.Status.ACTIVE,
            },
        )
        GlobalSettlementConfig.objects.get_or_create(singleton_key="global")
        self.stdout.write(self.style.SUCCESS("Seeded settlement registry bootstrap data."))
