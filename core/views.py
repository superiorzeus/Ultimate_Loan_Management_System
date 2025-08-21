# Django imports
import requests
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from datetime import timedelta

# Django Rest Framework imports
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView, UpdateAPIView

# Models imports
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment, PaymentSchedule
from .permissions import IsAdminUser, IsAdminUserOrReadOnly

# Serializers imports
from .serializers import (
    UserSerializer, CustomerProfileSerializer, CustomerDetailSerializer,
    LoanApplicationSerializer, LoanSerializer, LoanTypeSerializer,
    PaymentSerializer, PaymentScheduleSerializer, LoanApplicationApproveSerializer, UserRegisterSerializer,
    CustomerSerializer, SummarySerializer
)

# A new view to render the index.html template.
def index(request):
    """Renders the main index page for the front-end application."""
    return render(request, 'index.html')


# A view for user registration.
class UserRegisterView(APIView):
    """
    Handles user registration by creating a new User and CustomerProfile instance.
    This view does not require authentication.
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user but don't save the profile data yet
            user = serializer.save(is_active=False, is_customer_approved=False)
            
            # Now, handle the customer profile data
            profile_data = {
                'email': request.data.get('email'),
                'national_id': request.data.get('national_id'),
                'address': request.data.get('address'),
                'digital_address': request.data.get('digital_address'),
            }
            # Handle file uploads for the profile
            profile_data['national_id_front_scan'] = request.FILES.get('national_id_front_scan')
            profile_data['national_id_back_scan'] = request.FILES.get('national_id_back_scan')

            # Create the customer profile with the new user
            CustomerProfile.objects.create(user=user, **profile_data)
            
            # If the user is successfully created, generate a token
            token, created = Token.objects.get_or_create(user=user)
            # Return a success response with the token and user details.
            return Response({
                'message': 'Registration successful. Awaiting admin approval.',
                'token': token.key,
                'user_id': user.pk,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        # If the serializer is not valid, return the validation errors.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# A view to handle user registration form.
@csrf_exempt
def register_view(request):
    """
    Handles user registration via a form submission and sends data to the DRF API.
    """
    if request.method == 'POST':
        # Prepare the data for the API. Separating text fields and file fields is best practice.
        text_data = {
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
            'name': request.POST.get('name'),
            'phone_number': request.POST.get('phone_number'),
            'email': request.POST.get('email'),
            'national_id': request.POST.get('national_id'),
            'address': request.POST.get('address'),
            'digital_address': request.POST.get('digital_address'),
        }

        # The files dictionary will handle the file uploads.
        # It's crucial to use request.FILES here.
        file_data = {
            'national_id_front_scan': request.FILES.get('national_id_front_scan'),
            'national_id_back_scan': request.FILES.get('national_id_back_scan'),
        }

        # Make a POST request to your existing API endpoint
        url = 'http://127.0.0.1:8000/api/users/register/'
        
        try:
            # Use `data` for text fields and `files` for file uploads
            # requests.post will automatically set the correct headers for multipart/form-data
            response = requests.post(url, data=text_data, files=file_data)
            
            if response.status_code == 201:
                return render(request, 'registration_form.html', {
                    'success_message': 'Registration successful. Your account is pending admin approval.'
                })
            else:
                try:
                    error_data = response.json()
                    # Flatten the error messages for display
                    error_message = ''
                    for field, errors in error_data.items():
                        error_message += f"{field}: {', '.join(errors)} "
                    return render(request, 'registration_form.html', {'error_message': error_message.strip()})
                except (json.JSONDecodeError, KeyError):
                    return render(request, 'registration_form.html', {
                        'error_message': 'An unknown error occurred during registration.'
                    })
        except requests.exceptions.RequestException as e:
            return render(request, 'registration_form.html', {
                'error_message': f'Request failed: {e}'
            })

    return render(request, 'registration_form.html', {})


# LoginView using ObtainAuthToken
class LoginView(ObtainAuthToken):
    """
    Handles user authentication and token generation.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        is_admin = user.is_staff
        return Response({
            'token': token.key,
            'is_admin': is_admin
        })


# Simple view for logout.
@csrf_exempt
def logout_and_redirect(request):
    logout(request)
    return redirect('index')


# ViewSet for a customer to view their own profile.
class CustomerProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for customers to view and update their own profile.
    Admins can also view and update any customer profile.
    """
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [IsAuthenticated]

    # This method ensures that a customer can only see their own profile.
    def get_queryset(self):
        # Admins can see all profiles.
        if self.request.user.is_staff:
            return CustomerProfile.objects.all()
        # Customers can only see their own profile.
        return CustomerProfile.objects.filter(user=self.request.user)

    # This method ensures that a customer can only update their own profile.
    def get_object(self):
        # If the user is an admin, they can access any profile by its ID.
        if self.request.user.is_staff:
            queryset = self.get_queryset()
            obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        else:
            # If the user is a customer, they can only access their own profile.
            obj = get_object_or_404(CustomerProfile, user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj


# A ViewSet for managing loan applications.
class LoanApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan applications.
    Admins can create, view, and manage all loan applications.
    Customers can only create and view their own applications.
    """
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters the loan application queryset based on the user's role.
        """
        # Admins can view all loan applications.
        if self.request.user.is_staff:
            return LoanApplication.objects.all()
        # Customers can only view their own loan applications.
        return LoanApplication.objects.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Custom create method that sets the user on the loan application.
        """
        # The user is automatically set to the currently authenticated user
        if not self.request.user.is_staff:
            serializer.validated_data['user'] = self.request.user
        serializer.save()

    @action(detail=True, methods=['post'], url_path='approve')
    def approve_application(self, request, pk=None):
        """
        Action to approve a loan application.
        Only accessible by staff users.
        """
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."},
                            status=status.HTTP_403_FORBIDDEN)
        
        try:
            loan_application = self.get_object()
            if loan_application.status == 'pending':
                loan_application.status = 'approved'
                loan_application.save()
                return Response({"status": "Loan application approved successfully."},
                                status=status.HTTP_200_OK)
            return Response({"detail": "This application cannot be approved."},
                            status=status.HTTP_400_BAD_REQUEST)
        except LoanApplication.DoesNotExist:
            return Response({"detail": "Loan application not found."},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject_application(self, request, pk=None):
        """
        Action to reject a loan application.
        Only accessible by staff users.
        """
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."},
                            status=status.HTTP_403_FORBIDDEN)
        
        try:
            loan_application = self.get_object()
            if loan_application.status == 'pending':
                loan_application.status = 'rejected'
                loan_application.save()
                return Response({"status": "Loan application rejected successfully."},
                                status=status.HTTP_200_OK)
            return Response({"detail": "This application cannot be rejected."},
                            status=status.HTTP_400_BAD_REQUEST)
        except LoanApplication.DoesNotExist:
            return Response({"detail": "Loan application not found."},
                            status=status.HTTP_404_NOT_FOUND)


# A ViewSet for managing loan-related operations.
class LoanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loans.
    Admins can create, view, update, and delete loans.
    Customers can only view their own loans.
    """
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    # This permission ensures that only admins can create, update, and delete loans.
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]

    def get_queryset(self):
        """
        Filters the loans queryset based on the user's role.
        """
        # Admins can view all loans.
        if self.request.user.is_staff:
            return Loan.objects.all()
        # Customers can only view loans related to their own applications.
        # The correct filter is 'application__user' because the Loan model links to the LoanApplication model.
        return Loan.objects.filter(application__user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Custom create method that generates a payment schedule after a loan is created.
        """
        # Ensure the user is an admin
        if not self.request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        loan = serializer.save()
        create_payment_schedule(loan)

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Custom update method that allows admins to update a loan and also generate a payment schedule
        if one doesn't exist.
        """
        # Ensure the user is an admin
        if not self.request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        loan = serializer.save()
        # If the loan is approved and doesn't have a schedule yet, create one
        if loan.is_approved and not loan.payment_schedule.exists():
            create_payment_schedule(loan)


# A ViewSet for managing payment-related operations.
class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    Admins can create and view all payments.
    Customers can only view payments related to their loans.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    # This permission ensures only authenticated users can access this viewset.
    # The actual access control is handled in get_queryset().
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters the payments queryset based on the user's role.
        """
        # Admins can view all payments.
        if self.request.user.is_staff:
            return Payment.objects.all()
        # Customers can only view payments related to their loans.
        # This filter correctly links payments to the user's loan applications.
        return Payment.objects.filter(payment_schedule__loan__application__user=self.request.user)
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Custom create method that ensures the payment is tied to a valid schedule,
        updates the schedule, and sets the admin user who processed the payment.
        """
        # The user must be an admin to record payments.
        if not self.request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        # Get the payment schedule object from the validated data.
        payment_schedule = serializer.validated_data.get('payment_schedule')

        # Check if a payment has already been recorded for this schedule.
        # This prevents double-processing of payments.
        if payment_schedule.is_paid:
            return Response({"detail": "This payment has already been recorded."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate the amount of principal and interest to be paid off based on the payment amount.
        amount_to_pay = serializer.validated_data.get('amount_paid')
        remaining_interest = payment_schedule.interest_due
        remaining_principal = payment_schedule.principal_due
        
        # Pay off interest first.
        interest_paid = min(amount_to_pay, remaining_interest)
        principal_paid = 0

        if amount_to_pay > remaining_interest:
            principal_paid = amount_to_pay - interest_paid

        # Update the payment schedule with the new remaining amounts.
        payment_schedule.interest_due = remaining_interest - interest_paid
        payment_schedule.principal_due = remaining_principal - principal_paid

        # Check if the payment amount is enough to pay off the full scheduled amount.
        # Use a small tolerance for float comparison to avoid issues.
        if payment_schedule.principal_due <= 0.01 and payment_schedule.interest_due <= 0.01:
            payment_schedule.is_paid = True
            payment_schedule.date_paid = timezone.now().date()
        
        payment_schedule.save()

        # Save the payment with the user who processed it.
        serializer.save(recorded_by=self.request.user)


# A ViewSet for a customer to manage their user details and profile.
class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage user and customer profile details for the authenticated user.
    """
    serializer_class = CustomerDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # A customer can only view and edit their own user object.
        return User.objects.filter(pk=self.request.user.pk)

    def retrieve(self, request, *args, **kwargs):
        # Ensure a customer can only retrieve their own profile.
        if int(self.kwargs['pk']) != request.user.pk:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Returns a complete dashboard view for the authenticated customer.
        """
        # Get the user and their associated customer profile
        user = request.user
        try:
            profile = CustomerProfile.objects.get(user=user)
        except CustomerProfile.DoesNotExist:
            profile = None # In case the profile hasn't been created yet

        # Get all loan applications for this user
        loan_applications = LoanApplication.objects.filter(customer=user)

        # Serialize the data
        user_serializer = UserSerializer(user)
        profile_serializer = CustomerProfileSerializer(profile) if profile else None
        loan_applications_serializer = LoanApplicationSerializer(loan_applications, many=True)

        return Response({
            'user': user_serializer.data,
            'profile': profile_serializer.data if profile_serializer else None,
            'loan_applications': loan_applications_serializer.data
        })
    

# A ViewSet for admins to manage all customers and their details.
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admins to manage user accounts.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser] # Only admins can manage users.


# A ViewSet for admins to manage loan types.
class LoanTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admins to manage loan types.
    """
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAdminUser]


# A ViewSet for both admins and customers to view payment schedules.
class PaymentScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing payment schedules. Admins can see all schedules.
    Customers can only see schedules for their own loans.
    """
    queryset = PaymentSchedule.objects.all()
    serializer_class = PaymentScheduleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Filters the payment schedules based on the user's role.
        """
        # Admins can view all payment schedules.
        if self.request.user.is_staff:
            return PaymentSchedule.objects.all()
        # Customers can only view schedules for their own loans.
        return PaymentSchedule.objects.filter(loan__application__customer=self.request.user)
    

# A view to render a simple login form and handle authentication
@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(reverse('dashboard'))
        else:
            return render(request, 'login_form.html', {
                'error_message': 'Invalid username or password.'
            })
    return render(request, 'login_form.html', {})

@login_required
def dashboard_view(request):
    """
    Renders the dashboard page for authenticated users.
    """
    context = {
        'user': request.user
    }
    return render(request, 'dashboard.html', context)

# A View for Admins to create customers
class AdminCreateCustomerView(APIView):
    """
    API view for an admin to create a new customer account directly.
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # The data contains all user and customer profile fields
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user and profile
            user = serializer.save(is_active=True, is_customer_approved=True)
            return Response({
                "message": f"Customer '{user.username}' created successfully.",
                "user_id": user.pk
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# A view to render the add customer page
@login_required
def add_customer_view(request):
    """Renders the page for an admin to add a new customer."""
    if not request.user.is_staff:
        # Redirect non-admin users to the dashboard
        return redirect(reverse('dashboard'))
    return render(request, 'add_customer.html')

# A view to list all customers (non-staff, non-superuser).
# This is a good practice to separate concerns from the main UserViewSet.
class CustomerListView(ListAPIView):
    """
    API view to list all non-admin customer users.
    """
    queryset = User.objects.filter(is_staff=False, is_superuser=False)
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

@login_required
@user_passes_test(lambda u: u.is_staff)
def customer_detail_view(request, username):
    """
    Renders a detailed view of a specific customer for admin users.
    """
    # Use get_object_or_404 to handle cases where the username does not exist
    customer_user = get_object_or_404(User, username=username)

    # Get related data
    try:
        customer_profile = CustomerProfile.objects.get(user=customer_user)
    except CustomerProfile.DoesNotExist:
        customer_profile = None

    # Corrected line: 'created_at' is the correct field for sorting by submission date
    loan_applications = LoanApplication.objects.filter(user=customer_user).order_by('-created_at')
    loans = Loan.objects.filter(application__user=customer_user).order_by('-disbursement_date')
    payments = Payment.objects.filter(payment_schedule__loan__application__user=customer_user).order_by('-payment_date')

    context = {
        'customer_user': customer_user,
        'customer_profile': customer_profile,
        'loan_applications': loan_applications,
        'loans': loans,
        'payments': payments,
    }

    return render(request, 'customer_detail.html', context)

class SummaryViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    API endpoint that provides a summary of key metrics for the dashboard.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SummarySerializer

    def list(self, request, *args, **kwargs):
        total_loans = Loan.objects.count()
        # Corrected line: Filter for loans with a balance of 0
        paid_loans = Loan.objects.filter(balance=0).count()
        pending_applications = LoanApplication.objects.filter(status='pending').count()

        summary_data = {
            "total_loans": total_loans,
            "paid_loans": paid_loans,
            "pending_applications": pending_applications,
        }
        
        serializer = self.get_serializer(summary_data)
        return Response(serializer.data)

@login_required
def create_loan_application_view(request):
    """
    Renders the form for creating a new loan application.
    """
    context = {
        'user': request.user
    }
    return render(request, 'loan_application_form.html', context)