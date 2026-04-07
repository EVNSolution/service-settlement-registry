from django.urls import include, path
from rest_framework.routers import SimpleRouter

from settlementregistry.views import (
    HealthView,
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
    path("health/", HealthView.as_view()),
]
