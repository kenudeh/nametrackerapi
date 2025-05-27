from django_filters import rest_framework as filters
from .models import Tool, Support


# Definign a Filter Class
class ToolFilter(filters.FilterSet):
    # Custom filter for category (handles both IDs and names)
    category = filters.CharFilter(method='filter_category')
    # Standard auto-filters
    pricing = filters.CharFilter(method='filter_pricing')
    is_featured = filters.BooleanFilter(field_name="is_featured")
    tags = filters.CharFilter(field_name="tags", lookup_expr="icontains")
    
    class Meta:
        model = Tool
        fields = {
            'pricing': ['exact'],      # Provides exact match filtering
            'is_featured': ['exact'],  # Boolean filter
            'tags': ['icontains']      # Already declared above, this is optional
        }

    def filter_category(self, queryset, name, value):
        """Handle both category IDs (numbers) and names (text)"""
        if not value:
            return queryset
            
        try:
            # Try numeric ID first
            return queryset.filter(category__id=int(value))
        except (ValueError, TypeError):
            # Fall back to name search
            return queryset.filter(category__name__icontains=value)

    def filter_pricing(self, queryset, name, value):
        """Handle both pricing IDs (numbers) and names (text)"""
        if not value:
            return queryset
            
        try:
            # Try numeric ID first
            return queryset.filter(pricing__id=int(value))
        except (ValueError, TypeError):
            # Fall back to name search
            return queryset.filter(pricing__type__iexact=value)


# FIlter class for Requests
class RequestFilter(filters.FilterSet):
    created_at = filters.DateFilter(field_name="created_at", lookup_expr='gte')
    
    class Meta:
        model = Support
        fields = ['created_at']