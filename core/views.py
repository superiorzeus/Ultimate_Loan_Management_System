from django.shortcuts import render
from rest_framework import viewsets
from .models import LoanType, LoanApplication, Loan, Payment
from .serializers import LoanTypeSerializer, LoanApplicationSerializer, LoanSerializer, PaymentSerializer
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

# A ViewSet for viewing and managing Loan instances.
class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admins can view all loans
        if self.request.user.is_admin:
            return Loan.objects.all()
        # Customers can only view their own loans
        return Loan.objects.filter(application__user=self.request.user)

# A ViewSet for viewing and managing Payment instances.
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admins can view all payments
        if self.request.user.is_admin:
            return Payment.objects.all()
        # Customers can only view payments for their own loans
        return Payment.objects.filter(loan__application__user=self.request.user)
