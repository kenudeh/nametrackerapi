from rest_framework import pagination



# Pagination class for Tool
class ToolPagination(pagination.PageNumberPagination):
    page_size = 8 #Default page size
    page_size_query_param = "page_size"  # Allow client to override
    max_page_size = 100 # maximum page size
    
    
# Pagination class for Tool SUggestion
class ToolSuggestionPagination(pagination.PageNumberPagination):
    page_size = 10 #Default page size
    page_size_query_param = "page_size"  # Allow client to override
    max_page_size = 100 # maximum page size
    
    
    
# Pagination class for User Profile
class UserProfilePagination(pagination.PageNumberPagination):
    page_size = 10  # Number of items per page
    page_size_query_param = 'page_size'  # Allow client to override page size
    max_page_size = 100  # Maximum page size allowed
    
    
    
# Pagination class for Favorites
class FavoritePagination(pagination.PageNumberPagination):
    """
    Enables pagination for the Favorite list endpoint.
    Users can navigate through their favorite tools page by page.
    """
    page_size = 10  # Defines how many favorites are displayed per page
    page_size_query_param = 'page_size'  # Allows clients to specify page size
    max_page_size = 50  # Prevents excessively large responses
    
    
# Pagination class for Reviews
class ReviewPagination(pagination.PageNumberPagination):
    page_size = 10  # Number of reviews per page
    page_size_query_param = "page_size"
    max_page_size = 100
    
    
# Pagination class for Requests
class RequestPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100