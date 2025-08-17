from rest_framework import serializers
from .models import LoanType, User, CustomerProfile, LoanApplication, Loan, Payment

# This serializer is used to manage LoanType objects.
# It handles the conversion of LoanType model instances to and from JSON.
class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = '__all__'

# This serializer is used to manage LoanApplication objects.
# It handles the conversion of LoanApplication model instances to and from JSON.
class LoanApplicationSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    loan_type = serializers.PrimaryKeyRelatedField(queryset=LoanType.objects.all())
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        # The user is added from the request, not the request body
        validated_data['user'] = self.context['request'].user
        return LoanApplication.objects.create(**validated_data)

    def update(self, instance, validated_data):
        # We only allow the status to be changed for admin users
        if self.context['request'].user.is_admin:
            instance.status = validated_data.get('status', instance.status)
            instance.save()
        return instance

# This serializer is used for the Loan model.
class LoanSerializer(serializers.ModelSerializer):
    # The application is a read-only field since a loan is created from an application.
    application = serializers.PrimaryKeyRelatedField(read_only=True)
    # The balance is read-only as it will be calculated automatically.
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Loan
        fields = '__all__'

# This serializer is used for the Payment model.
class PaymentSerializer(serializers.ModelSerializer):
    # The loan is a read-only field since it's an FK to a loan.
    loan = serializers.PrimaryKeyRelatedField(read_only=True)
    # The payment date is read-only as it's set automatically.
    payment_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'
