# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect

# Django Rest Framework imports
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView, UpdateAPIView

# Models imports
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment, PaymentSchedule
from .permissions import IsAdminUser

# Serializers imports
from .serializers import (
    UserSerializer, CustomerProfileSerializer, CustomerDetailSerializer,
    LoanApplicationSerializer, LoanSerializer, LoanTypeSerializer,
    PaymentSerializer, PaymentScheduleSerializer, LoanApplicationApproveSerializer, UserRegisterSerializer,
    CustomerSerializer
)

# A new view to render the index.html template.
def index(request):
    """Renders the main index page for the front-end application."""
    return render(request, 'index.html')


# A view for user registration.
class UserRegisterView(APIView):
    """
    Handles user registration by creating a new User instance.
    This view does not require authentication.
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Pass the request data to the UserSerializer for validation and creation.
        # This will create both a User and a CustomerProfile.
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # If the user is successfully created, we can generate a token for them
            # so they can be logged in automatically after registration.
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

# @csrf_exempt
# @api_view(['POST'])
# def logout_view(request):
#     """
#     View to log out the user.
#     """
#     if request.user.is_authenticated:
#         request.user.auth_token.delete()
#         logout(request)
#         return Response({'success': 'Successfully logged out.'}, status=status.HTTP_200_OK)
#     return Response({'error': 'Not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)

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


# A ViewSet for a customer to apply for a loan.
class LoanApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan applications.
    Customers can create and view their own applications.
    Admins can see all applications.
    """
    queryset = LoanApplication.objects.all()
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    # This method ensures that customers can only view their own applications.
    def get_queryset(self):
        # Admins can see all loan applications.
        if self.request.user.is_staff:
            return LoanApplication.objects.all()
        # Customers can only see their own loan applications.
        return LoanApplication.objects.filter(customer=self.request.user)

    # This method automatically assigns the current user as the customer for the application.
    def perform_create(self, serializer):
        # Automatically set the 'customer' field to the current authenticated user.
        serializer.save(customer=self.request.user)


# A ViewSet for admins to manage loans.
class LoanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admins to manage all loans.
    Admins can approve applications, disburse loans, and view all loan details.
    """
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAdminUser] # Only admins can manage loans.

    # This is a custom action to handle the disbursement of a loan.
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    @transaction.atomic
    def disburse(self, request, pk=None):
        """Disburse a loan and generate its payment schedule."""
        loan = self.get_object()

        # Check if the loan has already been disbursed.
        if loan.disbursed:
            return Response({"error": "This loan has already been disbursed."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Set the loan's disbursement status and date.
        loan.disbursed = True
        loan.disbursement_date = timezone.now().date()
        loan.save()

        # Generate the payment schedule for the loan.
        self.generate_payment_schedule(loan)

        # Return the updated loan details.
        serializer = self.get_serializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def generate_payment_schedule(self, loan):
        """
        Generates a monthly payment schedule for a loan based on its terms.
        """
        # Calculate the monthly interest rate from the annual rate.
        monthly_interest_rate = loan.interest_rate / 12 / 100
        # Calculate the monthly payment using the loan amortization formula.
        if monthly_interest_rate > 0:
            monthly_payment = (loan.amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate)**-loan.term_months)
        else:
            monthly_payment = loan.amount / loan.term_months
            
        # Get the start date for the schedule.
        start_date = loan.disbursement_date
        current_balance = loan.amount

        for month in range(1, loan.term_months + 1):
            # Calculate the interest due for the current month.
            interest_due = current_balance * monthly_interest_rate
            # Calculate the principal due for the current month.
            principal_due = monthly_payment - interest_due
            # Update the remaining balance.
            current_balance -= principal_due
            
            # The next due date is one month after the previous one.
            due_date = start_date + timedelta(days=30 * month)

            # Create the PaymentSchedule entry.
            PaymentSchedule.objects.create(
                loan=loan,
                due_date=due_date,
                due_amount=monthly_payment,
                principal_due=principal_due,
                interest_due=interest_due,
            )

        # Update the loan's end date.
        loan.end_date = due_date
        loan.balance = loan.amount # Initialize balance
        loan.save()
        
    def get_queryset(self):
        """
        This method filters the loans based on the user's role.
        Admins see all loans. Customers only see loans related to their applications.
        """
        # If the user is an admin, show all loans.
        if self.request.user.is_staff:
            return Loan.objects.all()
        # Otherwise, show loans associated with the current customer's applications.
        return Loan.objects.filter(application__customer=self.request.user)

# A ViewSet for admins to manage payments and for customers to view their payment history.
class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing payments.
    Admins can create and view payments for any loan.
    Customers can only view their own payment history.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    # This permission ensures that admins can create payments, but customers can only read.
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters the payments queryset based on the user's role.
        """
        # Admins can view all payments.
        if self.request.user.is_staff:
            return Payment.objects.all()
        # Customers can only view payments related to their own loans.
        return Payment.objects.filter(payment_schedule__loan__application__customer=self.request.user)

    def perform_create(self, serializer):
        """
        Custom create method that records a payment, updates the loan balance,
        and marks the payment schedule as paid.
        """
        serializer.is_valid(raise_exception=True)

        # Retrieve the payment schedule and its corresponding loan
        payment_schedule_id = serializer.validated_data.get('payment_schedule').id
        payment_schedule = get_object_or_404(PaymentSchedule, pk=payment_schedule_id)
        loan = payment_schedule.loan

        # Check if the amount paid is sufficient to cover the due amount
        if serializer.validated_data.get('amount_paid') < payment_schedule.due_amount:
            return Response({"error": "Amount paid is less than the scheduled due amount."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the loan balance
        loan.balance = F('balance') - serializer.validated_data.get('amount_paid')
        loan.save()

        # Mark the payment schedule as paid
        payment_schedule.is_paid = True
        payment_schedule.date_paid = timezone.now()
        payment_schedule.save()

        # The recorded_by field is set by the backend
        serializer.validated_data['recorded_by'] = self.request.user
        
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
