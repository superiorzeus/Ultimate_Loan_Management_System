Ultimate Loan Management System API Documentation
This document provides a detailed overview and the RESTful API endpoints for the Loan Management System.

Project Setup - Follow these steps to set up the project locally:
    Prerequisites - Make sure you have the following installed on your system:
       - Python 3.13+
       - pip (Python package installer)
       - A database system (currently configured to use MySQL).
    
    1. Clone the Repository - Clone the project from your version control system (e.g., GitHub):
            >> git clone https://github.com/superiorzeus/Ultimate_Loan_Management_System.git
            >> cd Ultimate_Loan_Management_System

    2. Create a Virtual Environment - It's highly recommended to use a virtual environment to manage project dependencies:
            >> python3 -m venv venv
    
    3. Activate the Virtual Environment:
            On macOS and Linux:
                >> source venv/bin/activate
            On Windows:
                >> .\venv\Scripts\activate
    
    4. Install Dependencies - Install all the required Python packages using pip:
        >> pip install -r requirements.txt
    
    5. Configure the Database:
            Apply the database migrations to create the necessary tables:
                >> python manage.py makemigrations
                >> python manage.py migrate
    
    6. Create a Superuser:
            Create an administrative user to access the Django admin panel and manage your data:
                >> python manage.py createsuperuser
                Follow the prompts to enter a username, name, email, and password for your admin account.
    
    7. Run the Development Server - Start the Django development server to see the project in action:
        >> python manage.py runserver

    8. Access URL:
        API: http://127.0.0.1:8000/api/
        Django Admin: http://127.0.0.1:8000/admin/
        Frontend UI: http://127.0.0.1:8000/



Permissions - The API uses custom permission classes to control access:
    IsAuthenticated: Only authenticated users can access the endpoint.
    IsAdminUser: Only staff members with is_staff=True can access the endpoint.
    IsAdminUserOrReadOnly: Admins can perform any action, while other authenticated users can only perform read-only actions (GET, HEAD, OPTIONS).
    Custom View Logic: Some views contain logic to filter querysets based on the user, ensuring a customer can only see their own data.


Authentication:
This API uses token-based authentication. Users must be authenticated to access most endpoints.

Endpoints:

1. User and Authentication Endpoints - These endpoints manage user registration, authentication, and user data.
        Endpoint: /api/register/
        Method: POST
        Description: Creates a new User and a linked CustomerProfile. Requires user details and scans of the national ID.

        Endpoint: /api/login/
        Method: POST
        Description: Authenticates a user with a username and password, returning an authentication token.

        Endpoint: /api/users/
        Method: GET
        Description: Lists all users. (Admin only)

        Endpoint: /api/users/<pk>/
        Method: GET, PUT, PATCH, DELETE
        Description: Retrieve, update, or delete a specific user. (Admin only)

        Endpoint: /api/profile/
        Method: GET, PUT, PATCH
        Description: Retrieve and update the profile of the currently authenticated user.

    Request/Response Schemas:
        UserRegisterView (POST /api/register/):
            Request Body: username, phone_number, name, password, email, national_id, address, digital_address, national_id_front_scan, national_id_back_scan.
            Response: token and user_id upon successful registration.

        ObtainAuthToken (POST /api/login/)
            Request Body: username, password.
            Response: token


2. Loan Management Endpoints - These endpoints handle loan applications, loans, and related financial data:
        Endpoint: /api/loan-types/
        Method: GET
        Description: Retrieves a list of all available loan types.

        Endpoint: /api/loan-types/<pk>/
        Method: GET
        Description: Retrieve details for a specific loan type.

        Endpoint: /api/loan-types/manage/
        Method: POST
        Description: Endpoint to create a new loan type or update an existing one. (Admin only)

        Endpoint: /api/loan-applications/
        Method: GET, POST
        Description: Lists all applications. Admins see all, customers see their own. POST creates a new application.

        Endpoint: /api/loan-applications/<pk>/
        Method: GET, PUT, PATCH, DELETE
        Description: Retrieve, update, or delete a loan application. PUT and DELETE are admin-only.

        Endpoint: /api/loan-applications/<loan_pk>/disburse/
        Method: POST
        Description: Custom action to disburse a loan. Creates a Loan object and a PaymentSchedule. (Admin only)

        Endpoint: /api/loans/
        Method: GET
        Description: Lists all disbursed loans. Admins see all, customers see their own.

        Endpoint: /api/loans/<pk>/
        Method: GET
        Description: Retrieves details of a specific disbursed loan.

        Endpoint: /api/loans/<loan_pk>/payments/
        Method: POST
        Description: Creates a new payment for a specific loan. (Admin only)

        Endpoint: /api/loans/search/
        Method: GET
        Description: Searches for loans by loan ID or customer name/username. Requires q query parameter.
    
    Request/Response Schemas:
        LoanApplicationViewSet (POST /api/loan-applications/)
            Request Body: amount, purpose, loan_type_pk.
            Response: Details of the created loan application.

        LoanDisburseView (POST /api/loan-applications/<loan_pk>/disburse/)
            Request Body: N/A (requires loan_pk in URL).
            Response: { "detail": "Loan disbursed successfully." } or an error.
        
        PaymentCreateAPIView (POST /api/loans/<loan_pk>/payments/)
            Request Body: amount_paid, payment_date.
            Response: Details of the created payment.


3. Financial and Status Endpoints - These endpoints provide access to financial data like payments and payment schedules, as well as a summary of key loan statistics for administrative purposes:
        Endpoint: /api/payments/
        Method: GET, POST
        Description: Lists payments. Admins see all payments, customers see their own. POST creates a new payment. (Admin only)

        Endpoint: /api/payments/<pk>/
        Method: GET
        Description: Retrieves details of a specific payment.

        Endpoint: /api/payment-schedules/
        Method: GET
        Description: Lists all payment schedules for all loans. Admins see all, customers see their own.

        Endpoint: /api/payment-schedules/<pk>/
        Method: GET
        Description: Retrieves details for a specific payment schedule.

        Endpoint: /api/summary/
        Method: GET
        Description: Provides a summary of key statistics, including total loans, paid loans, and pending applications. (Admin only)
    
    Request/Response Schemas:
        SummaryViewSet (GET /api/summary/)
            Description: Provides a summary of key statistics, including total loans, paid loans, and pending applications. (Admin only)
            Request Body: None
            Response: { "total_loans": 10, "paid_loans": 5, "pending_applications": 2 }
        
        PaymentViewSet (POST /api/payments/)
            Request Body: payment_schedule, amount_paid.
            Response: Details of the created payment.


API Usage - Here are some example curl commands to demonstrate how to interact with the API:

    1. User Registration (POST /api/register/) - This command registers a new customer by sending a JSON payload and multipart form data for the ID scans:
        curl -X POST \
            http://127.0.0.1:8000/api/register/ \
            -H 'Content-Type: multipart/form-data' \
            -F 'username=johndoe' \
            -F 'phone_number=+233551234567' \
            -F 'name=John Doe' \
            -F 'password=yourpassword123' \
            -F 'email=john@example.com' \
            -F 'national_id=NI-123456789' \
            -F 'address=123 Main St' \
            -F 'digital_address=GA-123-4567' \
            -F 'national_id_front_scan=@/path/to/id_front.jpg' \
            -F 'national_id_back_scan=@/path/to/id_back.jpg'
    
    2. User Login (POST /api/login/) - This command authenticates a user and retrieves a token for subsequent API calls:
        curl -X POST \
            http://127.0.0.1:8000/api/login/ \
            -H 'Content-Type: application/json' \
            -d '{
                "username": "johndoe",
                "password": "yourpassword123"
            }'
    
    3. Get All Loans (GET /api/loans/) - This command retrieves a list of all loans using the authentication token:
        curl -X GET \
            http://127.0.0.1:8000/api/loans/ \
            -H 'Authorization: Token <your_auth_token>'


Models Schema - Here are the key models used in the project, providing context for the data represented by the API endpoints.

    1. User: Represents a user of the system.
            username (str): Unique username for login.
            name (str): The user's full name.
            phone_number (str): The user's phone number.
            is_staff (bool): True for staff/admin users.
            is_customer_approved (bool): True if the customer is approved for loans.

    2. CustomerProfile: Extends the User model with additional customer-specific details.
            user (OneToOne): Links to the User model.
            email (str): The user's email address.
            national_id (str): The customer's unique national ID.
            national_id_front_scan (file): A scanned image of the front of the national ID.
            national_id_back_scan (file): A scanned image of the back of the national ID.

    3. LoanApplication: Represents a request for a loan.
            amount (Decimal): The amount of money requested.
            purpose (str): The reason for the loan.
            status (str): The current status of the application (e.g., pending, approved, disbursed).
    
    4. Loan: Represents an approved and disbursed loan.
            application (ForeignKey): Links to the LoanApplication it originated from.
            amount (Decimal): The total loan amount.
            balance (Decimal): The outstanding balance.
            disbursement_date (date): The date the loan was disbursed.
            status (str): The loan's current status (e.g., active, paid).

    5. Payment: Records a payment made against a loan.
            loan (ForeignKey): The loan this payment is for.
            amount_paid (Decimal): The amount paid.
            payment_date (date): The date the payment was made.
            recorded_by (ForeignKey): The user who recorded the payment.
            transaction_id (UUID): A unique identifier for the payment transaction.

Frontend Pages - The project also includes a few front-end pages to provide a user-friendly interface for administration:
    /: The main landing or index page.
    /login/: The login page for users.
    /register/: The registration page for new customers.
    /dashboard/: The main dashboard for authenticated users (both admin and customers), showing a summary of their data.
    /customers/: A list of all customers, accessible by administrators.
    /add-customer/: A page for an admin to create a new customer.
    /customers/<username>/: A detailed view of a specific customer, including their personal information, loans, and payment history.
    /loan-applications/: A list of all submitted loan applications.
    /add-loan-application/: A form page for a customer and an admin to submit a new loan application.
    /loan-applications/<pk>/: A detailed view of a specific loan application.
    /loans/: A list of all disbursed loans.
    /loans/<pk>/: The detail page for a specific loan, showing its status and details.
    /loan-types/: A page to view and manage different types of loans.
    /add-payment/: A page for an admin to record a new payment.
    /payments/: A list of all payments made across all loans.
    /payments/<pk>/: A detailed view of a specific payment.