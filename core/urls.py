from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CustomerProfileViewSet, LoanTypeViewSet,
    LoanApplicationViewSet, LoanViewSet, PaymentViewSet, index
)


# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profile', CustomerProfileViewSet, basename='customerprofile')
router.register(r'loan-types', LoanTypeViewSet)
router.register(r'loan-applications', LoanApplicationViewSet)
router.register(r'loans', LoanViewSet)
router.register(r'payments', PaymentViewSet, basename='payments')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # The API endpoints are now nested under the 'api/' prefix
    path('api/', include(router.urls)),
    # This is the new URL pattern that serves the index.html template
    path('', index, name='index'),
]
