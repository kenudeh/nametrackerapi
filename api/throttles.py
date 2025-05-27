from rest_framework.throttling import UserRateThrottle


    
class ToolSuggestionThrottle(UserRateThrottle):
    scope = 'tool_submission'

# Not in use at the moment. Using AnonRate for now
class PostRequestThrottle(UserRateThrottle):
    scope = 'post_request'
     

class ComparisonThrotttle(UserRateThrottle):
    scope = 'compare'