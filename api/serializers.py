# Importing the default User model from Django
from django.contrib.auth.models import User
# Importing dj-rest default registration serializer from dj-rest-auth so I can override it and enforce email uniqueness
# from dj_rest_auth.registration.serializers import RegisterSerializer
# Importing dj-rest default login serializer
# from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from .models import AppUser, Name, UseCase, UseCaseTag, UseCaseCategory, PlanModel, Subscription, NewsLetter, PublicInquiry, AcquiredName, SavedName
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
class UseCaseTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = UseCaseTag
        fields = ['id', 'name']

class UseCaseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UseCaseCategory
        fields = ['id', 'name']




class UseCaseSerializer(serializers.ModelSerializer):
    domain_name = serializers.SlugRelatedField(
        read_only=True,
        slug_field='domain_name'  # This is the field in the Name model to display
    )
    tag = UseCaseTagSerializer(many=True, read_only=True)
    category = UseCaseCategorySerializer(read_only=True)
    

    class Meta:
        model = UseCase
        fields = [
            'id', 'domain_name', 
            'case_title', 'slug', 'description', 
            "category", "tag",
            'difficulty', 'competition', 
            'target_market', 'revenue_potential', 
            'order'
        ]


    
    def validate(self, data):
        """
        Custom validation for UseCase creation or update.

        Ensures:
        - No more than 3 use cases per domain name.
        - Each use case has a unique `order` value between 1 and 3.
        """
        domain = data.get('domain_name')
        order = data.get('order')

        if not domain:
            # FK validation might happen later, so we catch it here just in case
            raise serializers.ValidationError("Each use case must belong to a domain.")

        # Get all existing use cases for this domain (excluding the one being updated, if any)
        existing_qs = UseCase.objects.filter(domain_name=domain)
        if self.instance:
            # Exclude current instance if updating
            existing_qs = existing_qs.exclude(pk=self.instance.pk)

        # Count check: only allow up to 3 use cases per domain
        if existing_qs.count() >= 3:
            raise serializers.ValidationError(
                f"Only 3 use cases are allowed per domain. "
                f"'{domain}' already has {existing_qs.count()}."
            )

        # Order uniqueness check
        if existing_qs.filter(order=order).exists():
            raise serializers.ValidationError(
                f"Use case with order={order} already exists for '{domain}'. "
                f"Each domain must have one use case for each of order 1, 2, and 3."
            )

        return data
        

        

# Suggested use case serializer
class SuggestedUseCaseSerializer(serializers.ModelSerializer):
    domain_name = serializers.SlugRelatedField(
        read_only=True,
        slug_field='domain_name'  # This is the field in the Name model to display
    )
    tag = UseCaseTagSerializer(many=True, read_only=True)
    category = UseCaseCategorySerializer(read_only=True)

    
    class Meta:
        model = UseCase
        fields = [
            'id', 'domain_name', 
            'case_title', 'slug', 'description', 
            "category", "tag",
            'difficulty', 'competition', 
            'target_market', 'revenue_potential', 
            'order'
        ]



class NameSerializer(serializers.ModelSerializer):
    suggested_usecase = SuggestedUseCaseSerializer(read_only=True)
    other_use_cases = serializers.SerializerMethodField()
    saved = serializers.SerializerMethodField()
    slug = serializers.CharField(source='domain_name', read_only=True)


    class Meta:
        model = Name
        fields = ['domain_name', 'extension', 'domain_list', 'status', 'score', 'length', 'syllables',
                'suggested_usecase', 'other_use_cases', 'is_idea_of_the_day', 'is_top_rated',
                'drop_date', 'created_at', 'updated_at', 'saved', 'slug'
        ]

    # Dynamically checks if the current user has saved the name.
    def get_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.savedname_set.filter(user=request.user).exists()
        return False

    # Exclude the suggested one (order=1)
    def get_other_use_cases(self, obj):
        return UseCaseSerializer(
            obj.use_cases.exclude(order=1), many=True
        ).data
        

    def create(self, validated_data):
        use_cases_data = validated_data.pop('use_cases_domain', [])

        name = Name.objects.create(**validated_data)

        for use_case in use_cases_data:
            tag_data = use_case.pop('tag', [])
            category_slug = use_case.pop('category', None)

            # Get or create the category
            if category_slug:
                try:
                    category_obj = NameCategory.objects.get(slug=category_slug)
                except NameCategory.DoesNotExist:
                    raise ValidationError(f"Category '{category_slug}' is invalid. Choose from predefined categories.")
            
            # Create use case
            use_case_obj = UseCase.objects.create(
                domain_name=name,
                category=category_obj,
                **use_case
            )

            # Handle tags
            for tag in tag_data:
                tag_obj, _ = NameTag.objects.get_or_create(**tag)
                use_case_obj.tag.add(tag_obj)

        return name


    def update(self, instance, validated_data):
        use_cases_data = validated_data.pop('use_cases_domain', None)

        # Update base fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if use_cases_data is not None:
            instance.use_cases_domain.all().delete()

            for use_case in use_cases_data:
                tag_data = use_case.pop('tag', [])
                category_data = use_case.pop('category', None)

                category_obj = None
                if category_data:
                    category_obj, _ = NameCategory.objects.get_or_create(**category_data)

                use_case_obj = UseCase.objects.create(
                    domain_name=instance,
                    category=category_obj,
                    **use_case
                )

                for tag in tag_data:
                    tag_obj, _ = NameTag.objects.get_or_create(**tag)
                    use_case_obj.tag.add(tag_obj)

        return instance




    def validate_use_cases(self, value):
        """
        Validates that no more than 3 use cases are provided.
        """
        if len(value) > 3:
            raise serializers.ValidationError("A maximum of 3 use cases are allowed.")
        return value



# ============================================
# Acquired Names Serializer
# ============================================
class AcquiredNameSerializer(serializers.ModelSerializer):
    name = NameSerializer(read_only=True)  # Embed the full name details

    class Meta:
        model = AcquiredName
        fields = ['id', 'name', 'created_at']



# ============================================
# Saved Names Serializer
# ============================================
class SavedNameLightSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='name.domain_name')
    extension = serializers.CharField(source='name.extension')
    domain_list = serializers.CharField(source='name.domain_list')
    slug = serializers.CharField(source='name.slug')
    status = serializers.CharField(source='name.status')
    created_at = serializers.DateTimeField(source='name.created_at')
    saved = serializers.SerializerMethodField()

    class Meta:
        model = SavedName
        fields = ['slug', 'domain_name', 'extension', 'domain_list', 'status', 'created_at', 'saved']

    def get_saved(self, obj):
        return True  # Always True because it's from the saved names list



# class SavedNameSerializer(serializers.ModelSerializer):
#     name = NameSerializer(read_only=True)  # Embed the full name details
#     saved = serializers.SerializerMethodField() # Anotating the saved field instead of creating a method field


#     class Meta:
#         model = SavedName
#         fields = ['id', 'name', 'created_at', 'saved']

    
#     def get_saved(self, obj):
#         return True  # Since it's from the SavedName model, it's always saved


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

