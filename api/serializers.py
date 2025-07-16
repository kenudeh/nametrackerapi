# Importing the default User model from Django
from django.contrib.auth.models import User
# Importing dj-rest default registration serializer from dj-rest-auth so I can override it and enforce email uniqueness
# from dj_rest_auth.registration.serializers import RegisterSerializer
# Importing dj-rest default login serializer
# from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from .models import AppUser, Name, UseCase, NameTag, NameCategory, PlanModel, Subscription, NewsLetter, PublicInquiry
import re



# ============================================
# App User Serializer (with nested serializers)
# ============================================
class PlanModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanModel
        fields = ["plan_type", "description", "api_quota", "monthly_price"]

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanModelSerializer()  # Nested plan info

    class Meta:
        model = Subscription
        fields = ["payment_status", "subscription_expiry", "isPaid", "plan"]



class AppUserSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)

    class Meta:
        model = AppUser
        fields = [
            "clerk_id",
            "email",
            "first_name",
            "last_name",
            "created_at",
        ]
        read_only_fields = ["clerk_id", "email", "created_at"]










# ===========================================================================================================
# Name Serializer - With related UseCaseSerializer, NameCategorySerializer and NameTagSerializer serilizers
# ===========================================================================================================
class NameTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = NameTag
        fields = ['id', 'name']

class NameCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NameCategory
        fields = ['id', 'name']

class UseCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UseCase
        fields = ['id', 'case_title', 'description', 'difficulty', 'competition', 'target_market', 'revenue_potential', 'order']



class NameSerializer(serializers.ModelSerializer):
    tag = NameTagSerializer(many=True)
    category = NameCategorySerializer()
    use_cases = UseCaseSerializer(many=True, source='use_cases_domain')

    class Meta:
        model = Name
        fields = ['id', 'domain_name', 'extension', 'domain_list', 'status', 'score', 'length', 'syllables',
                  'competition', 'difficulty', 'suggested_usecase', 'is_top_rated', 'is_favorite',
                  'category', 'tag', 'drop_date', 'drop_time', 'created_at', 'updated_at', 'use_cases']

    def create(self, validated_data):
        tag_data = validated_data.pop('tag')
        category_data = validated_data.pop('category')
        use_cases_data = validated_data.pop('use_cases_domain')

        # Get or create the category
        category_obj, _ = NameCategory.objects.get_or_create(**category_data)
        name = Name.objects.create(category=category_obj, **validated_data)

        # Handle tags
        for tag in tag_data:
            tag_obj, _ = NameTag.objects.get_or_create(**tag)
            name.tag.add(tag_obj)

        # Handle use cases (max 3 already validated)
        for use_case in use_cases_data:
            UseCase.objects.create(domain_name=name, **use_case)

        return name

    def update(self, instance, validated_data):
        tag_data = validated_data.pop('tag', None)
        category_data = validated_data.pop('category', None)
        use_cases_data = validated_data.pop('use_cases_domain', None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create category
        if category_data:
            category_obj, _ = NameCategory.objects.get_or_create(**category_data)
            instance.category = category_obj
            instance.save()

        # Update tags
        if tag_data:
            tag_objs = []
            for tag in tag_data:
                tag_obj, _ = NameTag.objects.get_or_create(**tag)
                tag_objs.append(tag_obj)
            instance.tag.set(tag_objs)

        # Update use cases
        if use_cases_data:
            instance.use_cases_domain.all().delete()  # Remove old use cases
            for use_case in use_cases_data:
                UseCase.objects.create(domain_name=instance, **use_case)

        return instance

    def validate_use_cases(self, value):
        """
        Validates that no more than 3 use cases are provided.
        """
        if len(value) > 3:
            raise serializers.ValidationError("A maximum of 3 use cases are allowed.")
        return value



# ============================================
# Newsletter Serializer
# ============================================
class NewsletterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    class Meta:
        model = NewsLetter
        fields = ['email', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        if NewsLetter.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already subscribed.")
        return value



# ============================================
# Public Inquiry Serializer
# ============================================
class PublicInquirySerializer(serializers.ModelSerializer):
    email = serializers.EmailField()

    class Meta:
        model = PublicInquiry
        fields = ['name', 'email', 'message', 'ip_address', 'created_at', 'updated_at']
        read_only_fields = ['ip_address', 'created_at', 'updated_at']

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value

    def validate_message(self, value):
        message = value.strip()
        
        # Check if message is empty
        if not message:
            raise serializers.ValidationError("Message cannot be empty.")

        # Check for URL-like patterns
        if re.search(r'https?://|www\.', message, re.IGNORECASE):
            raise serializers.ValidationError(
                "Messages containing links are not allowed. If you need to share a link, please reach out via official email."
            )

        # Check length
        if len(message) > 500:
            raise serializers.ValidationError("Message is too long. Please keep it under 500 characters.")

        return message















# Email validation serializer (To be used in settings.py) - Not in use as Auth is now with Clerk
# class CustomRegisterSerializer(RegisterSerializer):
#     email = serializers.EmailField(required=True)

#     def validate_email(self, value):
#         if User.objects.filter(email__iexact=value).exists():
#             raise serializers.ValidationError("An account with this email already exists.")
#         return value


#  Custom  login serializer to allow the frontend to submit either "email or username" in one field (Not in use anymore - Clerk now handles auth)
# class CustomLoginSerializer(LoginSerializer):
#     def authenticate(self, **kwargs):
#         login_value = kwargs.get(self.username_field)
#         if login_value:
#             kwargs['username'] = login_value
#             kwargs['email'] = login_value
#         return super().authenticate(**kwargs)

