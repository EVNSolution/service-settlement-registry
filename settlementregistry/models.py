from datetime import date
from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class SettlementPolicy(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        INACTIVE = "inactive", "inactive"

    policy_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_code = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=Status.choices)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("policy_id",)


class SettlementPolicyVersion(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "draft"
        PUBLISHED = "published", "published"
        RETIRED = "retired", "retired"

    policy_version_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(
        SettlementPolicy,
        on_delete=models.CASCADE,
        related_name="versions",
        db_column="policy_id",
    )
    version_number = models.PositiveIntegerField()
    rule_payload = models.JSONField(default=dict)
    status = models.CharField(max_length=32, choices=Status.choices)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("policy_version_id",)
        constraints = [
            models.UniqueConstraint(
                fields=("policy", "version_number"),
                name="unique_policy_version_number_per_policy",
            )
        ]

    def clean(self):
        errors = {}
        is_published = self.status == self.Status.PUBLISHED
        if is_published and self.published_at is None:
            errors["published_at"] = "published_at is required for published versions."
        if not is_published and self.published_at is not None:
            errors["published_at"] = "published_at must be empty unless the version is published."
        if errors:
            raise ValidationError(errors)


class SettlementPolicyAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        INACTIVE = "inactive", "inactive"

    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_version = models.ForeignKey(
        SettlementPolicyVersion,
        on_delete=models.CASCADE,
        related_name="assignments",
        db_column="policy_version_id",
    )
    company_id = models.UUIDField()
    fleet_id = models.UUIDField()
    effective_start_date = models.DateField()
    effective_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices)

    class Meta:
        ordering = ("assignment_id",)

    def clean(self):
        errors = {}

        if (
            self.policy_version_id
            and self.policy_version.status != SettlementPolicyVersion.Status.PUBLISHED
        ):
            errors["policy_version"] = "Only published policy versions can be assigned."

        if self._has_active_overlap():
            errors["effective_start_date"] = (
                "Assignment interval overlaps an existing active assignment for the same scope."
            )

        if errors:
            raise ValidationError(errors)

    def _has_active_overlap(self) -> bool:
        if self.status != self.Status.ACTIVE or not self.company_id or not self.fleet_id:
            return False

        active_assignments = SettlementPolicyAssignment.objects.filter(
            company_id=self.company_id,
            fleet_id=self.fleet_id,
            status=self.Status.ACTIVE,
        ).exclude(pk=self.pk)

        for assignment in active_assignments:
            if self._intervals_overlap(assignment):
                return True
        return False

    def _intervals_overlap(self, other: "SettlementPolicyAssignment") -> bool:
        current_end = self.effective_end_date or date.max
        other_end = other.effective_end_date or date.max
        return self.effective_start_date < other_end and other.effective_start_date < current_end


class GlobalSettlementConfig(models.Model):
    singleton_key = models.CharField(max_length=32, unique=True, default="global")
    income_tax_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    vat_tax_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    reported_amount_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    national_pension_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    health_insurance_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    medical_insurance_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    employment_insurance_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0000"))
    industrial_accident_insurance_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    special_employment_insurance_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    special_industrial_accident_insurance_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    two_insurance_min_settlement_amount = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal("0.0000"),
    )
    meal_allowance = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0.0000"))

    @classmethod
    def load(cls):
        config, _ = cls.objects.get_or_create(singleton_key="global")
        return config
