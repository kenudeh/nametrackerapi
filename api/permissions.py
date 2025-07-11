from rest_framework.permissions import BasePermission, SAFE_METHODS




class IsManagerOrReadOnly(BasePermission):
    """
    Allows GET access only to authenticated users in the 'admin' group.
    Allows POST access to everyone.
    Denies PUT, PATCH, DELETE.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated and request.user.groups.filter(name="admin").exists()
        if request.method == "POST":
            return True
        return False

        

# class IsManagerOrReadOnly(BasePermission):
#     """
#     Custom permission to allow only managers to create menu items.
#     Delivery Crew and Customer roles can only read.
#     Anonymous users can also read.
#     """
    
#     def has_permission(self, request, view):
        
#         # safe methods include GET. THey do not alter db records
#         if request.method in SAFE_METHODS:
#             return True  # Unauthenticated and authenticated users can GET
        
#         if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
#             return request.user.is_authenticated and request.user.groups.filter(name="manager").exists() #Only managers can POST
       
#         return False # Deny all other HTTP method (PUT, PATCH, DELETE)