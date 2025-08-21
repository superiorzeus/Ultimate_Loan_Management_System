from rest_framework import serializers
from .models import User, CustomerProfile, LoanApplication, Loan, Payment, LoanType, PaymentSchedule
from django.db import transaction

# A serializer for the User model specifically for registration.
class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'phone_number', 'name', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user


# A serializer for the LoanType model.
class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = '__all__'

# A serializer for the Payment model.
class PaymentSerializer(serializers.ModelSerializer):
    # The recorded_by field is read-only because it's set by the backend.
    recorded_by = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'amount_paid', 'payment_date', 'recorded_by']
        read_only_fields = ['payment_date', 'recorded_by']

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
    # This will display the full payment schedule for the loan.
    payment_schedule = PaymentScheduleSerializer(many=True, read_only=True)
    loan_type = serializers.CharField(source='application.loan_type.name')
    term_months = serializers.IntegerField(source='application.loan_type.term_months')
    
    class Meta:
        model = Loan
        fields = [
            'id', 'amount', 'interest_rate', 'term_months', 'balance', 
            'disbursed', 'disbursement_date', 'start_date', 'end_date',
            'loan_type', 'payment_schedule' # Renamed from 'payments' to 'payment_schedule'
        ]


# A serializer for the LoanApplication model.
class LoanApplicationSerializer(serializers.ModelSerializer):
    # This serializer now uses a PrimaryKeyRelatedField for the user's customer profile.
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    loan_type = serializers.PrimaryKeyRelatedField(queryset=LoanType.objects.all())
    loan = LoanSerializer(read_only=True)

    class Meta:
        model = LoanApplication
        fields = ['id', 'user', 'loan_type', 'amount', 'status', 'created_at', 'loan']
        read_only_fields = ['user', 'status', 'created_at']

# A serializer for approving a loan application.
class LoanApplicationApproveSerializer(serializers.Serializer):
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    term_months = serializers.IntegerField()


# A serializer for creating and updating the User model.
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Added 'is_admin' to fields for the login view check.
        fields = ['username', 'phone_number', 'name', 'is_customer', 'is_admin', 'is_staff', 'password']
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


# A simple serializer for the CustomerProfile model.
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = '__all__'


# A serializer for the CustomerProfile model.
class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['national_id', 'email', 'address', 'digital_address', 'national_id_front_scan', 'national_id_back_scan']


# This serializer combines both User and CustomerProfile.
class CustomerDetailSerializer(serializers.ModelSerializer):
    profile = CustomerProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['username', 'phone_number', 'name', 'profile']
        read_only_fields = ['username', 'phone_number', 'name']

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update User fields
        instance.name = validated_data.get('name', instance.name)
        instance.save()

        # Update or create CustomerProfile
        profile_data = validated_data.pop('profile', None)
        if profile_data:
            customer_profile, created = CustomerProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(customer_profile, attr, value)
            customer_profile.save()
        
        return instance
