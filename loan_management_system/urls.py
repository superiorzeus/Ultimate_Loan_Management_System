from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Make sure to import all the views you need from your core app
from core import views

# Create a router instance for your viewsets
router = DefaultRouter()
router.register(r'loantypes', views.LoanTypeViewSet)
router.register(r'loanapplications', views.LoanApplicationViewSet, basename='loanapplication')
router.register(r'loans', views.LoanViewSet, basename='loan')
router.register(r'payments', views.PaymentViewSet, basename='payment')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'), # Serves the index.html file
    
    # User authentication and registration
    # Use a different name for the user registration endpoint, for example, 'register'
    path('api/register/', views.UserRegisterView.as_view(), name='register'),
    path('api/login/', views.LoginView.as_view(), name='login'),

    # Customer and Admin specific endpoints
    path('api/profile/', views.CustomerProfileView.as_view(), name='customer_profile'),
    path('api/admin/customers/', views.AdminCustomerListView.as_view(), name='admin_customer_list'),
    path('api/admin/customers/<int:pk>/approve/', views.ApproveCustomerView.as_view(), name='approve_customer'),
    path('api/admin/loanapplications/<int:pk>/approve/', views.ApproveLoanApplicationView.as_view(), name='approve_loan_application'),
    path('api/admin/loanapplications/<int:pk>/decline/', views.DeclineLoanApplicationView.as_view(), name='decline_loan_application'),
    path('api/admin/loanapplications/<int:pk>/disburse/', views.DisburseLoanApplicationView.as_view(), name='disburse_loan_application'),
    
    # DRF router URLs for the viewsets
    path('api/', include(router.urls)),
]
