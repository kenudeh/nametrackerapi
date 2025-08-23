from django_filters import rest_framework as filters
from .models import Name, UseCase
from django.utils.dateparse import parse_date


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




class UseCaseFilter(django_filters.FilterSet):
    # exact matches
    competition = django_filters.CharFilter(field_name="competition", lookup_expr="iexact")
    difficulty  = django_filters.CharFilter(field_name="difficulty",  lookup_expr="iexact")
    target_market = django_filters.CharFilter(field_name="target_market", lookup_expr="icontains")
    # category by id or name (both handy)
    category = django_filters.NumberFilter(field_name="category_id")
    category_name = django_filters.CharFilter(field_name="category__name", lookup_expr="iexact")
    # created_at range
    created_at_after = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at_before = django_filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = UseCase
        fields = [
            "competition",
            "difficulty",
            "category",
            "category_name",
            "target_market",
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