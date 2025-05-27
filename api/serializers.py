from rest_framework import serializers
from .models import *
from django.core.cache import cache
import json





class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']
        
        


class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingModel
        fields = '__all__'
        


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name']
        
class TargetUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetUsers
        fields = ['id', 'name']
        


class ToolSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    pricing = PricingSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    target_users = TargetUsersSerializer(many=True, read_only=True)
    
    
    class Meta:
        model = Tool
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')  
        
    
    # Validation for website field
    def validate_website(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("invalide website URL format. Must start with http:// or https:// ")
        return value


    # Validation for tags
    def validate(self, data):
        if 'tags' in data and not data['tags']:
            raise serializers.ValidationError({"tags": "At least one tag must be provided."})
        return data
    
    
    """
     # Validating pricing
    def validate_pricing(self, value):
        valid_choices = [choice[0] for choice in Tool._meta.get_field('pricing').choices]
        if value not in valid_choices:
            raise serializers.ValidationError("invalid pricing option")
        return value
    
    # Validation for categories
    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("Category is required.")
        return value
    """
    
class ToolSuggestionSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    category = serializers.SlugRelatedField(  # New: Same pattern as pricing
        slug_field='name',  # Uses Category.name (from your model)
        queryset=Category.objects.all()
    )
    pricing = serializers.CharField()  # Allow any input
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[],
        write_only=True  # Critical for input only
    )

    
    # Explicitly declare all optional ManyToMany fields
    languages = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[],
        write_only=True
    )
    target_users = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[],
        write_only=True
    )
    features = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=[],
        write_only=True
    )
   
    class Meta:
        model = ToolSuggestion
        fields = [
            'id', 'name', 'email', 'tool_name', 'category',
            'description', 'website', 'pricing', 'tags', 'image',
            'languages', 'target_users', 'features', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'status')
        # Map our output field to the original name
        extra_kwargs = {
            'tag_names': {'source': 'tags'}
        }

    

    def get_tag_names(self, obj):
        """Safe serialization for output"""
        return list(obj.tags.values_list('name', flat=True))



    def validate_category(self, value):
        value = str(value).strip().lower()
        try:
            return Category.objects.get(name__iexact=value)
        except Category.DoesNotExist:
            valid_categories = [choice[0] for choice in CategoryType.choices]
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {valid_categories}"
            )
    
    
    def validate_pricing(self, value):
        # Try ID first
        try:
            return PricingModel.objects.get(pk=value)
        except (PricingModel.DoesNotExist, ValueError):
            # Try type string next
            try:
                return PricingModel.objects.get(type=value)
            except PricingModel.DoesNotExist:
                raise serializers.ValidationError("Invalid pricing: ID or type does not exist.")

    def validate_features(self, value):
        """Ensure features is always a list of strings"""
        if isinstance(value, str):  # Handle accidental string input
            return [value.strip()]
        return [str(item).strip() for item in value if str(item).strip()]
            

    def validate_tags(self, value):
        """Ensure tags are never JSON strings"""
        cleaned_tags = []
        for tag in value:
            if isinstance(tag, str) and tag.startswith('['):
                try:
                    cleaned_tags.extend(json.loads(tag))
                except json.JSONDecodeError:
                    cleaned_tags.append(tag)
            else:
                cleaned_tags.append(tag)
        return [tag.strip().lower() for tag in cleaned_tags if tag.strip()]
            
    
    def validate_image(self, value):
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError('File size must be less than 5MB.')
        return value
    
    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        instance = super().create(validated_data)
        
        tag_objs = []
        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
            tag_objs.append(tag)
        instance.tags.set(tag_objs)
        
        return instance

    
class UpdateToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateTool
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')



# SERILAIZERS FOR THE TOOL COMAPRISON FEATURE

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name']  

class TargetUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TargetUsers
        fields = ['id', 'name']  

        
class ToolComparisonSerializer(serializers.Serializer):
    """
    Serializer for the comparison data.
    """
    tool1 = serializers.SerializerMethodField()
    tool2 = serializers.SerializerMethodField()
    common_features = serializers.ListField(child=serializers.CharField())

    def get_tool1(self, obj):
        return self._get_tool_data(obj['tool1'])

    def get_tool2(self, obj):
        return self._get_tool_data(obj['tool2'])

    def _get_tool_data(self, tool):
        return {
            'tool_name': tool.tool_name,
            'description': tool.description,
            'pricing': tool.pricing.type if tool.pricing else "Not specified",
            'features': tool.features or [],  # Directly use ArrayField
            'languages': LanguageSerializer(tool.languages.all(), many=True).data,
            'target_users': TargetUserSerializer(tool.target_users.all(), many=True).data,
        }



# # USER PROFILE SERIALIZER
# class UserProfileSerializer(serializers.ModelSerializer):
#     submissions = ToolSuggestionSerializer(many=True, read_only=True)
#     my_favorites = ToolSerializer(many=True, read_only=True)
    
#     class Meta:
#         model = UserProfile
#         fields = ['first_name', 'last_name', 'email', 'submissions', 'my_favorites']
#         read_only_fields = ['email']  # Email should not be editable via this serializer


# class FavoriteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Favorite
#         fields = '__all__'
#         read_only_fields = ('created_at')
        


class FeaturedToolsSerializer(serializers.ModelSerializer):
    # Override foreign key fields to use nested serializers
    category = CategorySerializer()
    pricing = PricingSerializer()
    # Override many-to-many field to use nested serializer
    tags = TagSerializer(many=True)
    
    class Meta:
        model = Tool
        fields = [ 'tool_name',
            'category',
            'pricing',
            'description',
            'website', 
            'features', 
            'slug', 
            'image', 'tags'
        ]
    

# class ReviewSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Review
#         fields = '__all__'
#         read_only_fields = ('created_at', "id", "user", "tool_name", "is_approved", "created_at")
        
#     def validate(self, data):
#         # Get the current user and tool from the context
#         user = self.context["request"].user.userprofile
#         tool = self.context["tool"]

#         # Check if the user has already reviewed the tool
#         if Review.objects.filter(user=user, tool=tool).exists():
#             raise serializers.ValidationError("You have already submitted a review for this tool.")

#         return data
    
#     def validate_ratings(self, value):
#         if value < 1 or value > 5:
#             raise serializers.ValidationError("Ratings must be between 1 and 5.")
#         return value
    
#     def validate_comment(self, value):
#         if len(value) > 1000:
#             raise serializers.ValidationError("Comment cannot exceed 1000 characters.")
#         return value

        
        
# class PaidToolsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PaidTool
#         fields = '__all__'
#         read_only_fields = ('created_at', 'updated_at')
        

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