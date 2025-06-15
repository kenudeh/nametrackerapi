from django_filters import rest_framework as filters
from .models import Name

# class NameFilter(filters.FilterSet):
#     class Meta:
#         model = Name
#         fields = {
#             'domain': ['exact', 'icontains'],
#             'extension': ['exact'],
#             'status': ['exact'],
#             'is_top_rated': ['exact'],
#             'length': ['exact', 'gte', 'lte'],
#             'syllables': ['exact', 'gte', 'lte'],
#             'drop_date': ['exact', 'gte', 'lte'],
#         }

class NameFilter(filters.FilterSet):
    class Meta:
        model = Name
        fields = {
            'domain_name': ['icontains'],
            'category__name': ['exact'],
            'tag__name': ['exact'],
            'is_top_rated': ['exact'],
            'is_favorite': ['exact'],
        }