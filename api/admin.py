# admin.py
from django.contrib import admin
from .models import Name, AppUser, UseCaseCategory, UseCaseTag, UseCase, ArchivedName, Subscription, PlanModel, AcquiredName, SavedName, ExtensionDropInfo, PublicInquiry, NewsLetter, IdeaOfTheDay, UploadedFile
from .tasks import process_pending_files


# Inline for UseCase - allows adding up to 3 UseCases directly in the Name admin page.
class UseCaseInline(admin.StackedInline):
    model = UseCase
    extra = 0  # No extra empty forms by default
    max_num = 3  # Enforce maximum of 3 UseCases per Name
    min_num = 1  # Must have at least 1 UseCase (enforced via serializer but safe reminder here)
    show_change_link = True  # Allow jumping into UseCase admin from here

# Since 'category' is now ForeignKey, no inline needed.

# Inline for ManyToMany Tag relation (optional, as filter_horizontal can also be used)
# class UseCaseTagInline(admin.TabularInline):
#     model = UseCase.tag.through  # This is the intermediary model between UseCase and NameTag
#     extra = 1



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
    list_display = ( #removed 'competition' and 'difficulty'
        'domain_name',  
        'extension',
        'domain_list',
        'status',
        'length',
        'syllables',
        'score',
        'is_idea_of_the_day',
        'is_top_rated',
        'is_favorite',
        'drop_date',
        'created_at',
    )
    list_display_links = ('domain_name',) 
    list_filter = (  #removed 'category'
        'extension',
        'domain_list',
        'status',
        'score',
        'is_idea_of_the_day',
        'is_top_rated',
        'is_favorite',
    )
    search_fields = ('domain_name',)  
    date_hierarchy = 'drop_date'
    inlines = [UseCaseInline]  #Removed UseCaseTagInline ||| Inlines for UseCase and Tags
    # filter_horizontal = ('tag',)  # Easier multi-select for tags
    actions = [archive_selected_names]

    fieldsets = (
        (None, { 
            'fields': ('domain_name', 'domain_list', 'status')
        }),
        ('Metrics', {
            'fields': ('is_idea_of_the_day', 'is_top_rated', 'is_favorite')  #removed 'competition' and 'difficulty'
        }),
        ('Relations', {
            'fields': ('suggested_usecase',) #removed 'category'  # Category is FK, suggested_usecase auto-set
        }),
        ('Timing', {
            'fields': ('drop_date',)
        }),
    )


@admin.register(AppUser)
class AppUser(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email')
   

@admin.register(UseCaseCategory)
class UseCaseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id')
    search_fields = ('name',)

@admin.register(UseCaseTag)
class UseCaseTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):
    list_display = ('case_title', 'domain_name', 'category', 'order', 'difficulty', 'competition', 'revenue_potential')
    list_filter = ('difficulty', 'competition', 'revenue_potential')
    search_fields = ('case_title', 'target_market')


@admin.register(IdeaOfTheDay)
class IdeaOfTheDayAdmin(admin.ModelAdmin):
    list_display = ('use_case', 'drop_date', 'domain_list')
   

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'subscription_expiry', 'isPaid')
    list_filter = ('plan', 'isPaid')
    


@admin.register(PlanModel)
class PlanModelAdmin(admin.ModelAdmin):
    list_display = ('plan_type', 'monthly_price')
    



@admin.register(AcquiredName)
class AcquiredNameAdmin(admin.ModelAdmin):
    list_display = ('user', 'name')
    



@admin.register(SavedName)
class SavedNameAdmin(admin.ModelAdmin):
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



@admin.register(NewsLetter)
class NewsLetterAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'updated_at')


@admin.register(PublicInquiry)
class PublicInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message', 'ip_address', 'created_at')
    readonly_fields = ('ip_address', 'created_at', 'updated_at')



@admin.action(description="Process selected files NOW")
def process_files_immediately(modeladmin, request, queryset):
    from .utils import process_file
    for obj in queryset.filter(processed=False):
        try:
            process_file(obj)
            obj.processing_method = 'manual'
            obj.save()
            modeladmin.message_user(request, f"Processed {obj.filename}")
        except Exception as e:
            modeladmin.message_user(request, f"Failed {obj.filename}: {str(e)}", level='error')


class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'processed', 'uploaded_at')
    actions = [process_files_immediately]   # This adds the action to the admin dropdown
    readonly_fields = ('processed_at',)

admin.site.register(UploadedFile, UploadedFileAdmin)


