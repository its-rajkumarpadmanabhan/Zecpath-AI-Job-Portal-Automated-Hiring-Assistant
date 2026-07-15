from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User,Job,Application

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'title', 'company', 'description', 'posted_by', 'created_at']
        read_only_fields = ['posted_by']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'job', 'status', 'applied_at']  # candidate is set server-side, not from input