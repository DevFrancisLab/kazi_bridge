from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.db import IntegrityError
from .models import Job, Task, Earnings, Bid, Message

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    phone_number = serializers.CharField(
        max_length=20,
        help_text='Phone number in E.164 format (e.g., +254712345678)'
    )
    
    class Meta:
        model = User
        fields = ('email', 'password', 'phone_number', 'role')
        extra_kwargs = {
            'role': {'required': True},
            'phone_number': {'required': True},
        }
    
    def validate_phone_number(self, value):
        """Validate and normalize phone number to E.164 format."""
        import re
        
        # Remove any non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Check if it starts with + or country code
        if not cleaned.startswith('+'):
            # Assume it's a Kenyan number if no country code
            if cleaned.startswith('0'):
                cleaned = '+254' + cleaned[1:]
            elif len(cleaned) == 9:
                # Assume local number without 0
                cleaned = '+254' + cleaned
            else:
                cleaned = '+' + cleaned
        
        # Validate format: +[1-3 digits country code][number]
        if not re.match(r'^\+\d{1,3}\d{6,14}$', cleaned):
            raise serializers.ValidationError(
                'Phone number must be in E.164 format (e.g., +254712345678 or +1234567890)'
            )
        
        return cleaned
    
    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user with hashed password and normalized phone number."""
        password = validated_data.pop('password')
        phone_number = validated_data.pop('phone_number', '')

        # Ensure username is set for AbstractUser unique username constraint.
        validated_data['username'] = validated_data.get('email', '')
        validated_data.setdefault('first_name', '')
        validated_data['phone_number'] = phone_number

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    phone_number = serializers.CharField(
        max_length=20,
        help_text='Phone number in E.164 format (e.g., +254712345678)'
    )
    
    class Meta:
        model = User
        fields = ('email', 'password', 'phone_number', 'role')
        extra_kwargs = {
            'role': {'required': True},
            'phone_number': {'required': True},
        }
    
    def validate_phone_number(self, value):
        """Validate and normalize phone number to E.164 format."""
        import re
        
        # Remove any non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Check if it starts with + or country code
        if not cleaned.startswith('+'):
            # Assume it's a Kenyan number if no country code
            if cleaned.startswith('0'):
                cleaned = '+254' + cleaned[1:]
            elif len(cleaned) == 9:
                # Assume local number without 0
                cleaned = '+254' + cleaned
            else:
                cleaned = '+' + cleaned
        
        # Validate format: +[1-3 digits country code][number]
        if not re.match(r'^\+\d{1,3}\d{6,14}$', cleaned):
            raise serializers.ValidationError(
                'Phone number must be in E.164 format (e.g., +254712345678 or +1234567890)'
            )
        
        return cleaned
    
    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user with hashed password and normalized phone number."""
        password = validated_data.pop('password')
        phone_number = validated_data.pop('phone_number', '')

        # Ensure username is set for AbstractUser unique username constraint.
        validated_data['username'] = validated_data.get('email', '')
        validated_data.setdefault('first_name', '')
        validated_data['phone_number'] = phone_number

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, data):
        """Validate user credentials."""
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            raise serializers.ValidationError({
                'email': 'Email and password are required.'
            })
        
        # Authenticate using email
        user = authenticate(username=email, password=password)
        
        if not user:
            raise serializers.ValidationError({
                'email': 'Invalid email or password.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'email': 'User account is disabled.'
            })
        
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data (read-only)."""
    
    class Meta:
        model = User
        fields = ('id', 'email', 'phone_number', 'first_name', 'last_name', 'role', 'skills', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (including skills)."""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'skills')
        extra_kwargs = {
            'phone_number': {'required': False},
            'skills': {'required': False},
        }


class JobSerializer(serializers.ModelSerializer):
    """Serializer for Job model."""
    created_by = UserSerializer(read_only=True)
    freelancer = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = ('id', 'title', 'description', 'budget', 'deadline', 'created_by', 'status', 'created_at', 'freelancer')
        read_only_fields = ('id', 'created_at', 'created_by', 'freelancer')
    
    def get_freelancer(self, obj):
        """Get the freelancer for jobs in progress."""
        if obj.status == 'IN_PROGRESS':
            accepted_bid = obj.bids.filter(status='ACCEPTED').first()
            if accepted_bid:
                return {
                    'id': accepted_bid.freelancer.id,
                    'email': accepted_bid.freelancer.email,
                    'role': accepted_bid.freelancer.role
                }
        return None


class JobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating jobs."""
    
    class Meta:
        model = Job
        fields = ('title', 'description', 'budget', 'deadline')
    
    def create(self, validated_data):
        """Create job with client set to current user."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    
    job = JobSerializer(read_only=True)
    freelancer = UserSerializer(read_only=True)
    
    class Meta:
        model = Task
        fields = ('id', 'title', 'description', 'job', 'freelancer', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating only task status."""

    class Meta:
        model = Task
        fields = ('status',)

    def validate_status(self, value):
        valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of {', '.join(valid_statuses)}.")
        return value


class EarningsSerializer(serializers.ModelSerializer):
    """Serializer for Earnings model."""
    
    freelancer = UserSerializer(read_only=True)
    job = JobSerializer(read_only=True)
    
    class Meta:
        model = Earnings
        fields = ('id', 'freelancer', 'job', 'amount', 'earned_at')
        read_only_fields = ('id', 'earned_at')


class BidSerializer(serializers.ModelSerializer):
    """Serializer for Bid model (read/write)."""

    freelancer = UserSerializer(read_only=True)
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.all())

    class Meta:
        model = Bid
        fields = ('id', 'job', 'freelancer', 'amount', 'proposal', 'status', 'created_at')
        read_only_fields = ('id', 'created_at', 'freelancer', 'status')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['freelancer'] = request.user
        return super().create(validated_data)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be greater than zero.")
        return value


class BidUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating bid status (client only)."""

    class Meta:
        model = Bid
        fields = ('status',)

    def validate_status(self, value):
        if value not in ['ACCEPTED', 'REJECTED']:
            raise serializers.ValidationError("Status must be ACCEPTED or REJECTED.")
        return value


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages between clients and freelancers."""
    
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    
    class Meta:
        model = Message
        fields = ('id', 'job', 'sender', 'recipient', 'content', 'created_at', 'is_read', 'sender_email', 'recipient_email')
        read_only_fields = ('id', 'created_at', 'sender_email', 'recipient_email')
    
    def create(self, validated_data):
        """Set sender to current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['sender'] = request.user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages."""
    
    class Meta:
        model = Message
        fields = ('job', 'recipient', 'content')
    
    def validate(self, data):
        """Validate that sender and recipient are different and have valid relationship."""
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            raise serializers.ValidationError("Authentication required.")
        
        sender = request.user
        recipient = data['recipient']
        job = data['job']
        
        # Check if sender and recipient are different
        if sender == recipient:
            raise serializers.ValidationError("Cannot send message to yourself.")
        
        # Check if both users are involved with the job
        if sender.role == 'CLIENT' and job.created_by != sender:
            raise serializers.ValidationError("You can only send messages for your own jobs.")
        
        if sender.role == 'FREELANCER':
            # Check if freelancer has a bid on this job or is assigned to a task
            has_bid = Bid.objects.filter(job=job, freelancer=sender).exists()
            has_task = Task.objects.filter(job=job, freelancer=sender).exists()
            if not has_bid and not has_task:
                raise serializers.ValidationError("You can only send messages for jobs you've bid on or are assigned to.")
        
        # Check if recipient is the other party in the job
        if recipient.role == 'CLIENT' and job.created_by != recipient:
            raise serializers.ValidationError("Invalid recipient for this job.")
        
        if recipient.role == 'FREELANCER':
            has_bid = Bid.objects.filter(job=job, freelancer=recipient).exists()
            has_task = Task.objects.filter(job=job, freelancer=recipient).exists()
            if not has_bid and not has_task:
                raise serializers.ValidationError("Invalid recipient for this job.")
        
        return data
