# core/views.py

# Django imports
import requests
import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from decimal import Decimal
import uuid

# Django Rest Framework imports
from rest_framework import viewsets, status, permissions, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView, UpdateAPIView, ListCreateAPIView
from rest_framework.filters import SearchFilter

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
    """
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer

    # Add this custom action to create a unique URL for the list view.
    @action(detail=False, methods=['get'], url_path='list-applications')
    def list_applications(self, request):
        applications = self.get_queryset()
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Custom action to approve a loan application.
        """
        loan_application = self.get_object()
        if loan_application.status == 'pending':
            loan_application.status = 'approved'
            loan_application.save()
            return Response({'status': 'Application approved successfully.'})
        return Response({'status': 'Application cannot be approved.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='disburse')
    def disburse(self, request, pk=None):
        """
        Custom action to disburse an approved loan and create the payment schedule.
        """
        loan_application = self.get_object()

        if loan_application.status != 'approved':
            return Response({'detail': 'This application is not approved and cannot be disbursed.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Find the existing Loan object
                loan = get_object_or_404(Loan, application=loan_application)

                # Update the Loan status
                loan.disbursed = True
                loan.disbursement_date = timezone.now().date()
                loan.save()

                # Update the application status to disbursed
                loan_application.status = 'disbursed'
                loan_application.date_disbursed = timezone.now()
                loan_application.save()
                
                # Payment schedule creation logic (remains the same)
                principal = loan_application.amount
                interest_rate = loan_application.loan_type.interest_rate
                term_months = loan_application.loan_type.term_months
                interest_rate_type = loan_application.loan_type.interest_rate_type
                
                # Calculate total payable amount based on interest rate type
                if interest_rate_type in ['flat', 'flat_rate']:
                    total_interest = (principal * interest_rate) / 100
                    total_payable = principal + total_interest
                elif interest_rate_type in ['monthly', 'monthly_rate', 'yearly', 'yearly_rate']:
                    total_interest = (principal * (interest_rate / 100) * (term_months / 12))
                    total_payable = principal + total_interest
                else:
                    return Response({'detail': f'Unsupported interest rate type: {interest_rate_type}'}, status=status.HTTP_400_BAD_REQUEST)
                
                monthly_payment = total_payable / term_months
                current_date = timezone.now().date()
                for month in range(term_months):
                    current_date += relativedelta(months=1)
                    PaymentSchedule.objects.create(
                        loan=loan,
                        due_date=current_date,
                        due_amount=monthly_payment,
                        principal_due=monthly_payment,
                        interest_due=0,
                        is_paid=False
                    )
        
        except Exception as e:
            return Response({'detail': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': 'Loan disbursed and payment schedule created successfully.'})


# A ViewSet for managing loans.
class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Admins can view all loans
        if self.request.user.is_staff:
            return Loan.objects.all()
        # Customers can only view their own loans
        return Loan.objects.filter(application__user=self.request.user)

    @transaction.atomic
    @action(detail=True, methods=['post'], url_path='disburse')
    def disburse(self, request, pk=None):
        """
        Action to disburse a loan and generate its payment schedule.
        Only accessible by staff users.
        """
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."},
                            status=status.HTTP_403_FORBIDDEN)
        
        try:
            loan = self.get_object()
            loan_application = loan.loan_application
            loan_type = loan_application.loan_type

            # Check if the loan has already been disbursed
            if loan.disbursement_date:
                return Response({"detail": "This loan has already been disbursed."},
                                status=status.HTTP_400_BAD_REQUEST)
            
            # Update loan's status and disbursement date
            loan.status = 'active'
            loan.disbursement_date = timezone.now()
            
            total_amount = float(loan_application.amount)
            interest_rate = float(loan_type.interest_rate) / 100
            term_months = loan_type.term_months
            
            # --- Payment Schedule Calculation Logic based on your rules ---
            if loan_type.interest_rate_type == 'flat_rate':
                total_interest = total_amount * interest_rate
                total_payable = total_amount + total_interest
                monthly_installment = total_payable / term_months
                
                # Generate a schedule for each month
                for i in range(term_months):
                    PaymentSchedule.objects.create(
                        loan=loan,
                        due_date=loan.disbursement_date + timedelta(days=(i + 1) * 30),
                        amount_due=monthly_installment
                    )

            elif loan_type.interest_rate_type == 'monthly_rate':
                # Simple monthly interest
                monthly_rate = interest_rate
                remaining_balance = total_amount
                
                for i in range(term_months):
                    interest_for_month = remaining_balance * monthly_rate
                    # To calculate a fixed monthly payment for simple interest:
                    # Let's assume a simple amortization where principal is evenly spread
                    principal_for_month = total_amount / term_months
                    monthly_installment = principal_for_month + interest_for_month
                    
                    PaymentSchedule.objects.create(
                        loan=loan,
                        due_date=loan.disbursement_date + timedelta(days=(i + 1) * 30),
                        amount_due=monthly_installment
                    )
                    remaining_balance -= principal_for_month

            elif loan_type.interest_rate_type == 'yearly_rate':
                # Convert yearly rate to monthly rate and apply simple interest
                monthly_rate = (interest_rate / 12)
                remaining_balance = total_amount
                
                for i in range(term_months):
                    interest_for_month = remaining_balance * monthly_rate
                    principal_for_month = total_amount / term_months
                    monthly_installment = principal_for_month + interest_for_month
                    
                    PaymentSchedule.objects.create(
                        loan=loan,
                        due_date=loan.disbursement_date + timedelta(days=(i + 1) * 30),
                        amount_due=monthly_installment
                    )
                    remaining_balance -= principal_for_month

            loan.save()
            return Response({"status": "Loan disbursed and payment schedule generated."},
                            status=status.HTTP_200_OK)

        except Loan.DoesNotExist:
            return Response({"detail": "Loan not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": f"An error occurred: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    def create(self, request, *args, **kwargs):
        """
        Custom create method that ensures the payment is tied to a valid schedule,
        updates the schedule, and sets the admin user who processed the payment.
        """
        # The user must be an admin to record payments.
        if not request.user.is_staff:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        # The serializer now handles all the payment processing logic,
        # including the loan balance update and finding the payment schedule.
        # We just need to ensure the serializer is valid and then save it.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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


# This ViewSet is for the API endpoint that serves the list of loan types to the public form.
class LoanTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer

# A view for managing loan types for admins
class LoanTypeManageView(ListCreateAPIView):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()


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

    # --- START OF ADDED CODE ---
    # Handle POST request for updating customer status
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            customer_user.is_customer_approved = True
            messages.success(request, f'Customer {customer_user.name} has been approved successfully.')
        elif action == 'activate':
            customer_user.is_active = True
            messages.success(request, f'Account for {customer_user.name} has been activated.')
        elif action == 'deactivate':
            customer_user.is_active = False
            messages.warning(request, f'Account for {customer_user.name} has been deactivated.')
        customer_user.save()
        # --- START OF CORRECTED LINE ---
        # Redirect back to the same page with the updated status using the correct URL name
        return redirect('customer-detail', username=customer_user.username)
        # --- END OF CORRECTED LINE ---
    # --- END OF ADDED CODE ---

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
    Renders the form for creating a new loan application and handles form submission.
    """
    customers = User.objects.filter(customer_profile__isnull=False, is_active=True).order_by('username')
    
    if request.method == 'POST':
        api_data = {
            'user': request.POST.get('user'),
            'loan_type': request.POST.get('loan_type'),
            'amount': request.POST.get('amount')
        }
        
        api_url = 'http://127.0.0.1:8000/api/loan-applications/'
        
        # --- START OF UPDATED CODE ---
        try:
            user_token = Token.objects.get(user=request.user)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Token {user_token.key}'
            }
        except Token.DoesNotExist:
            messages.error(request, 'Authentication token not found. Please log in again.')
            return redirect('login')
        
        response = requests.post(api_url, data=json.dumps(api_data), headers=headers)

        if response.status_code == 201:
            messages.success(request, 'Loan application submitted successfully!')
            return redirect('dashboard')
        else:
            # Handle API errors more gracefully
            try:
                errors = response.json()
            except json.JSONDecodeError:
                # Fallback for non-JSON responses
                errors = {'detail': [f'API Error: {response.text}']}
            
            # This is where we ensure the errors variable is a dictionary with a list value.
            # Example: {"detail": ["Authentication credentials were not provided."]}
            # If the API returns a simple string, we wrap it in a dictionary and a list.
            if isinstance(errors.get('detail'), str):
                 errors['detail'] = [errors['detail']]

            loan_types = LoanType.objects.all()
            context = {
                'user': request.user,
                'errors': errors,
                'loan_types': loan_types,
                'customers': customers
            }
            messages.error(request, 'There was an error submitting your application. Please check the form.')
            return render(request, 'loan_application_form.html', context)
    
    loan_types = LoanType.objects.all()
    context = {
        'user': request.user,
        'loan_types': loan_types,
        'customers': customers
    }
    return render(request, 'loan_application_form.html', context)


# Loan detail view
@login_required
def loan_detail_view(request, pk):
    loan = get_object_or_404(Loan, application__pk=pk)
    context = {'loan': loan}
    return render(request, 'loan_detail.html', context)

# Loan application detail view
# @login_required
# def loan_application_detail_view(request, pk):
#     """
#     Renders the loan application detail page.
#     The details are fetched by the frontend JavaScript.
#     """
#     return render(request, 'loan_application_detail.html', {'user': request.user})
@login_required
def loan_application_detail_view(request, pk):
    """
    Renders the loan application detail page or serves JSON for API calls.
    """
    loan_application = get_object_or_404(LoanApplication, pk=pk)

    # Check if the request is for JSON data (an API call)
    if request.headers.get('accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        serializer = LoanApplicationSerializer(loan_application)
        return JsonResponse(serializer.data, safe=False)

    # Otherwise, render the HTML page as normal
    return render(request, 'loan_application_detail.html', {'user': request.user})

# A view to render the add_payment.html template
@login_required
def add_payment_view(request):
    """
    Renders the add payment form page and passes the user's auth token.
    """
    try:
        # Attempt to get the auth token for the current user
        token = Token.objects.get(user=request.user).key
    except Token.DoesNotExist:
        # Handle case where a token doesn't exist for the user
        token = None
    
    context = {
        'auth_token': token
    }
    return render(request, 'add_payment.html', context)

# A view to search for loans by customer name or loan ID.
class LoanSearchAPIView(ListAPIView):
    """
    API view to search for loans by customer name or loan ID.
    """
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['id', 'application__user__name', 'application__user__username']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('q', None)
        if query:
            # Try to get the loan by its primary key
            try:
                # We use an exact lookup for the primary key
                loan = queryset.get(pk=int(query))
                return queryset.filter(pk=loan.pk)
            except (ValueError, Loan.DoesNotExist):
                # If the query is not a number or the loan is not found,
                # fall back to searching other fields using icontains
                queryset = queryset.filter(
                    Q(application__user__name__icontains=query) |
                    Q(application__user__username__icontains=query)
                )
        return queryset.filter(disbursed=True)

# A view to process payments for a specific loan.
class PaymentAPIView(APIView):
    """
    API view to process payments for a specific loan.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        loan_id = request.data.get('loan_pk')
        amount_paid = request.data.get('amount_paid')
        
        if not loan_id or not amount_paid:
            return Response({"error": "Loan ID and amount are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            loan = Loan.objects.get(pk=loan_id, disbursed=True)
        except Loan.DoesNotExist:
            return Response({"error": "Loan not found or not disbursed."}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate payment amount
        amount_paid = Decimal(amount_paid)
        if amount_paid <= 0:
            return Response({"error": "Payment amount must be a positive number."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update loan balance
        loan.balance -= amount_paid
        
        # Create a new payment record
        Payment.objects.create(
            loan=loan,
            amount_paid=amount_paid,
            recorded_by=request.user
        )
        
        # Save the updated loan
        loan.save()
        
        return Response({"message": "Payment processed successfully!", "new_balance": loan.balance}, status=status.HTTP_201_CREATED)