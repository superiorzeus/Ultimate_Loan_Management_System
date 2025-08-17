from django.shortcuts import render
from rest_framework import viewsets
from .models import LoanType
from .serializers import LoanTypeSerializer
from .permissions import IsAdminUser

# Create your views here.

# A ViewSet for viewing and editing LoanType instances.
# It provides CRUD operations (Create, Read, Update, Delete) for the LoanType model.
class LoanTypeViewSet(viewsets.ModelViewSet):
    queryset = LoanType.objects.all()
    serializer_class = LoanTypeSerializer
    permission_classes = [IsAdminUser]
