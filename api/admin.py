# admin.py
from django.contrib import admin
from .models import Name, AppUser, NameCategory, NameTag, UseCase, ArchivedName, Subscription, PlanModel, AcquiredNames, SavedNames, ExtensionDropInfo

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

#Bulk Action to Archive Manually - to be used in NameAdmin
@admin.action(description='Archive selected names')
def archive_selected_names(modeladmin, request, queryset):
    for name in queryset:
        ArchivedName.objects.create(
            domain_name=name.domain_name,
            extension=name.extension,
            original_drop_date=name.drop_date,
            reason='Manual archive from admin'
        )
        name.delete()


#Name admin
@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    readonly_fields = ('length', 'syllables', 'status') 
    list_display = (
        'domain_name',  
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
    list_display_links = ('domain_name',) 
    list_filter = (
        'extension',
        'domain_list',
        'status',
        'is_top_rated',
        'is_favorite',
        'category', 
    )
    search_fields = ('domain_name',)  
    date_hierarchy = 'drop_date'
    inlines = [UseCaseInline, NameTagInline]  # Inlines for UseCase and Tags
    filter_horizontal = ('tag',)  # Easier multi-select for tags
    actions = [archive_selected_names]

    fieldsets = (
        (None, {
            'fields': ('domain_name', 'extension', 'domain_list', 'status')
        }),
        ('Metrics', {
            'fields': ('competition', 'difficulty', 'is_top_rated', 'is_favorite')
        }),
        ('Relations', {
            'fields': ('category', 'suggested_usecase')  # Category is FK, suggested_usecase auto-set
        }),
        ('Timing', {
            'fields': ('drop_date', 'drop_time')
        }),
    )


@admin.register(AppUser)
class AppUser(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email')
   

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


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'subscription_expiry', 'isPaid')
    list_filter = ('plan', 'isPaid')
    


@admin.register(PlanModel)
class PlanModelAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'monthly_price')
    



@admin.register(AcquiredNames)
class AcquiredNamesAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')
    



@admin.register(SavedNames)
class SavedNamesAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')
    

@admin.register(ExtensionDropInfo)
class ExtensionDropInfoAdmin(admin.ModelAdmin):
    list_display = ('extension', 'first_check_delay_hours', 'second_check_delay_hours')
    






@admin.register(ArchivedName)
class ArchivedNameAdmin(admin.ModelAdmin):
    list_display = ('domain_name', 'extension', 'archived_on', 'original_drop_date')
    list_filter = ('extension', 'archived_on')
    search_fields = ('domain_name',)
    readonly_fields = ('domain_name', 'extension', 'original_drop_date', 'archived_on')

    fieldsets = (
        (None, {
            'fields': ('domain_name', 'extension', 'original_drop_date', 'archived_on')
        }),
    )