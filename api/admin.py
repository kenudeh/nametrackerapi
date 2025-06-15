# admin.py
from django.contrib import admin
from .models import Name, NameCategory, NameTag, UseCase

# Inline for UseCase - allows adding up to 3 UseCases directly in the Name admin page.
class UseCaseInline(admin.StackedInline):
    model = UseCase
    extra = 0  # No extra empty forms by default
    max_num = 3  # Enforce maximum of 3 UseCases per Name
    min_num = 1  # Must have at least 1 UseCase (enforced via serializer but safe reminder here)
    show_change_link = True  # Allow jumping into UseCase admin from here

# Since 'category' is now ForeignKey, no inline needed.

# Inline for ManyToMany Tag relation (optional, as filter_horizontal can also be used)
class NameTagInline(admin.TabularInline):
    model = Name.tag.through  # Through table for ManyToMany relationship
    extra = 1

@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    list_display = (
        'domain_name',  # Corrected field name
        'extension',
        'domain_list',
        'status',
        'length',
        'syllables',
        'competition',
        'difficulty',
        'is_top_rated',
        'is_favorite',
        'drop_date',
    )
    list_filter = (
        'extension',
        'domain_list',
        'status',
        'is_top_rated',
        'is_favorite',
        'category',  # Allow filtering by category in sidebar
    )
    search_fields = ('domain_name',)  # Corrected field name
    date_hierarchy = 'drop_date'
    
    inlines = [UseCaseInline, NameTagInline]  # Inlines for UseCase and Tags
    
    filter_horizontal = ('tag',)  # Easier multi-select for tags
    
    fieldsets = (
        (None, {
            'fields': ('domain_name', 'extension', 'domain_list', 'status')
        }),
        ('Metrics', {
            'fields': ('length', 'syllables', 'competition', 'difficulty', 'is_top_rated', 'is_favorite')
        }),
        ('Relations', {
            'fields': ('category', 'suggested_usecase')  # Category is FK, suggested_usecase auto-set
        }),
        ('Timing', {
            'fields': ('drop_date', 'drop_time')
        }),
    )

@admin.register(NameCategory)
class NameCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(NameTag)
class NameTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    list_display = ('case_title', 'domain_name', 'order', 'difficulty', 'competition', 'revenue_potential')
    list_filter = ('difficulty', 'competition', 'revenue_potential')
    search_fields = ('case_title', 'target_market')
