from django.shortcuts import render
from rest_framework import viewsets
from .models import LoanType, LoanApplication
from .serializers import LoanTypeSerializer, LoanApplicationSerializer
from .permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated

# Create your views here.

# A ViewSet for viewing and editing LoanType instances.
# It provides CRUD operations (Create, Read, Update, Delete) for the LoanType model.
class LoanTypeViewSet(viewsets.ModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAdminUser]

# A ViewSet for viewing and managing LoanApplication instances.
class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admins can view all loan applications
        if self.request.user.is_admin:
            return LoanApplication.objects.all()
        # Customers can only view their own loan applications
        return LoanApplication.objects.filter(user=self.request.user)
