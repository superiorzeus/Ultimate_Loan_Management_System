# Import the post_save signal from Django's core
from django.db.models.signals import post_save
# Import the LoanApplication and Loan models
from django.dispatch import receiver
from .models import LoanApplication, Loan
# Import the date library
from datetime import date
from dateutil.relativedelta import relativedelta


# The receiver decorator connects this function to the post_save signal.
# It will be triggered whenever a LoanApplication instance is saved.
@receiver(post_save, sender=LoanApplication)
def create_loan_on_approval(sender, instance, created, **kwargs):
    """
    Automatically creates a Loan instance when a LoanApplication is approved.
    The total interest is calculated and added to the balance upfront.
    """
    # Check if the application's status is 'approved'
    # We also check if a loan doesn't already exist for this application to prevent duplicates
    if instance.status == 'approved' and not hasattr(instance, 'loan'):
        # Calculate the end date for the loan
        end_date = date.today() + relativedelta(months=+instance.loan_type.term_months)
        
        # Calculate the total interest based on the flat rate
        total_interest = (instance.amount * instance.loan_type.interest_rate) / 100
        
        # Calculate the total balance due (principal + total interest)
        total_balance = instance.amount + total_interest

        # Create the new Loan instance
        Loan.objects.create(
            application=instance,
            amount=instance.amount,
            interest_rate=instance.loan_type.interest_rate,
            term_months=instance.loan_type.term_months,
            # Set the initial balance with the total interest added
            balance=total_balance,
            end_date=end_date,
            # Initially, the loan is not yet disbursed
            disbursed=False,
            disbursement_date=None,
        )

        print(f"Loan created for application {instance.id}")


# A signal receiver that listens for changes to the Loan model.
@receiver(post_save, sender=Loan)
def set_disbursement_date(sender, instance, **kwargs):
    """
    Sets the disbursement date when a loan is marked as disbursed.
    """
    if instance.disbursed and not instance.disbursement_date:
        instance.disbursement_date = date.today()
        # Save the instance again with the updated date, but set update_fields
        # to prevent an infinite loop.
        instance.save(update_fields=['disbursement_date'])
        print(f"Loan {instance.pk} disbursed on {instance.disbursement_date}")
