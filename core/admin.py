from django.contrib import admin
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment

# Register your models here.
admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(LoanType)
admin.site.register(LoanApplication)
admin.site.register(Loan)
admin.site.register(Payment)