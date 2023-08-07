import base64
import datetime as dt

import webcolors
from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Achievement, AchievementCat, Cat


class Hex2NameColor(serializers.Field):
    """Color conversion from hex encoding to human-readable."""
    def to_representation(self, value):
        """Transform the *outgoing* native value into primitive data."""
        return value

    def to_internal_value(self, data):
        """Convert a hexadecimal color value to its readble color name,

        if any such name exists.
        """
        try:
            data = webcolors.hex_to_name(data)
        except ValueError:
            raise serializers.ValidationError('Для этого цвета нет имени')
        return data


class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for Achievement model."""
    achievement_name = serializers.CharField(source='name')

    class Meta:
        """Meta options for AchievementSerializer."""
        model = Achievement
        fields = ('id', 'achievement_name')


class Base64ImageField(serializers.ImageField):
    """Decode the Base64 encoded bytes-like object or ASCII string."""
    def to_internal_value(self, data):
        """Transform the *incoming* primitive data into a native value."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CatSerializer(serializers.ModelSerializer):
    """Serializer for Cat model."""
    achievements = AchievementSerializer(required=False, many=True)
    color = Hex2NameColor()
    age = serializers.SerializerMethodField()
    image = Base64ImageField(required=False, allow_null=True)
    image_url = serializers.SerializerMethodField(
        'get_image_url',
        read_only=True
    )

    class Meta:
        """Meta options for CatSerializer."""
        model = Cat
        fields = (
            'id', 'name', 'color', 'birth_year', 'achievements',
            'owner', 'age', 'image', 'image_url'
        )
        read_only_fields = ('owner',)

    def get_image_url(self, obj):
        """Get the URL of the cat's image."""
        if obj.image:
            return obj.image.url
        return None

    def get_age(self, obj):
        """Get the age of the cat."""
        return dt.datetime.now().year - obj.birth_year

    def create(self, validated_data):
        """Create a new cat with achievements list if exists."""
        if 'achievements' not in self.initial_data:
            cat = Cat.objects.create(**validated_data)
            return cat
        else:
            achievements = validated_data.pop('achievements')
            cat = Cat.objects.create(**validated_data)
            for achievement in achievements:
                current_achievement, _ = Achievement.objects.get_or_create(
                    **achievement
                    )
                AchievementCat.objects.create(
                    achievement=current_achievement, cat=cat
                    )
            return cat

    def update(self, instance, validated_data):
        """Update an existing cat."""
        instance.name = validated_data.get('name', instance.name)
        instance.color = validated_data.get('color', instance.color)
        instance.birth_year = validated_data.get(
            'birth_year', instance.birth_year
            )
        instance.image = validated_data.get('image', instance.image)
        if 'achievements' in validated_data:
            achievements_data = validated_data.pop('achievements')
            lst = []
            for achievement in achievements_data:
                current_achievement, _ = Achievement.objects.get_or_create(
                    **achievement
                    )
                lst.append(current_achievement)
            instance.achievements.set(lst)

        instance.save()
        return instance
