from django_filters import rest_framework as filters
from .models import Name, UseCase
from django.utils.dateparse import parse_date

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




class UseCaseFilter(BaseFilterBackend):
    """
    Custom filter backend that mimics the old django_filters.FilterSet functionality.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params

        # exact matches
        competition = params.get("competition")
        if competition:
            queryset = queryset.filter(competition__iexact=competition)

        difficulty = params.get("difficulty")
        if difficulty:
            queryset = queryset.filter(difficulty__iexact=difficulty)

        target_market = params.get("target_market")
        if target_market:
            queryset = queryset.filter(target_market__icontains=target_market)

        # category by id or name
        category = params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        category_name = params.get("category_name")
        if category_name:
            queryset = queryset.filter(category__name__iexact=category_name)

        # created_at range
        created_at_after = params.get("created_at_after")
        if created_at_after:
            queryset = queryset.filter(created_at__gte=created_at_after)

        created_at_before = params.get("created_at_before")
        if created_at_before:
            queryset = queryset.filter(created_at__lte=created_at_before)

        # last_n shortcut
        last_n = params.get("last_n")
        if last_n:
            try:
                n = int(last_n)
                if n > 0:
                    queryset = queryset.order_by("-created_at")[:n]
            except (TypeError, ValueError):
                pass

        return queryset

#We’ll wire last_n in the view since it’s a convenience shortcut.