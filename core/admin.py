# core/admin.py:
from django.contrib import admin
from .models import User, CustomerProfile, LoanType, LoanApplication, Loan, Payment, PaymentSchedule


# A class to show the PaymentSchedule items directly within the Loan admin page.
class PaymentScheduleInline(admin.TabularInline):
    """
    An inline view to show the payment schedule related to a specific loan.
    This allows admins to see and manage payments directly from the Loan detail page.
    """
    model = PaymentSchedule
    extra = 0 # Prevents extra empty forms from being displayed
    readonly_fields = ('due_date', 'due_amount', 'is_paid', 'date_paid', 'principal_due', 'interest_due')
    can_delete = False


# Custom ModelAdmin for the Loan model to control its appearance and behavior.
class LoanAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Loan model, including list display, fieldsets,
    and a custom inline for payment schedules.
    """
    # The list_display property controls which fields are shown on the list page.
    list_display = ('application', 'amount', 'balance', 'disbursed', 'disbursement_date')
    
    # readonly_fields makes sure that these fields cannot be edited in the admin panel.
    readonly_fields = ('application', 'amount', 'interest_rate', 'term_months', 'balance', 'end_date', 'disbursement_date')
    
    # Use fieldsets to group the fields logically in the detail view.
    fieldsets = (
        (None, {
            'fields': ('application', 'amount', 'interest_rate', 'term_months', 'balance', 'end_date', 'disbursed', 'disbursement_date')
        }),
    )

    # Add the PaymentScheduleInline to this admin class.
    inlines = [PaymentScheduleInline]

    # This method dynamically sets which fields are read-only.
    def get_readonly_fields(self, request, obj=None):
        # If the object exists and the loan is disbursed, make the 'disbursed' field read-only.
        if obj and obj.disbursed:
            return self.readonly_fields + ('disbursed',)
        # Otherwise, return the default read-only fields.
        return self.readonly_fields


# Custom ModelAdmin for the Payment model.
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Payment model.
    """
    # The list_display controls the columns in the list view.
    list_display = ('id', 'payment_schedule', 'amount_paid', 'payment_date', 'recorded_by')


# Register your models here.
admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(LoanType)
admin.site.register(LoanApplication)
admin.site.register(Loan, LoanAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(PaymentSchedule)
