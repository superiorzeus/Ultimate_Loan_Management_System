# Django imports
from django.shortcuts import render
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta

# Django Rest Framework imports
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView, UpdateAPIView
from django.shortcuts import get_object_or_404
from django.db.models import F

# Models imports
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment, PaymentSchedule
from .permissions import IsAdminUser

# Serializers imports
from .serializers import (
    UserSerializer, CustomerProfileSerializer, CustomerDetailSerializer,
    LoanApplicationSerializer, LoanSerializer, LoanTypeSerializer,
    PaymentSerializer, PaymentScheduleSerializer
)

# A new view to render the index.html template.
def index(request):
    return render(request, 'index.html')


# A view for user registration.
class UserRegisterView(APIView):
    # This view does not require authentication.
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        # The request data will contain user fields and customer profile fields.
        # We need to extract them separately.
        
        # Extract user-specific data
        user_data = {
            'username': request.data.get('username'),
            'phone_number': request.data.get('phone_number'),
            'name': request.data.get('name'),
            'password': request.data.get('password'),
        }

        # Extract customer profile-specific data, including files
        profile_data = {
            'national_id': request.data.get('national_id'),
            'email': request.data.get('email'),
            'address': request.data.get('address'),
            'digital_address': request.data.get('digital_address'),
            'national_id_front_scan': request.data.get('national_id_front_scan'),
            'national_id_back_scan': request.data.get('national_id_back_scan'),
        }
        
        # Validate user data first
        user_serializer = UserSerializer(data=user_data)
        if user_serializer.is_valid():
            user = user_serializer.save(is_customer=True, is_approved=False)
            
            # Now validate profile data. We pass the files from request.FILES as well.
            profile_serializer = CustomerProfileSerializer(data=profile_data)
            if profile_serializer.is_valid():
                profile = profile_serializer.save(user=user)
                return Response({
                    "message": "User registered successfully. Your account is pending admin approval.",
                    "user": user_serializer.data,
                    "profile": profile_serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                user.delete()  # Rollback user creation if profile data is invalid.
                return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# A view for user login. It extends DRF's built-in token authentication view.
class LoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        # The serializer handles authentication and token creation.
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        # We use get_or_create to ensure a token always exists for the user.
        # This handles cases where a token might not have been created by the signal.
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'is_admin': user.is_admin,
            'is_customer': user.is_customer,
        })


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
        return self.request.user.customer_profile


# A view for customers to manage their own profile.
class CustomerProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the current user's profile.
        user = request.user
        # We use a detailed serializer to display both user and profile information.
        serializer = CustomerDetailSerializer(user)
        return Response(serializer.data)

    @transaction.atomic
    def put(self, request):
        # This will update both user and profile information.
        user = request.user
        serializer = CustomerDetailSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ViewSet for the LoanType model.
class LoanTypeViewSet(viewsets.ModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAdminUser]


# ViewSet for the LoanApplication model.
class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    # This method ensures that a user can only see and manage their own loan applications.
    def get_queryset(self):
        # Admins can view all applications, customers can only view their own
        if self.request.user.is_admin:
            return LoanApplication.objects.all()
        return LoanApplication.objects.filter(user=self.request.user)

    # This method ensures that the user who submitted the application is set automatically.
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ViewSet for the Loan model.
class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    # This ensures a user can only view their own loans.
    def get_queryset(self):
        # Admins can view all loans
        if self.request.user.is_admin:
            return Loan.objects.all()
        # Customers can only view their own disbursed loans
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
        return Payment.objects.filter(payment_schedule__loan_application__user=self.request.user)

    # This override ensures that only admins can create payments.
    def create(self, request, *args, **kwargs):
        if not request.user.is_admin:
            return Response({'error': 'Only admins can record payments'}, status=status.HTTP_403_FORBIDDEN)

        # When creating a payment, automatically set the recorded_by field
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(recorded_by=self.request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Admin views for managing customers.
class AdminCustomerListView(ListAPIView):
    queryset = User.objects.filter(is_customer=True).order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class ApproveCustomerView(UpdateAPIView):
    queryset = User.objects.filter(is_customer=True)
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    # Set the lookup field to find the user by their primary key.
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Retrieve the user object to be approved.
        instance = self.get_object()
        # Ensure the user is not already approved.
        if instance.is_approved:
            return Response({"message": "User is already approved."}, status=status.HTTP_400_BAD_REQUEST)
        # Mark the user as approved and set the admin who approved them.
        instance.is_approved = True
        instance.customer_profile.approved_by = request.user
        instance.customer_profile.save()
        instance.save()
        return Response({"message": f"User {instance.username} has been approved successfully."}, status=status.HTTP_200_OK)


class ApproveLoanApplicationView(UpdateAPIView):
    queryset = LoanApplication.objects.filter(status='pending')
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Retrieve the application to be approved.
        instance = self.get_object()
        # Change the status to 'approved' and record the approving admin.
        instance.status = 'approved'
        instance.approved_by = request.user
        instance.date_approved = date.today()
        instance.save()
        return Response({"message": f"Application {instance.id} has been approved."}, status=status.HTTP_200_OK)


class DisburseLoanApplicationView(UpdateAPIView):
    queryset = LoanApplication.objects.filter(status='approved')
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Retrieve the application to be disbursed.
        instance = self.get_object()
        
        # Change the status to 'disbursed' and record the disbursement date.
        instance.status = 'disbursed'
        instance.date_disbursed = date.today()
        instance.save()
        
        # Create the Loan instance.
        loan = Loan.objects.create(
            application=instance,
            amount=instance.amount,
            interest_rate=instance.loan_type.interest_rate,
            term_months=instance.loan_type.term_months,
            disbursement_date=instance.date_disbursed,
            end_date=instance.date_disbursed + timedelta(days=30 * instance.loan_type.term_months),
            disbursed=True,
        )

        # Calculate and create the payment schedule.
        loan_type = instance.loan_type
        term_months = loan_type.term_months
        total_interest = (instance.amount * loan_type.interest_rate) / 100
        total_due = float(instance.amount) + float(total_interest)
        monthly_payment = total_due / term_months
        principal_per_month = float(instance.amount) / term_months
        interest_per_month = float(total_interest) / term_months

        for i in range(1, term_months + 1):
            due_date = instance.date_disbursed + timedelta(days=30 * i)
            PaymentSchedule.objects.create(
                loan_application=instance, # Use loan_application instead of loan
                due_date=due_date,
                due_amount=monthly_payment,
                principal_due=principal_per_month,
                interest_due=interest_per_month,
            )

        return Response({"message": f"Loan {loan.id} has been disbursed and payment schedule created."}, status=status.HTTP_200_OK)


class DeclineLoanApplicationView(UpdateAPIView):
    queryset = LoanApplication.objects.filter(status='pending')
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Retrieve the application to be declined.
        instance = self.get_object()
        # Change the status to 'rejected'.
        instance.status = 'rejected'
        instance.save()
        return Response({"message": f"Application {instance.id} has been declined."}, status=status.HTTP_200_OK)
