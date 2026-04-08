from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from settlementregistry.models import (
    SettlementPolicy,
    SettlementPolicyAssignment,
    SettlementPolicyVersion,
)
from settlementregistry.services.source_clients import SourceValidationError


class SettlementRegistryApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_token = self._issue_token("admin", allowed_nav_keys=["settlements"])
        self.user_token = self._issue_token("user")

    def _issue_token(self, role: str, *, allowed_nav_keys: list[str] | None = None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "email": f"{role}@example.com",
            "role": role,
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "jti": str(uuid4()),
            "type": "access",
        }
        if allowed_nav_keys is not None:
            payload["allowed_nav_keys"] = allowed_nav_keys
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def _authenticate(self, token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _create_policy(self, policy_code: str = "fleet-standard") -> SettlementPolicy:
        return SettlementPolicy.objects.create(
            policy_code=policy_code,
            name=policy_code.replace("-", " ").title(),
            status=SettlementPolicy.Status.ACTIVE,
        )

    def _create_version(
        self,
        *,
        policy: SettlementPolicy | None = None,
        version_number: int = 1,
        status: str = SettlementPolicyVersion.Status.DRAFT,
        published_at=None,
    ) -> SettlementPolicyVersion:
        policy = policy or self._create_policy(policy_code=f"policy-{version_number}")
        return SettlementPolicyVersion.objects.create(
            policy=policy,
            version_number=version_number,
            status=status,
            rule_payload={"base_rate": 1000 + version_number},
            published_at=published_at,
        )

    def _create_assignment(
        self,
        *,
        policy_version: SettlementPolicyVersion,
        company_id: str = "30000000-0000-0000-0000-000000000001",
        fleet_id: str = "40000000-0000-0000-0000-000000000001",
        effective_start_date: str = "2026-03-24",
        effective_end_date: str | None = None,
        status: str = SettlementPolicyAssignment.Status.ACTIVE,
    ) -> SettlementPolicyAssignment:
        return SettlementPolicyAssignment.objects.create(
            policy_version=policy_version,
            company_id=company_id,
            fleet_id=fleet_id,
            effective_start_date=effective_start_date,
            effective_end_date=effective_end_date,
            status=status,
        )

    def _policy_payload(self):
        return {
            "policy_code": "registry-standard",
            "name": "Registry Standard",
            "status": "active",
            "description": "Default settlement policy.",
        }

    def _version_payload(self, policy_id: str):
        return {
            "policy_id": policy_id,
            "version_number": 1,
            "rule_payload": {"base_rate": 1000},
            "status": "draft",
            "published_at": None,
        }

    def _assignment_payload(self, policy_version_id: str):
        return {
            "policy_version_id": policy_version_id,
            "company_id": "30000000-0000-0000-0000-000000000001",
            "fleet_id": "40000000-0000-0000-0000-000000000001",
            "effective_start_date": "2026-03-24",
            "effective_end_date": None,
            "status": "active",
        }

    def test_health_endpoint_responds_publicly(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    def test_unauthenticated_policy_list_returns_401_shape(self):
        response = self.client.get("/policies/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})

    def test_authenticated_non_admin_cannot_manage_policies(self):
        policy = self._create_policy()
        self._authenticate(self.user_token)

        list_response = self.client.get("/policies/")
        create_response = self.client.post("/policies/", self._policy_payload(), format="json")
        patch_response = self.client.patch(
            f"/policies/{policy.policy_id}/",
            {"name": "Changed"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(patch_response.status_code, 403)

    def test_admin_can_crud_policies(self):
        self._authenticate(self.admin_token)

        create_response = self.client.post("/policies/", self._policy_payload(), format="json")
        self.assertEqual(create_response.status_code, 201)
        policy_id = create_response.data["policy_id"]

        detail_response = self.client.get(f"/policies/{policy_id}/")
        self.assertEqual(detail_response.status_code, 200)

        patch_response = self.client.patch(
            f"/policies/{policy_id}/",
            {"description": "Updated description."},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["description"], "Updated description.")

    def test_authenticated_non_admin_cannot_manage_policy_versions(self):
        policy = self._create_policy()
        version = self._create_version(policy=policy)
        self._authenticate(self.user_token)

        list_response = self.client.get("/policy-versions/")
        create_response = self.client.post(
            "/policy-versions/",
            self._version_payload(str(policy.policy_id)),
            format="json",
        )
        patch_response = self.client.patch(
            f"/policy-versions/{version.policy_version_id}/",
            {"rule_payload": {"base_rate": 1100}},
            format="json",
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(patch_response.status_code, 403)

    def test_admin_can_crud_policy_versions(self):
        policy = self._create_policy()
        self._authenticate(self.admin_token)

        create_response = self.client.post(
            "/policy-versions/",
            self._version_payload(str(policy.policy_id)),
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        policy_version_id = create_response.data["policy_version_id"]

        detail_response = self.client.get(f"/policy-versions/{policy_version_id}/")
        self.assertEqual(detail_response.status_code, 200)

        patch_response = self.client.patch(
            f"/policy-versions/{policy_version_id}/",
            {"rule_payload": {"base_rate": 1200}},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["rule_payload"]["base_rate"], 1200)

    def test_authenticated_non_admin_cannot_manage_policy_assignments(self):
        version = self._create_version(
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        assignment = self._create_assignment(policy_version=version)
        self._authenticate(self.user_token)

        list_response = self.client.get("/policy-assignments/")
        create_response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version.policy_version_id)),
            format="json",
        )
        patch_response = self.client.patch(
            f"/policy-assignments/{assignment.assignment_id}/",
            {"status": "inactive"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(patch_response.status_code, 403)

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_admin_can_crud_policy_assignments(self, mock_validate_scope):
        version = self._create_version(
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        self._authenticate(self.admin_token)

        create_response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version.policy_version_id)),
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        assignment_id = create_response.data["assignment_id"]
        mock_validate_scope.assert_called_once()

        detail_response = self.client.get(f"/policy-assignments/{assignment_id}/")
        self.assertEqual(detail_response.status_code, 200)

        patch_response = self.client.patch(
            f"/policy-assignments/{assignment_id}/",
            {"status": "inactive"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["status"], "inactive")

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_assignment_create_rejects_non_published_version(self, mock_validate_scope):
        version = self._create_version()
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version.policy_version_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})
        self.assertIn("policy_version_id", response.data["details"])
        mock_validate_scope.assert_called_once()

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_assignment_create_rejects_overlapping_interval(self, mock_validate_scope):
        policy = self._create_policy(policy_code="overlap-api")
        version_one = self._create_version(
            policy=policy,
            version_number=1,
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        version_two = self._create_version(
            policy=policy,
            version_number=2,
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc),
        )
        self._create_assignment(policy_version=version_one)
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version_two.policy_version_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})
        self.assertIn("effective_start_date", response.data["details"])
        mock_validate_scope.assert_called_once()

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_assignment_create_rejects_unknown_company_scope(self, mock_validate_scope):
        version = self._create_version(
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        mock_validate_scope.side_effect = SourceValidationError(
            field="company_id",
            message="Referenced company does not exist.",
        )
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version.policy_version_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("company_id", response.data["details"])

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_assignment_create_rejects_mismatched_company_fleet_membership(self, mock_validate_scope):
        version = self._create_version(
            status=SettlementPolicyVersion.Status.PUBLISHED,
            published_at=datetime(2026, 3, 24, 9, 0, tzinfo=timezone.utc),
        )
        mock_validate_scope.side_effect = SourceValidationError(
            field="fleet_id",
            message="Referenced fleet does not belong to the referenced company.",
        )
        self._authenticate(self.admin_token)

        response = self.client.post(
            "/policy-assignments/",
            self._assignment_payload(str(version.policy_version_id)),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("fleet_id", response.data["details"])

    def test_admin_without_settlements_nav_key_cannot_list_policies(self):
        self._authenticate(self._issue_token("admin", allowed_nav_keys=[]))

        response = self.client.get("/policies/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})

    def test_admin_without_settlements_nav_key_cannot_read_policy_detail(self):
        policy = self._create_policy()
        self._authenticate(self._issue_token("admin", allowed_nav_keys=[]))

        response = self.client.get(f"/policies/{policy.policy_id}/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(set(response.data.keys()), {"code", "message", "details"})
