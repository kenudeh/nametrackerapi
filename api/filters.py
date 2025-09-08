from django_filters import rest_framework as filters
from .models import Name, UseCase
from django.utils.dateparse import parse_date
import django_filters.rest_framework as filters
from rest_framework.filters import BaseFilterBackend
from django.db.models import Q

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

# Currently not in use
class NameFilter(filters.FilterSet):
    class Meta:
        model = Name
        fields = {
            'domain_name': ['icontains'],
            # 'category__name': ['exact'],
            # 'tag__name': ['exact'],
            'is_top_rated': ['exact'],
            'is_favorite': ['exact'],
        }




class UseCaseFilter(filters.FilterSet):
    # exact matches
    competition = filters.CharFilter(field_name="competition", lookup_expr="iexact")
    difficulty  = filters.CharFilter(field_name="difficulty", lookup_expr="iexact")
    target_markets = filters.CharFilter(field_name="target_markets__name", lookup_expr="icontains")

    # category by id or name
    category = filters.NumberFilter(field_name="category_id")
    category_name = filters.CharFilter(field_name="category__name", lookup_expr="iexact")

    # created_at range
    created_at_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = UseCase
        fields = [
            "competition",
            "difficulty",
            "category",
            "category_name",
            "target_markets",
            "created_at_after",
            "created_at_before",
        ]

    @staticmethod
    def last_n(queryset, value):
        try:
            n = int(value)
            if n > 0:
                # “last N by created_at” (newest first)
                return queryset.order_by("-created_at")[:n]
        except (TypeError, ValueError):
            pass
        return queryset

#We’ll wire last_n in the view since it’s a convenience shortcut.