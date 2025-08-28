from rest_framework import serializers
from .models import User, CustomerProfile, LoanApplication, Loan, Payment, LoanType, PaymentSchedule
from django.db import transaction
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# A simple serializer for the CustomerProfile model.
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = '__all__'

# A new serializer for user registration that handles all fields directly.
# A new serializer for user registration that handles all fields directly.
class UserRegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    national_id = serializers.CharField(write_only=True)
    address = serializers.CharField(write_only=True)
    digital_address = serializers.CharField(write_only=True)
    # The file fields are now required.
    national_id_front_scan = serializers.FileField(write_only=True)
    national_id_back_scan = serializers.FileField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'phone_number', 'name', 'password',
            'email', 'national_id', 'address', 'digital_address', 
            'national_id_front_scan', 'national_id_back_scan'
        ]
        extra_kwargs = {'password': {'write_only': True}}
    
    @transaction.atomic
    def create(self, validated_data):
        # Pop the fields that belong to the CustomerProfile model
        profile_data = {
            'email': validated_data.pop('email'),
            'national_id': validated_data.pop('national_id'),
            'address': validated_data.pop('address'),
            'digital_address': validated_data.pop('digital_address'),
            'national_id_front_scan': validated_data.pop('national_id_front_scan'),
            'national_id_back_scan': validated_data.pop('national_id_back_scan'),
        }

        # Create the User object with the remaining data
        user = User.objects.create_user(
            username=validated_data['username'],
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        
        # Create the CustomerProfile linked to the new user
        CustomerProfile.objects.create(user=user, **profile_data)
        
        return user


# A serializer for the LoanType model.
class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = '__all__'

# A serializer for the Payment model.
class PaymentSerializer(serializers.ModelSerializer):
    # This field is for writing only and links to the Loan via the payment schedule.
    # It allows you to pass a loan_pk from the front end.
    loan_pk = serializers.PrimaryKeyRelatedField(
        queryset=Loan.objects.all(),
        write_only=True
    )

    class Meta:
        model = Payment
        fields = ['id', 'amount_paid', 'payment_date', 'recorded_by', 'transaction_id', 'loan_pk']
        read_only_fields = ['id', 'recorded_by', 'transaction_id']

    @transaction.atomic
    def create(self, validated_data):
        """
        Handles the creation of a Payment and updates the related Loan and PaymentSchedule.
        This method contains all the business logic for payment processing.
        """
        # Retrieve the loan object using the provided loan_pk
        loan = get_object_or_404(Loan, pk=validated_data.pop('loan_pk').pk)
        
        # Get the amount paid, which is already a Decimal due to the model field type
        amount_paid = validated_data.get('amount_paid')

        # Get the first unpaid payment schedule for the loan
        payment_schedule = PaymentSchedule.objects.filter(loan=loan, is_paid=False).first()
        
        if not payment_schedule:
            raise serializers.ValidationError({"detail": "No pending payment schedule found for this loan."})

        # Calculate interest and principal paid
        remaining_interest = payment_schedule.interest_due
        interest_paid = min(amount_paid, remaining_interest)
        
        principal_paid = Decimal('0.0')
        if amount_paid > remaining_interest:
            principal_paid = amount_paid - interest_paid

        # Update the payment schedule with the new remaining amounts.
        payment_schedule.interest_due -= interest_paid
        payment_schedule.principal_due -= principal_paid

        # Update the loan balance
        loan.balance -= Decimal(amount_paid)
        
        # Mark payment schedule as paid if the full amount is covered
        if payment_schedule.principal_due <= Decimal('0.01') and payment_schedule.interest_due <= Decimal('0.01'):
            payment_schedule.is_paid = True
            payment_schedule.date_paid = timezone.now().date()
        
        # Save both the updated loan and payment schedule
        payment_schedule.save()
        loan.save()
        
        # Create the Payment instance and link it to the schedule and user
        payment = Payment.objects.create(
            payment_schedule=payment_schedule,
            amount_paid=amount_paid,
            payment_date=validated_data.get('payment_date'),
            recorded_by=self.context['request'].user,
            transaction_id=uuid.uuid4()
        )
        
        return payment

# A new serializer for the PaymentSchedule model. This is used to display the full payment plan.
class PaymentScheduleSerializer(serializers.ModelSerializer):
    # Use a nested serializer to show the actual payments made against a scheduled entry.
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentSchedule
        fields = ['id', 'due_date', 'due_amount', 'is_paid', 'payments']
        read_only_fields = ['is_paid']

# A new serializer for recording a payment.
# This serializer is used specifically for the PaymentViewSet's create action
# to accept 'payment_schedule' and 'amount_paid' fields.
class LoanPaymentSerializer(serializers.ModelSerializer):
    payment_schedule = serializers.PrimaryKeyRelatedField(queryset=PaymentSchedule.objects.all())
    
    class Meta:
        model = Payment
        fields = ['payment_schedule', 'amount_paid']
        
# A serializer for the Loan model. It now includes the PaymentSchedule.
class LoanSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='application.user.name', read_only=True)
    loan_type_name = serializers.CharField(source='application.loan_type.loan_type_name', read_only=True)
    
    # New computed field to return the remaining term
    remaining_term = serializers.SerializerMethodField()
    
    class Meta:
        model = Loan
        # Removed 'id' from fields, as 'application' is the primary key
        fields = ['application', 'customer_name', 'loan_type_name', 'amount', 'interest_rate', 'term_months', 'start_date', 'end_date', 'balance', 'disbursed', 'disbursement_date', 'remaining_term']

    def get_remaining_term(self, obj):
        if obj.disbursed and obj.disbursement_date:
            today = date.today()
            # Use relativedelta to calculate the difference in months
            delta = relativedelta(obj.end_date, today)
            # The remaining term is the sum of full years and months
            return delta.years * 12 + delta.months
        return 0


# A serializer for the LoanApplication model.
class LoanApplicationSerializer(serializers.ModelSerializer):
    # This read-only field gets the user's name from the related User model
    user_name = serializers.CharField(source='user.name', read_only=True)
    # This read-only field gets the loan type name from the related LoanType model
    loan_type_name = serializers.CharField(source='loan_type.name', read_only=True)

    class Meta:
        model = LoanApplication
        fields = ['id', 'user', 'user_name', 'loan_type', 'loan_type_name', 'amount', 'purpose', 'status', 'created_at']
        read_only_fields = ['status', 'user_name', 'loan_type_name', 'created_at']

# A serializer for approving a loan application.
class LoanApplicationApproveSerializer(serializers.Serializer):
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    term_months = serializers.IntegerField()


# A serializer for creating and updating the User model.
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Added 'is_admin' to fields for the login view check.
        fields = ['username', 'phone_number', 'name', 'is_admin', 'is_staff', 'is_customer_approved', 'is_active', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    # We will override the create method to make sure the password gets hashed correctly.
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user

# A serializer for the CustomerProfile model.
class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['national_id', 'email', 'address', 'digital_address', 'national_id_front_scan', 'national_id_back_scan']


# This serializer combines both User and CustomerProfile.
class CustomerDetailSerializer(serializers.ModelSerializer):
    customer_profile = CustomerProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['username', 'phone_number', 'name', 'customer_profile']
        read_only_fields = ['username', 'phone_number', 'name']

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update User fields
        instance.name = validated_data.get('name', instance.name)
        instance.save()

        # Update or create CustomerProfile
        profile_data = validated_data.pop('customer_profile', None)
        if profile_data:
            customer_profile, created = CustomerProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(customer_profile, attr, value)
            customer_profile.save()
        
        return instance
    

class SummarySerializer(serializers.Serializer):
    total_loans = serializers.IntegerField()
    paid_loans = serializers.IntegerField()
    pending_applications = serializers.IntegerField()