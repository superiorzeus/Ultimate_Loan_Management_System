from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    UserViewSet, CustomerProfileViewSet, LoanTypeViewSet,
    LoanApplicationViewSet, LoanViewSet, PaymentViewSet, 
    UserRegisterView, CustomerViewSet, PaymentScheduleViewSet,
    index, login_view, dashboard_view, logout_and_redirect
)


# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profile', CustomerProfileViewSet, basename='customerprofile')
router.register(r'loan-types', LoanTypeViewSet)
router.register(r'loan-applications', LoanApplicationViewSet)
router.register(r'loans', LoanViewSet)
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'customers', CustomerViewSet, basename='customers')
router.register(r'payment-schedules', PaymentScheduleViewSet)


urlpatterns = [
    # Custom URL for the main index page
    path('', index, name='index'),
    # Custom URL for user registration
    path('register/', UserRegisterView.as_view(), name='register'),
    # Custom URL for the login view
    path('login/', login_view, name='login'),
    # Custom URL for the dashboard page
    path('dashboard/', dashboard_view, name='dashboard'),
    # Custom URL for the logout view
    path('logout/', views.logout_and_redirect, name='logout'),
    # path('logout/', logout_view, name='logout'),
    
    # Include the router-generated URLs
    path('api/', include(router.urls)),
]

