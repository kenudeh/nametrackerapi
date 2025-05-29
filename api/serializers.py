from rest_framework import serializers
from .models import *
from django.core.cache import cache
import json





class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
        
        


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']






class NewsLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsLetter
        fields = ['email',]
        extra_kwargs = {
            'email': {
                'error_messages' : {
                    'unique' : 'This email is already subscribed!'
                }
            }
        }
        
    

# Request Serializer
class SupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Support
        fields = ['id', 'subject', 'message', 'email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_subject(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Subject must be at least 5 characters long.")
        return value

    def validate_message(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value