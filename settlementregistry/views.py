from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from settlementregistry.models import (
    CompanyFleetPricingTable,
    SettlementPolicy,
    SettlementPolicyAssignment,
    SettlementPolicyVersion,
    GlobalSettlementConfig,
)
from settlementregistry.permissions_navigation import require_nav_access
from settlementregistry.permissions import AdminOnlyAccess
from settlementregistry.settlement_config_metadata import SETTLEMENT_CONFIG_METADATA
from settlementregistry.serializers import (
    CompanyFleetPricingTableSerializer,
    SettlementPolicyAssignmentSerializer,
    SettlementPolicySerializer,
    SettlementPolicyVersionSerializer,
    GlobalSettlementConfigSerializer,
)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class SettlementConfigMetadataView(APIView):
    permission_classes = [AdminOnlyAccess]

    def get(self, request):
        require_nav_access(request, "settlements")
        return Response(SETTLEMENT_CONFIG_METADATA)


class SettlementConfigView(APIView):
    permission_classes = [AdminOnlyAccess]

    def get(self, request):
        require_nav_access(request, "settlements")
        config = GlobalSettlementConfig.load()
        serializer = GlobalSettlementConfigSerializer(config)
        return Response(serializer.data)

    def patch(self, request):
        require_nav_access(request, "settlements")
        config = GlobalSettlementConfig.load()
        serializer = GlobalSettlementConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SettlementPolicyViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicy.objects.all()
    serializer_class = SettlementPolicySerializer
    lookup_field = "policy_id"
    permission_classes = [AdminOnlyAccess]

    def list(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().retrieve(request, *args, **kwargs)


class SettlementPolicyVersionViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicyVersion.objects.select_related("policy").all()
    serializer_class = SettlementPolicyVersionSerializer
    lookup_field = "policy_version_id"
    permission_classes = [AdminOnlyAccess]

    def list(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().retrieve(request, *args, **kwargs)


class SettlementPolicyAssignmentViewSet(viewsets.ModelViewSet):
    queryset = SettlementPolicyAssignment.objects.select_related("policy_version").all()
    serializer_class = SettlementPolicyAssignmentSerializer
    lookup_field = "assignment_id"
    permission_classes = [AdminOnlyAccess]

    def list(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        require_nav_access(request, "settlements")
        return super().retrieve(request, *args, **kwargs)


class CompanyFleetPricingTableViewSet(viewsets.ModelViewSet):
    queryset = CompanyFleetPricingTable.objects.all()
    serializer_class = CompanyFleetPricingTableSerializer
    lookup_field = "pricing_table_id"
    permission_classes = [AdminOnlyAccess]

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        fleet_id = self.request.query_params.get("fleet_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if fleet_id:
            queryset = queryset.filter(fleet_id=fleet_id)
        return queryset

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_nav_access(request, "settlements")
