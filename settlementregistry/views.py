from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from settlementregistry.models import (
    SettlementPolicy,
    SettlementPolicyAssignment,
    SettlementPolicyVersion,
)
from settlementregistry.permissions import AdminOnlyAccess
from settlementregistry.serializers import (
    SettlementPolicyAssignmentSerializer,
    SettlementPolicySerializer,
    SettlementPolicyVersionSerializer,
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class SettlementPolicyViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicy.objects.all()
    serializer_class = SettlementPolicySerializer
    lookup_field = "policy_id"
    permission_classes = [AdminOnlyAccess]


class SettlementPolicyVersionViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicyVersion.objects.select_related("policy").all()
    serializer_class = SettlementPolicyVersionSerializer
    lookup_field = "policy_version_id"
    permission_classes = [AdminOnlyAccess]


class SettlementPolicyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicyAssignment.objects.select_related("policy_version").all()
    serializer_class = SettlementPolicyAssignmentSerializer
    lookup_field = "assignment_id"
    permission_classes = [AdminOnlyAccess]
