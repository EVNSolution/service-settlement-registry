from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from settlementregistry.exceptions import ServiceUnavailableError
from settlementregistry.models import (
    SettlementPolicy,
    SettlementPolicyAssignment,
    SettlementPolicyVersion,
    GlobalSettlementConfig,
)
from settlementregistry.services.source_clients import SourceClients, SourceServiceError, SourceValidationError


class SettlementPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SettlementPolicy
        fields = ("policy_id", "policy_code", "name", "status", "description")
        read_only_fields = ("policy_id",)

    def validate(self, attrs):
        candidate = self.instance or SettlementPolicy()
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class SettlementPolicyVersionSerializer(serializers.ModelSerializer):
    policy_id = serializers.PrimaryKeyRelatedField(
        queryset=SettlementPolicy.objects.all(),
        source="policy",
    )

    class Meta:
        model = SettlementPolicyVersion
        fields = (
            "policy_version_id",
            "policy_id",
            "version_number",
            "rule_payload",
            "status",
            "published_at",
        )
        read_only_fields = ("policy_version_id",)

    def validate(self, attrs):
        candidate = self.instance or SettlementPolicyVersion()
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            errors = dict(exc.message_dict)
            if "policy" in errors:
                errors["policy_id"] = errors.pop("policy")
            raise serializers.ValidationError(errors) from exc
        return attrs


class SettlementPolicyAssignmentSerializer(serializers.ModelSerializer):
    policy_version_id = serializers.PrimaryKeyRelatedField(
        queryset=SettlementPolicyVersion.objects.select_related("policy").all(),
        source="policy_version",
    )

    class Meta:
        model = SettlementPolicyAssignment
        fields = (
            "assignment_id",
            "policy_version_id",
            "company_id",
            "fleet_id",
            "effective_start_date",
            "effective_end_date",
            "status",
        )
        read_only_fields = ("assignment_id",)

    def validate(self, attrs):
        candidate = self.instance or SettlementPolicyAssignment()
        for field, value in attrs.items():
            setattr(candidate, field, value)

        request = self.context.get("request")
        authorization = request.headers.get("Authorization", "") if request else ""

        try:
            SourceClients().validate_company_fleet_scope(
                company_id=str(candidate.company_id),
                fleet_id=str(candidate.fleet_id),
                authorization=authorization,
            )
            candidate.full_clean()
        except SourceValidationError as exc:
            raise serializers.ValidationError({exc.field: [exc.message]}) from exc
        except SourceServiceError as exc:
            raise ServiceUnavailableError(str(exc)) from exc
        except DjangoValidationError as exc:
            errors = dict(exc.message_dict)
            if "policy_version" in errors:
                errors["policy_version_id"] = errors.pop("policy_version")
            raise serializers.ValidationError(errors) from exc
        return attrs


class GlobalSettlementConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettlementConfig
        fields = (
            "singleton_key",
            "income_tax_rate",
            "vat_tax_rate",
            "reported_amount_rate",
            "national_pension_rate",
            "health_insurance_rate",
            "medical_insurance_rate",
            "employment_insurance_rate",
            "industrial_accident_insurance_rate",
            "special_employment_insurance_rate",
            "special_industrial_accident_insurance_rate",
            "two_insurance_min_settlement_amount",
            "meal_allowance",
        )
        read_only_fields = ("singleton_key",)

    def validate(self, attrs):
        candidate = self.instance or GlobalSettlementConfig.load()
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(dict(exc.message_dict)) from exc

        return attrs
