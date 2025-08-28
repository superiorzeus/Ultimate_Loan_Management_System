# core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    UserViewSet, CustomerProfileViewSet, LoanTypeViewSet,
    LoanApplicationViewSet, LoanViewSet, PaymentViewSet, 
    UserRegisterView, CustomerViewSet, PaymentScheduleViewSet, register_view,
    index, login_view, dashboard_view, logout_and_redirect, AdminCreateCustomerView, add_customer_view, CustomerListView, customer_detail_view, SummaryViewSet,
    create_loan_application_view, LoanTypeManageView, loan_detail_view, loan_application_detail_view, LoanSearchAPIView, payment_detail_view
)


# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profile', CustomerProfileViewSet, basename='customerprofile')
router.register(r'loan-types', LoanTypeViewSet)
router.register(r'loan-applications', LoanApplicationViewSet)
# router.register(r'api-loan-applications', LoanApplicationViewSet, basename='api-loan-applications')
router.register(r'loans', LoanViewSet)
router.register(r'payments', PaymentViewSet, basename='payments')
router.register(r'customers', CustomerViewSet, basename='customers')
router.register(r'payment-schedules', PaymentScheduleViewSet)

# Add this new line for the summary endpoint
router.register(r'summary', SummaryViewSet, basename='summary')


urlpatterns = [
    # Custom URL for the main index page
    path('', index, name='index'),
    # Custom URL for the form-based registration view
    path('register/', register_view, name='register'),
    # Custom URL for the login view
    path('login/', login_view, name='login'),
    # Custom URL for the dashboard page
    path('dashboard/', dashboard_view, name='dashboard'),
    # Custom URL for the logout view
    path('logout/', views.logout_and_redirect, name='logout'),
    # URL for the add customer page
    path('add-customer/', add_customer_view, name='add-customer'),
    
    # This is the crucial URL for the DRF API's registration endpoint.
    # It must be before the `include(router.urls)` line to take precedence.
    path('api/users/register/', UserRegisterView.as_view(), name='user-register'),

    # URL for admins to create customers directly
    path('api/admin/create-customer/', AdminCreateCustomerView.as_view(), name='admin-create-customer'),

    # URL to list all customers specifically for the admin dashboard
    path('api/customers/list/', CustomerListView.as_view(), name='customer-list'),

    # URL to show the detail page for a specific customer
    path('customers/<str:username>/', views.customer_detail_view, name='customer-detail'),

    # New URL to handle the update action for customer status
    path('customers/<str:username>/update-status/', views.customer_detail_view, name='customer_update_status'),

    # URL for the loan application form page
    path('add-loan-application/', views.create_loan_application_view, name='add-loan-application'),

    # URL to manage loan types
    path('api/loan-types/manage/', LoanTypeManageView.as_view(), name='manage-loan-types'),

    # URL for the loan detail page
    path('loans/<int:pk>/', views.loan_detail_view, name='loan-detail'),

    # URL for the loan application detail page
    path('loan-applications/<int:pk>/', loan_application_detail_view, name='loan-application-detail'),

    # URL for searching loans
    path('api/loans/search/', views.LoanSearchAPIView.as_view(), name='loan-search'),

    # URL for the add payment page
    path('add-payment/', views.add_payment_view, name='add-payment'),

    # URL for the payment detail page
    path('payments/<int:pk>/', views.payment_detail_view, name='payment-detail'),

    # Include the router-generated URLs
    path('api/', include(router.urls)),
]