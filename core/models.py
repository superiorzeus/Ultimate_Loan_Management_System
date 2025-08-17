from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

# Create your models here.

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
        extra_fields.setdefault('is_approved', True)

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
    is_customer = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone_number']

    objects = CustomUserManager()

    def __str__(self):
        return self.username

# Customer Profile Model
# This model holds the additional details for a customer user
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
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
        ('monthly', 'Monthly'),
        ('flat', 'Flat'),
    ]
    name = models.CharField(max_length=100)
    interest_rate_type = models.CharField(max_length=10, choices=INTEREST_RATE_CHOICES)
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
        ('rejected', 'Rejected'),
    ]
    
    # A foreign key to the User who submitted the application
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # A foreign key to the type of loan being applied for
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loan application by {self.user.username} for {self.loan_type.name}"
