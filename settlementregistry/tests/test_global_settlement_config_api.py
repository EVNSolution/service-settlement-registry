from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient


class GlobalSettlementConfigApiTests(TestCase):
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

    def test_metadata_returns_sections(self):
        self._authenticate(self.admin_token)
        response = self.client.get("/settlement-config/metadata/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sections", response.data)
        self.assertTrue(response.data["sections"])
        self.assertEqual(response.data["sections"][0]["fields"][0]["key"], "income_tax_rate")

    def test_get_settlement_config_returns_singleton_defaults(self):
        self._authenticate(self.admin_token)

        response = self.client.get("/settlement-config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["singleton_key"], "global")
        self.assertEqual(response.data["income_tax_rate"], "0.0000")
        self.assertIn("meal_allowance", response.data)

    def test_patch_settlement_config_updates_partial_fields(self):
        self._authenticate(self.admin_token)
        response = self.client.patch(
            "/settlement-config/",
            {"income_tax_rate": "0.0330"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["income_tax_rate"], "0.0330")
        self.assertIn("vat_tax_rate", response.data)

    def test_non_admin_cannot_manage_settlement_config(self):
        self._authenticate(self.user_token)

        metadata_response = self.client.get("/settlement-config/metadata/")
        config_response = self.client.get("/settlement-config/")
        patch_response = self.client.patch(
            "/settlement-config/",
            {"income_tax_rate": "0.0330"},
            format="json",
        )

        self.assertEqual(metadata_response.status_code, 403)
        self.assertEqual(config_response.status_code, 403)
        self.assertEqual(patch_response.status_code, 403)
