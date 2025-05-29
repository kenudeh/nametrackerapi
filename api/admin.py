from django.contrib import admin, messages
from .models import *
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.db import transaction



# Register your models here.
class CategoryAdmin(admin.ModelAdmin):
    pass
admin.site.register(Category, CategoryAdmin)


# Tag admin class
class TagAdmin(admin.ModelAdmin):
    pass
admin.site.register(Tag, TagAdmin)






# Support admin class
class SupportAdmin(admin.ModelAdmin):
    list_display = ('subject','created_at')
admin.site.register(Support, SupportAdmin)




