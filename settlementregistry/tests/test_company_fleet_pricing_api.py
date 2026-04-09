from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from settlementregistry.services.source_clients import SourceValidationError


class CompanyFleetPricingApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_token = self._issue_token("admin", allowed_nav_keys=["settlements"])
        self.user_token = self._issue_token("user")
        self.company_id = "30000000-0000-0000-0000-000000000001"
        self.fleet_id = "40000000-0000-0000-0000-000000000001"

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

    def _payload(self, **overrides):
        payload = {
            "company_id": self.company_id,
            "fleet_id": self.fleet_id,
            "box_sale_unit_price": "1000.00",
            "box_purchase_unit_price": "800.00",
            "overtime_fee": "20000.00",
        }
        payload.update(overrides)
        return payload

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_can_create_company_fleet_pricing_table(self, mock_validate_scope):
        self._authenticate(self.admin_token)

        response = self.client.post("/pricing-tables/", self._payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["company_id"], self.company_id)
        self.assertEqual(response.data["fleet_id"], self.fleet_id)
        self.assertEqual(response.data["box_sale_unit_price"], "1000.00")
        self.assertEqual(response.data["box_purchase_unit_price"], "800.00")
        self.assertEqual(response.data["overtime_fee"], "20000.00")
        mock_validate_scope.assert_called_once()

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_can_list_filter_and_patch_company_fleet_pricing_tables(self, mock_validate_scope):
        self._authenticate(self.admin_token)
        create_response = self.client.post("/pricing-tables/", self._payload(), format="json")
        self.assertEqual(create_response.status_code, 201)
        pricing_table_id = create_response.data["pricing_table_id"]

        list_response = self.client.get(
            "/pricing-tables/",
            {"company_id": self.company_id, "fleet_id": self.fleet_id},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["pricing_table_id"], pricing_table_id)

        patch_response = self.client.patch(
            f"/pricing-tables/{pricing_table_id}/",
            {"overtime_fee": "25000.00"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.data["overtime_fee"], "25000.00")
        self.assertEqual(mock_validate_scope.call_count, 2)

    def test_non_admin_cannot_manage_company_fleet_pricing_tables(self):
        self._authenticate(self.user_token)

        list_response = self.client.get("/pricing-tables/")
        create_response = self.client.post("/pricing-tables/", self._payload(), format="json")

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(create_response.status_code, 403)

    @patch("settlementregistry.services.source_clients.SourceClients.validate_company_fleet_scope")
    def test_create_rejects_invalid_company_fleet_scope(self, mock_validate_scope):
        mock_validate_scope.side_effect = SourceValidationError(
            field="fleet_id",
            message="Referenced fleet does not belong to the referenced company.",
        )
        self._authenticate(self.admin_token)

        response = self.client.post("/pricing-tables/", self._payload(), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("fleet_id", response.data["details"])
