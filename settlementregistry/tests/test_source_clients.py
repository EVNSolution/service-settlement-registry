from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings


class SourceClientsTests(SimpleTestCase):
    @override_settings(ORGANIZATION_MASTER_BASE_URL="http://organization-master-api:8000")
    @patch("settlementregistry.services.source_clients.urlopen")
    def test_validate_company_fleet_scope_forwards_caller_token(self, mocked_urlopen):
        from settlementregistry.services.source_clients import SourceClients

        company_response = MagicMock()
        company_response.__enter__.return_value.read.return_value = (
            b'{"company_id":"30000000-0000-0000-0000-000000000001","name":"Seed Company"}'
        )
        fleet_response = MagicMock()
        fleet_response.__enter__.return_value.read.return_value = (
            b'{"fleet_id":"40000000-0000-0000-0000-000000000001","company_id":"30000000-0000-0000-0000-000000000001","name":"Seed Fleet"}'
        )
        mocked_urlopen.side_effect = [company_response, fleet_response]

        SourceClients().validate_company_fleet_scope(
            company_id="30000000-0000-0000-0000-000000000001",
            fleet_id="40000000-0000-0000-0000-000000000001",
            authorization="Bearer token",
        )

        company_request = mocked_urlopen.call_args_list[0].args[0]
        fleet_request = mocked_urlopen.call_args_list[1].args[0]
        self.assertEqual(company_request.get_header("Authorization"), "Bearer token")
        self.assertEqual(fleet_request.get_header("Authorization"), "Bearer token")

    @override_settings(ORGANIZATION_MASTER_BASE_URL="http://organization-master-api:8000")
    @patch("settlementregistry.services.source_clients.urlopen")
    def test_validate_company_fleet_scope_rejects_unknown_company(self, mocked_urlopen):
        from settlementregistry.services.source_clients import SourceClients, SourceValidationError

        mocked_urlopen.side_effect = HTTPError(
            url="http://organization-master-api:8000/companies/missing/",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

        with self.assertRaises(SourceValidationError) as context:
            SourceClients().validate_company_fleet_scope(
                company_id="30000000-0000-0000-0000-000000000099",
                fleet_id="40000000-0000-0000-0000-000000000001",
                authorization="Bearer token",
            )

        self.assertEqual(context.exception.field, "company_id")

    @override_settings(ORGANIZATION_MASTER_BASE_URL="http://organization-master-api:8000")
    @patch("settlementregistry.services.source_clients.urlopen")
    def test_validate_company_fleet_scope_rejects_unknown_fleet(self, mocked_urlopen):
        from settlementregistry.services.source_clients import SourceClients, SourceValidationError

        company_response = MagicMock()
        company_response.__enter__.return_value.read.return_value = (
            b'{"company_id":"30000000-0000-0000-0000-000000000001","name":"Seed Company"}'
        )
        mocked_urlopen.side_effect = [
            company_response,
            HTTPError(
                url="http://organization-master-api:8000/fleets/missing/",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            ),
        ]

        with self.assertRaises(SourceValidationError) as context:
            SourceClients().validate_company_fleet_scope(
                company_id="30000000-0000-0000-0000-000000000001",
                fleet_id="40000000-0000-0000-0000-000000000099",
                authorization="Bearer token",
            )

        self.assertEqual(context.exception.field, "fleet_id")

    @override_settings(ORGANIZATION_MASTER_BASE_URL="http://organization-master-api:8000")
    @patch("settlementregistry.services.source_clients.urlopen")
    def test_validate_company_fleet_scope_rejects_mismatched_membership(self, mocked_urlopen):
        from settlementregistry.services.source_clients import SourceClients, SourceValidationError

        company_response = MagicMock()
        company_response.__enter__.return_value.read.return_value = (
            b'{"company_id":"30000000-0000-0000-0000-000000000001","name":"Seed Company"}'
        )
        fleet_response = MagicMock()
        fleet_response.__enter__.return_value.read.return_value = (
            b'{"fleet_id":"40000000-0000-0000-0000-000000000001","company_id":"30000000-0000-0000-0000-000000000099","name":"Seed Fleet"}'
        )
        mocked_urlopen.side_effect = [company_response, fleet_response]

        with self.assertRaises(SourceValidationError) as context:
            SourceClients().validate_company_fleet_scope(
                company_id="30000000-0000-0000-0000-000000000001",
                fleet_id="40000000-0000-0000-0000-000000000001",
                authorization="Bearer token",
            )

        self.assertEqual(context.exception.field, "fleet_id")
