from django.urls import include, path
from rest_framework.routers import SimpleRouter

from settlementregistry.views import (
    HealthView,
    SettlementConfigMetadataView,
    SettlementConfigView,
    SettlementPolicyAssignmentViewSet,
    SettlementPolicyVersionViewSet,
    SettlementPolicyViewSet,
)

router = SimpleRouter()
router.register("policies", SettlementPolicyViewSet, basename="policy")
router.register("policy-versions", SettlementPolicyVersionViewSet, basename="policy-version")
router.register("policy-assignments", SettlementPolicyAssignmentViewSet, basename="policy-assignment")

urlpatterns = [
    path("", include(router.urls)),
    path("settlement-config/metadata/", SettlementConfigMetadataView.as_view()),
    path("settlement-config/", SettlementConfigView.as_view()),
    path("health/", HealthView.as_view()),
]
