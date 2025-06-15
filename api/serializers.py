# serializers.py
from rest_framework import serializers
from .models import Name, UseCase, NameTag, NameCategory

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
        fields = ['id', 'domain_name', 'extension', 'domain_list', 'status', 'length', 'syllables',
                  'competition', 'difficulty', 'suggested_usecase', 'is_top_rated', 'is_favorite',
                  'category', 'tag', 'drop_date', 'drop_time', 'created_at', 'updated_at', 'use_cases']

    def create(self, validated_data):
        tag_data = validated_data.pop('tag')
        category_data = validated_data.pop('category')
        use_cases_data = validated_data.pop('use_cases_domain')

        category_obj, _ = NameCategory.objects.get_or_create(**category_data)
        name = Name.objects.create(category=category_obj, **validated_data)

        for tag in tag_data:
            tag_obj, _ = NameTag.objects.get_or_create(**tag)
            name.tag.add(tag_obj)

        for use_case in use_cases_data:
            UseCase.objects.create(domain_name=name, **use_case)

        return name

    def validate_use_cases_domain(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("A maximum of 3 use cases are allowed.")
        return value