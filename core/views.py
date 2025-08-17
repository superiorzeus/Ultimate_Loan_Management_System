from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import User, CustomerProfile, LoanApplication, Loan, LoanType, Payment
from .serializers import (
    UserSerializer, CustomerProfileSerializer, CustomerDetailSerializer,
    LoanApplicationSerializer, LoanSerializer, LoanTypeSerializer,
    PaymentSerializer
)
from django.shortcuts import render

# A new view to render the index.html template.
def index(request):
    return render(request, 'index.html')


# ViewSet for the User model.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# ViewSet for the CustomerProfile model.
class CustomerProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]

    # This method is used to retrieve the profile of the currently authenticated user.
    def get_object(self):
        return self.request.user.customerprofile


# ViewSet for the LoanType model.
class LoanTypeViewSet(viewsets.ModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer


# ViewSet for the LoanApplication model.
class LoanApplicationViewSet(viewsets.ModelViewSet):
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    # This method ensures that a user can only see and manage their own loan applications.
    def get_queryset(self):
        return LoanApplication.objects.filter(user=self.request.user)

    # This method ensures that the user who submitted the application is set automatically.
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    # We will add a custom action to approve a loan application.
    @action(detail=True, methods=['put'])
    def approve(self, request, pk=None):
        try:
            loan_application = self.get_object()
            if loan_application.status == 'pending':
                loan_application.status = 'approved'
                loan_application.save()
                return Response({'status': 'loan application approved'}, status=status.HTTP_200_OK)
            return Response({'error': 'Loan application is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        except LoanApplication.DoesNotExist:
            return Response({'error': 'Loan application not found'}, status=status.HTTP_404_NOT_FOUND)

    # A custom action to reject a loan application.
    @action(detail=True, methods=['put'])
    def reject(self, request, pk=None):
        try:
            loan_application = self.get_object()
            if loan_application.status == 'pending':
                loan_application.status = 'rejected'
                loan_application.save()
                return Response({'status': 'loan application rejected'}, status=status.HTTP_200_OK)
            return Response({'error': 'Loan application is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        except LoanApplication.DoesNotExist:
            return Response({'error': 'Loan application not found'}, status=status.HTTP_404_NOT_FOUND)


# ViewSet for the Loan model to allow customers to view their disbursed loans and payment history.
class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    # This ensures a customer can only view their own loans.
    def get_queryset(self):
        return Loan.objects.filter(application__user=self.request.user, disbursed=True)

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
