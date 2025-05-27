from django.contrib import admin, messages
from .models import PricingModel, Support, UpdateTool, ToolSuggestion, Tool, TargetUsers, Language, Tag, Category

from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.db import transaction



# Register your models here.
  

    # Future Usage    
# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):  
#     pass



# class BookmarksAdmin(admin.ModelAdmin):
#     list_display = ('user', 'tool', 'created_at')
#     ordering = ('-created_at',) # Order by most recent messages first
    
# admin.site.register(Favorite,BookmarksAdmin)



class CategoryAdmin(admin.ModelAdmin):
    pass
admin.site.register(Category, CategoryAdmin)


# Tag admin class
class TagAdmin(admin.ModelAdmin):
    pass
admin.site.register(Tag, TagAdmin)


# Supported languages admin class
class LanguageAdmin(admin.ModelAdmin):
    pass
admin.site.register(Language, LanguageAdmin)


# Target Users admin class
class TargetUsersAdmin(admin.ModelAdmin):
    pass
admin.site.register(TargetUsers, TargetUsersAdmin)


# Tool admin class
class ToolAdmin(admin.ModelAdmin):
    list_display = ('tool_name',
        'get_category',
        'get_pricing',
        'status',
        'image_preview')
    search_fields = ('tool_name',)
    
    def get_category(self, obj):
        if obj.category:
            # For ChoiceField - get the display value
            if hasattr(obj.category, 'get_type_display'):
                return obj.category.get_type_display()
            # For regular ForeignKey
            return str(obj.category)
        return None
    get_category.short_description = 'Category'
    
    def get_pricing(self, obj):
        return obj.pricing.type if obj.pricing else None  # or .name if that's the field
    get_pricing.short_description = 'Pricing'
    get_pricing.admin_order_field = 'pricing__type'
    
    # Tags are cluttering the admin view for tools, so I took it out
    # def get_tags(self, obj):
    #     return ", ".join([t.name for t in obj.tags.all()]) if obj.tags.exists() else None
    # get_tags.short_description = 'Tags'
    
    
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Image Preview"
    
admin.site.register(Tool, ToolAdmin)



#***************************ToolSuggestion admin class*****************************
class ToolSuggestionAdmin(admin.ModelAdmin):
    list_display = ('tool_name', 'status', 'created_at', 'action_buttons', 'get_category', 'get_pricing', 'image_preview')
    list_filter = ('status', 'created_at')
    search_fields = ('tool_name', 'features')
    actions = ['approve_selected', 'reject_selected']
    
    
    def get_category(self, obj):
        return obj.category.name if obj.category else None
    get_category.short_description = 'Category'
    
    def get_pricing(self, obj):
        return obj.pricing.type if obj.pricing else None
    get_pricing.short_description = 'Pricing'
    
    
    
    def action_buttons(self, obj):
        """Displays Approve and Reject buttons in the admin panel for each row."""
        if obj.status == 'pending':
            approve_url = f'approve/{obj.id}/'
            reject_url = f'reject/{obj.id}/'
            
            return format_html(
                '<a class="button" href="{}" style="margin-right: 10px; background:green; color:white; padding:5px 10px;">Approve</a>'
                '<a class="button" href="{}" style="background:red; color:white; padding:5px 10px;">Reject</a>',
                approve_url, reject_url
            )
        return "Action taken"
    
    action_buttons.allow_tags = True
    action_buttons.short_description = "Actions"
            
        
    from django.db import transaction

    def approve_tool(self, request, tool_id):
        try:
            with transaction.atomic():  # Start transaction
                obj = get_object_or_404(ToolSuggestion, id=tool_id, status='pending')
                
                # Create new tool (slug auto-generated in save())
                new_tool = Tool.objects.create(
                    tool_name=obj.tool_name,
                    description=obj.description,
                    website=obj.website,
                    category=obj.category,
                    pricing=obj.pricing,
                    features=obj.features,
                    name=obj.name,
                    email=obj.email,
                    image=obj.image,  # shared reference
                    status='approved'
                )
                
                # Copy M2M relationships
                new_tool.tags.set(obj.tags.all())
                new_tool.languages.set(obj.languages.all())
                new_tool.target_users.set(obj.target_users.all())
                
                # Update original status
                obj.status = 'approved'
                obj.save()
                
        except Exception as e:
            # Optional: log the error
            self.message_user(request, f"Approval failed: {str(e)}", messages.ERROR)
            return redirect('/admin/api/toolsuggestion/')
        
        self.message_user(request, f"'{obj.tool_name}' approved successfully", messages.SUCCESS)
        return redirect('/admin/api/toolsuggestion/')


    
    def reject_tool(self, request, tool_id):
        """Handles single tool rejection via admin button."""
        obj = get_object_or_404(ToolSuggestion, id=tool_id, status='pending')
        obj.status = 'rejected'
        obj.save()

        self.message_user(request, f"'{obj.tool_name}' has been rejected.", messages.WARNING)
        return redirect('/admin/api/toolsuggestion/')  
    
    
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Image Preview"
    
    
    def get_urls(self):
        """Adds custom URLs for approving and rejecting tools."""
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:tool_id>/', self.admin_site.admin_view(self.approve_tool), name="approve_tool"),
            path('reject/<int:tool_id>/', self.admin_site.admin_view(self.reject_tool), name="reject_tool"),
        ]
        
        return custom_urls + urls
    
admin.site.register(ToolSuggestion, ToolSuggestionAdmin)
        
        
# Tool Update Admin
class UpdateToolAdmin(admin.ModelAdmin):
    list_display = ["id", "tool_name","message", "created_at"]

admin.site.register(UpdateTool, UpdateToolAdmin)

    # Future Usage    
# Review admin class
# class ReviewAdmin(admin.ModelAdmin):
#     list_display = ["id", "user", "tool_name", "ratings", "is_approved", "created_at"]
#     list_editable = ["is_approved"]  # Allow editing is_approved directly from the list view
#     list_filter = ["is_approved", "tool_name"]
#     actions = ["approve_reviews"]

#     def approve_reviews(self, request, queryset):
#         """
#         Custom admin action to approve selected reviews.
#         """
#         queryset.update(is_approved=True)
#         self.message_user(request, f"{queryset.count()} reviews were approved.")
#     approve_reviews.short_description = "Approve selected reviews"
    
# admin.site.register(Review, ReviewAdmin)


    # Future Usage    
# Subscription admin class
# class PaidToolsAdmin(admin.ModelAdmin):
#     pass
# admin.site.register(PaidTool, PaidToolsAdmin)



# Support admin class
class SupportAdmin(admin.ModelAdmin):
    list_display = ('subject','created_at')
admin.site.register(Support, SupportAdmin)


class PricingAdmin(admin.ModelAdmin):
    list_display = ('type',)
admin.site.register(PricingModel, PricingAdmin)


