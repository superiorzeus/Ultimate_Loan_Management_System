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

class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access for all users,
    but write access only for admin users.
    """
    def has_permission(self, request, view):
        # SAFE_METHODS are GET, HEAD, OPTIONS.
        # This checks if the request is a read-only operation.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # If it's a write operation (POST, PUT, DELETE),
        # only allow it if the user is a staff member.
        return bool(request.user and request.user.is_staff)

    def has_object_permission(self, request, view, obj):
        # Read-only permissions are granted to any user on any object.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only granted if the user is an admin.
        return bool(request.user and request.user.is_staff)
