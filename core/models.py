from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid

# A custom user manager to handle user creation with username and phone number
class CustomUserManager(BaseUserManager):
    def create_user(self, username, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_customer_approved', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(username, phone_number, password, **extra_fields)

# User Model
# This is our custom user model that uses username for authentication
class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_customer_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone_number', 'name']

    objects = CustomUserManager()

    def __str__(self):
        return self.username
    
    # Check if the user is a full admin with staff and superuser permissions
    @property
    def is_full_admin(self):
        return self.is_staff and self.is_superuser
    
    # Check if the user is an admin
    @property
    def is_admin_only(self):
        return self.is_admin and not self.is_superuser

# Customer Profile Model
# This model holds the additional details for a customer user
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    national_id = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    digital_address = models.CharField(max_length=255)
    national_id_front_scan = models.FileField(upload_to='id_scans/')
    national_id_back_scan = models.FileField(upload_to='id_scans/')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_customers')

    def __str__(self):
        return f"Profile for {self.user.username}"

# Loan Type Model
# This model allows admins to define different loan products
class LoanType(models.Model):
    INTEREST_RATE_CHOICES = [
        ('flat_rate', 'Flat Rate'),
        ('monthly_rate', 'Monthly Rate'),
        ('yearly_rate', 'Yearly Rate'),
    ]
    name = models.CharField(max_length=100)
    interest_rate_type = models.CharField(max_length=50, choices=INTEREST_RATE_CHOICES)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.IntegerField()

    def __str__(self):
        return self.name

# Loan Application Model
# This model stores a customer's loan request.
class LoanApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('rejected', 'Rejected'),
    ]
    
    # A foreign key to the User who submitted the application
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # A foreign key to the type of loan being applied for
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateTimeField(null=True, blank=True)
    date_disbursed = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_applications')

    def __str__(self):
        return f"Loan application by {self.user.username} for {self.loan_type.name}"

# Loan Model
# This model represents an approved loan with its own details.
class Loan(models.Model):
    # A one-to-one relationship with the approved LoanApplication
    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.IntegerField()
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    disbursed = models.BooleanField(default=False)
    disbursement_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Loan for {self.application.user.username} - GHS{self.amount}"

# A new model to store the payment schedule for a loan.
class PaymentSchedule(models.Model):
    # This foreign key links the schedule to a specific, approved loan.
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payment_schedule')
    due_date = models.DateField()
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    principal_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    interest_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_paid = models.BooleanField(default=False)
    date_paid = models.DateField(null=True, blank=True)
    is_overdue = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment due on {self.due_date} for loan {self.loan.pk}"


# Payment Model
# This model stores all the payments made towards a specific loan.
class Payment(models.Model):
    payment_schedule = models.ForeignKey(PaymentSchedule, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    # New field to record which admin processed the payment
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_payments')
    # Using UUIDField for a unique, hard-to-guess transaction ID.
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Payment of GHS{self.amount_paid} for loan {self.payment_schedule.loan.pk}"
