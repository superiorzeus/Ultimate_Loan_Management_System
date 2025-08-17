from django.contrib import admin
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment

# Register your models here.
admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(LoanType)
admin.site.register(LoanApplication)

# Custom ModelAdmin for the Loan model to control its appearance and behavior.
class LoanAdmin(admin.ModelAdmin):
    # The list_display property controls which fields are shown on the list page.
    list_display = ('application', 'amount', 'balance', 'disbursed', 'disbursement_date')
    
    # readonly_fields makes sure that these fields cannot be edited in the admin panel.
    # Note: 'disbursed' is not in this tuple initially
    readonly_fields = ('application', 'amount', 'interest_rate', 'term_months', 'balance', 'end_date', 'disbursement_date')
    
    # We will use the fieldsets property to group the fields logically
    fieldsets = (
        (None, {
            'fields': ('application', 'amount', 'interest_rate', 'term_months', 'balance', 'end_date', 'disbursed', 'disbursement_date')
        }),
    )

    # This method dynamically sets which fields are read-only
    def get_readonly_fields(self, request, obj=None):
        # If the object exists and the loan is disbursed, make the 'disbursed' field read-only
        if obj and obj.disbursed:
            return self.readonly_fields + ('disbursed',)
        # Otherwise, return the default read-only fields
        return self.readonly_fields

admin.site.register(Loan, LoanAdmin)
admin.site.register(Payment)