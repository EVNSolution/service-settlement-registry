import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class SourceClientError(Exception):
    """Base error for upstream organization source calls."""


@dataclass
class SourceValidationError(SourceClientError):
    field: str
    message: str

    def __str__(self) -> str:
        return self.message


class SourceServiceError(SourceClientError):
    """Raised when the upstream service is unavailable or returns malformed data."""


class SourceClients:
    def _build_url(self, path: str) -> str:
        return f"{settings.ORGANIZATION_MASTER_BASE_URL.rstrip('/')}{path}"

    def _request_json(self, *, url: str, authorization: str, missing_field: str, missing_message: str):
        headers = {"Accept": "application/json"}
        if authorization:
            headers["Authorization"] = authorization

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                raise SourceValidationError(field=missing_field, message=missing_message) from exc
            raise SourceServiceError(f"Upstream request failed: {url}") from exc
        except (URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceServiceError(f"Upstream request failed: {url}") from exc

        if not isinstance(payload, dict):
            raise SourceServiceError(f"Upstream request failed: {url}")
        return payload

    def validate_company_fleet_scope(self, *, company_id: str, fleet_id: str, authorization: str) -> None:
        company_payload = self._request_json(
            url=self._build_url(f"/companies/{company_id}/"),
            authorization=authorization,
            missing_field="company_id",
            missing_message="Referenced company does not exist.",
        )
        fleet_payload = self._request_json(
            url=self._build_url(f"/fleets/{fleet_id}/"),
            authorization=authorization,
            missing_field="fleet_id",
            missing_message="Referenced fleet does not exist.",
        )

        if str(company_payload.get("company_id")) != company_id:
            raise SourceServiceError("Upstream request failed: malformed company payload.")
        if str(fleet_payload.get("fleet_id")) != fleet_id:
            raise SourceServiceError("Upstream request failed: malformed fleet payload.")
        if str(fleet_payload.get("company_id")) != company_id:
            raise SourceValidationError(
                field="fleet_id",
                message="Referenced fleet does not belong to the referenced company.",
            )
