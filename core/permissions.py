from rest_framework import permissions

# Custom permission to only allow admin users to access a view.
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # Read permissions are allowed to any user, so we'll only check for write permissions
        # on safe methods (GET, HEAD, OPTIONS).
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions (POST, PUT, PATCH, DELETE) are only allowed to admin users.
        return request.user and request.user.is_authenticated and request.user.is_admin
