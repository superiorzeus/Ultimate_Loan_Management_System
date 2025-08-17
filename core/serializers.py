from rest_framework import serializers
from .models import LoanType, User, CustomerProfile

# This serializer is used to manage LoanType objects.
# It handles the conversion of LoanType model instances to and from JSON.
class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = '__all__'
