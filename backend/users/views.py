from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model, logout
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, JobSerializer, JobCreateSerializer, TaskSerializer, EarningsSerializer
from .serializers import BidSerializer, BidUpdateSerializer, TaskUpdateSerializer, MessageSerializer, MessageCreateSerializer, UserProfileSerializer
from .models import Job, Task, Earnings
from .models import Bid, Message
from .sms import send_job_notification_to_freelancers, safe_send_sms, send_sms

User = get_user_model()


class RegisterView(APIView):
    """
    User registration endpoint.
    POST: Create new user account
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
            except IntegrityError as e:
                return Response({
                    'success': False,
                    'errors': {'detail': str(e)},
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True,
                'message': 'User registered successfully.',
                'email': user.email,
                'role': user.role,
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    User login endpoint.
    POST: Authenticate user and create session
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'email': user.email,
                'role': user.role,
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors,
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """
    User logout endpoint.
    POST: Logout user and destroy session
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({
            'success': True,
            'message': 'Logout successful.',
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    Get current user profile.
    GET: Return authenticated user data
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data,
        }, status=status.HTTP_200_OK)


class ProfileUpdateView(generics.UpdateAPIView):
    """
    Update user profile.
    PATCH: Update user profile (name, phone, skills)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully.',
            'data': UserSerializer(instance).data,
        }, status=status.HTTP_200_OK)


class JobListCreateView(generics.ListCreateAPIView):
    """
    Jobs endpoint.
    GET: List jobs (filtered by user role)
    POST: Create new job (clients only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = JobSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'FREELANCER':
            # Freelancers see only open jobs
            return Job.objects.filter(status='OPEN')
        elif user.role == 'CLIENT':
            # Clients see their own jobs
            return Job.objects.filter(created_by=user).prefetch_related('bids__freelancer')
        return Job.objects.none()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return JobCreateSerializer
        return JobSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'CLIENT':
            raise PermissionDenied("Only clients can post jobs.")
        
        # Save the job
        job = serializer.save(created_by=user)
        
        # Send SMS notifications to freelancers (non-blocking)
        try:
            sms_stats = send_job_notification_to_freelancers(job)
            # Log SMS sending stats but don't fail the job creation
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Job {job.id} SMS notifications: {sms_stats}")
        except Exception as e:
            # Log error but don't interrupt job creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending SMS notifications for job {job.id}: {str(e)}")


class IsClientOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.is_authenticated and request.user.role == 'CLIENT'


class IsFreelancerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user.is_authenticated and request.user.role == 'FREELANCER'


class IsJobOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj in this view is Bid
        return request.user.is_authenticated and obj.job.created_by == request.user


class IsTaskOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # obj in this view is Task
        return request.user.is_authenticated and obj.freelancer == request.user


class BidListCreateView(generics.ListCreateAPIView):
    """
    Bids endpoint.
    POST: Freelancer creates a bid (freelancer set automatically).
    GET: List bids for authenticated user (freelancers get their bids, clients get bids on their jobs).
    """
    permission_classes = [IsAuthenticated, IsFreelancerOrReadOnly]
    serializer_class = BidSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'FREELANCER':
            return Bid.objects.filter(freelancer=user)
        if user.role == 'CLIENT':
            return Bid.objects.filter(job__created_by=user)
        return Bid.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'FREELANCER':
            raise PermissionDenied('Only freelancers can place bids.')
        
        # Save the bid
        bid = serializer.save(freelancer=user)
        
        # Send SMS notification to the client
        try:
            job = bid.job
            client = job.created_by
            
            if client.phone_number:
                message = f"You received a new bid on your job '{job.title}'. Check KaziLink to review it."
                sms_result = safe_send_sms(client.phone_number, message)
                
                # Log the SMS sending result
                import logging
                logger = logging.getLogger(__name__)
                if sms_result:
                    logger.info(f"Bid notification SMS sent to client {client.email} for job {job.id}")
                else:
                    logger.warning(f"Failed to send bid notification SMS to client {client.email}")
            else:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Client {client.email} has no phone number for bid notifications")
                
        except Exception as e:
            # Log error but don't interrupt bid creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending bid notification SMS: {str(e)}")


class JobBidsListView(generics.ListAPIView):
    """List all bids for a given job (client only)."""
    permission_classes = [IsAuthenticated, IsClientOrReadOnly]
    serializer_class = BidSerializer

    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, pk=job_id)
        if self.request.user != job.created_by:
            raise PermissionDenied('Only the client who owns the job can see bids.')
        return Bid.objects.filter(job=job)


class BidUpdateView(generics.UpdateAPIView):
    """Update bid status (client of the job only)."""
    permission_classes = [IsAuthenticated, IsJobOwner]
    serializer_class = BidUpdateSerializer
    queryset = Bid.objects.all()

    def perform_update(self, serializer):
        bid = serializer.instance
        job = bid.job
        if self.request.user != job.created_by:
            raise PermissionDenied('Only the job client can accept/reject bids.')

        # Save bid status change first
        updated_bid = serializer.save()

        # If bid is accepted, mark the job in-progress and create a task for freelancer
        if updated_bid.status == 'ACCEPTED':
            if job.status != 'IN_PROGRESS':
                job.status = 'IN_PROGRESS'
                job.save(update_fields=['status'])

            Task.objects.get_or_create(
                job=job,
                freelancer=updated_bid.freelancer,
                defaults={
                    'title': job.title,
                    'description': updated_bid.proposal,
                    'status': 'PENDING',
                }
            )

            # Optionally reject other pending bids for the same job
            Bid.objects.filter(job=job, status='PENDING').exclude(pk=updated_bid.pk).update(status='REJECTED')
            
            # Send SMS notification to freelancer
            freelancer = updated_bid.freelancer
            try:
                if freelancer.phone_number:
                    message = f"Your bid for '{job.title}' has been accepted! Start working on KaziLink."
                    sms_result = safe_send_sms(freelancer.phone_number, message)
                    
                    # Log the SMS sending result
                    import logging
                    logger = logging.getLogger(__name__)
                    if sms_result:
                        logger.info(f"Acceptance SMS sent to freelancer {freelancer.email} for job {job.id}")
                    else:
                        logger.warning(f"Failed to send acceptance SMS to freelancer {freelancer.email}")
                else:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Freelancer {freelancer.email} has no phone number for acceptance notifications")
                    
            except Exception as e:
                # Log error but don't interrupt bid acceptance
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending acceptance SMS: {str(e)}")
        

class TaskUpdateView(generics.UpdateAPIView):
    """Update task status (freelancer only)."""
    permission_classes = [IsAuthenticated, IsTaskOwner]
    serializer_class = TaskUpdateSerializer
    queryset = Task.objects.all()

    def perform_update(self, serializer):
        updated_task = serializer.save()
        if updated_task.status == 'COMPLETED':
            job = updated_task.job
            if job.status != 'COMPLETED':
                job.status = 'COMPLETED'
                job.save(update_fields=['status'])
class TaskListView(generics.ListAPIView):
    """
    Tasks endpoint.
    GET: List tasks for authenticated freelancer
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'FREELANCER':
            return Task.objects.filter(freelancer=user)
        return Task.objects.none()


class EarningsListView(generics.ListAPIView):
    """
    Earnings endpoint.
    GET: List earnings for authenticated freelancer
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EarningsSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'FREELANCER':
            return Earnings.objects.filter(freelancer=user)
        return Earnings.objects.none()


class MessageListCreateView(generics.ListCreateAPIView):
    """
    Messages endpoint.
    GET: List messages for authenticated user
    POST: Create new message
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related('sender', 'recipient', 'job')
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class JobMessagesListView(generics.ListCreateAPIView):
    """
    Job messages endpoint.
    GET: List messages for a specific job
    POST: Create new message for a specific job
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        job_id = self.kwargs['job_id']
        user = self.request.user
        return Message.objects.filter(
            job_id=job_id
        ).filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related('sender', 'recipient', 'job')
    
    def perform_create(self, serializer):
        job_id = self.kwargs['job_id']
        job = get_object_or_404(Job, id=job_id)
        serializer.save(sender=self.request.user, job=job)


class FreelancersListView(generics.ListAPIView):
    """
    Freelancers endpoint.
    GET: List all freelancers (clients only)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'CLIENT':
            # Clients can see all freelancers
            return User.objects.filter(role='FREELANCER')
        return User.objects.none()


@method_decorator(csrf_exempt, name='dispatch')
class SendSMSView(APIView):
    """
    SMS sending endpoint.
    POST: Send SMS to a phone number
    
    Request format:
    {
        "phone": "0707274525",  // Any format (normalized automatically)
        "message": "Hello!"
    }
    
    Response format:
    {
        "success": true,
        "messageId": "abc123",
        "phone": "+254707274525",
        "message": "Hello!",
        "cost": "KES 0.50"
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Send SMS to specified phone number."""
        try:
            # Parse JSON request
            data = json.loads(request.body)
            phone = data.get("phone", "").strip()
            message = data.get("message", "").strip()
            
            # Validate inputs
            if not phone:
                return Response({
                    "success": False,
                    "error": "Invalid request",
                    "details": "Phone number is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not message:
                return Response({
                    "success": False,
                    "error": "Invalid request",
                    "details": "Message is required"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Send SMS
            result = send_sms(phone, message)
            
            # Return appropriate status code based on result
            status_code = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
            
            return Response(result, status=status_code)
        
        except json.JSONDecodeError:
            return Response({
                "success": False,
                "error": "Invalid JSON",
                "details": "Request body must be valid JSON"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                "success": False,
                "error": "Internal server error",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
