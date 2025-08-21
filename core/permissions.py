from rest_framework import permissions

# Custom permission to only allow admin users to access a view.
class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow authenticated admin users to access a view.
    """
    def has_permission(self, request, view):
        # The standard Django field for admin users is `is_staff`.
        # Your custom User model inherits from AbstractBaseUser, which includes this field.
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)