import secrets
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with role-based access."""
    
    ROLE_CHOICES = [
        ('CLIENT', 'Client'),
        ('FREELANCER', 'Freelancer'),
    ]
    
    # Phone number validator for E.164 format
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Phone number must be entered in E.164 format: +[country code][number]. Up to 15 digits allowed.'
    )
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=20,
        validators=[phone_regex],
        default='+254000000000',
        help_text='Phone number in E.164 format (e.g., +254712345678)'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLIENT',
        help_text='User role: CLIENT or FREELANCER'
    )
    skills = models.TextField(
        blank=True,
        help_text='Comma-separated list of skills (for freelancers)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email


class Job(models.Model):
    """Job model for clients to post jobs."""
    
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Task(models.Model):
    """Task model for freelancers to manage their tasks."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='tasks')
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Earnings(models.Model):
    """Earnings model to track freelancer earnings.

    Existing rows have no payment. Optional links are filled only after a
    payment is confirmed and, later, when a payout record is created.
    """
    
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earnings')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='earnings')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    earned_at = models.DateTimeField(auto_now_add=True)
    payment = models.OneToOneField(
        'Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='earning',
    )
    payout = models.OneToOneField(
        'Payout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='earning',
    )
    
    class Meta:
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.freelancer.email} - ${self.amount}"


class Bid(models.Model):
    """Bid model for freelancers bidding on jobs."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bids')
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proposal = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bid({self.job.title} - {self.freelancer.email} - {self.amount})"


class Message(models.Model):
    """Message model for communication between clients and freelancers."""
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} to {self.recipient.email} on {self.job.title}"


def _generate_unique_reference(model, kind):
    """Build a public reference that does not expose the database id."""
    for _ in range(5):
        if kind == 'payment':
            reference = f"KZB-{timezone.localdate():%Y%m%d}-{secrets.token_hex(4).upper()}"
        else:
            reference = f"KZB-PAYOUT-{secrets.token_hex(6).upper()}"
        if not model.objects.filter(transaction_reference=reference).exists():
            return reference
    raise ValidationError('Could not generate a unique transaction reference.')


class Payment(models.Model):
    """Client payment for an accepted job.

    PAYMENT_RECEIVED is reserved for a confirmed payment. Creating this record
    does not confirm money movement. Payaza status handling will own that
    confirmation later; this model does not call Payaza.
    """

    PAYMENT_PENDING = 'PAYMENT_PENDING'
    PAYMENT_PROCESSING = 'PAYMENT_PROCESSING'
    PAYMENT_RECEIVED = 'PAYMENT_RECEIVED'
    PAYMENT_FAILED = 'PAYMENT_FAILED'
    PAYMENT_CANCELLED = 'PAYMENT_CANCELLED'
    STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Payment pending'),
        (PAYMENT_PROCESSING, 'Payment processing'),
        (PAYMENT_RECEIVED, 'Payment received'),
        (PAYMENT_FAILED, 'Payment failed'),
        (PAYMENT_CANCELLED, 'Payment cancelled'),
    ]
    ACTIVE_STATUSES = (
        PAYMENT_PENDING,
        PAYMENT_PROCESSING,
        PAYMENT_RECEIVED,
    )
    TRANSITIONS = {
        PAYMENT_PENDING: {PAYMENT_PROCESSING, PAYMENT_FAILED, PAYMENT_CANCELLED},
        PAYMENT_PROCESSING: {PAYMENT_RECEIVED, PAYMENT_FAILED, PAYMENT_CANCELLED},
        PAYMENT_RECEIVED: set(),
        PAYMENT_FAILED: set(),
        PAYMENT_CANCELLED: set(),
    }
    DEFAULT_CURRENCY = 'KES'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='payments')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_payments')
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='freelancer_payments')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    currency = models.CharField(max_length=3, default=DEFAULT_CURRENCY)
    transaction_reference = models.CharField(max_length=32, unique=True, editable=False)
    provider_transaction_reference = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PAYMENT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='payment_amount_positive',
            ),
            models.UniqueConstraint(
                fields=['job'],
                condition=models.Q(status__in=['PAYMENT_PENDING', 'PAYMENT_PROCESSING', 'PAYMENT_RECEIVED']),
                name='unique_active_payment_per_job',
            ),
        ]

    def __str__(self):
        return self.transaction_reference

    def save(self, *args, **kwargs):
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if not self.transaction_reference:
            self.transaction_reference = _generate_unique_reference(Payment, 'payment')
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'transaction_reference'}
        super().save(*args, **kwargs)

    def transition_to(self, new_status):
        """Move to a later payment state. Received means the payment is confirmed."""
        allowed = self.TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                {'status': f'Cannot change payment status from {self.status} to {new_status}.'}
            )
        with transaction.atomic():
            self.status = new_status
            self.save(update_fields=['status', 'updated_at'])
            if new_status == self.PAYMENT_RECEIVED:
                Earnings.objects.get_or_create(
                    payment=self,
                    defaults={
                        'freelancer': self.freelancer,
                        'job': self.job,
                        'amount': self.amount,
                    },
                )


class Payout(models.Model):
    """Freelancer payout prepared after a payment has been received.

    PAYOUT_PAID is reserved for a confirmed payout. Creating this record does
    not send money and does not call Payaza.
    """

    PAYOUT_PENDING = 'PAYOUT_PENDING'
    PAYOUT_PROCESSING = 'PAYOUT_PROCESSING'
    PAYOUT_PAID = 'PAYOUT_PAID'
    PAYOUT_FAILED = 'PAYOUT_FAILED'
    PAYOUT_CANCELLED = 'PAYOUT_CANCELLED'
    STATUS_CHOICES = [
        (PAYOUT_PENDING, 'Payout pending'),
        (PAYOUT_PROCESSING, 'Payout processing'),
        (PAYOUT_PAID, 'Payout paid'),
        (PAYOUT_FAILED, 'Payout failed'),
        (PAYOUT_CANCELLED, 'Payout cancelled'),
    ]
    ACTIVE_STATUSES = (
        PAYOUT_PENDING,
        PAYOUT_PROCESSING,
        PAYOUT_PAID,
    )
    TRANSITIONS = {
        PAYOUT_PENDING: {PAYOUT_PROCESSING, PAYOUT_FAILED, PAYOUT_CANCELLED},
        PAYOUT_PROCESSING: {PAYOUT_PAID, PAYOUT_FAILED, PAYOUT_CANCELLED},
        PAYOUT_PAID: set(),
        PAYOUT_FAILED: set(),
        PAYOUT_CANCELLED: set(),
    }
    METHOD_CHOICES = [
        ('MOBILE_MONEY', 'Mobile money'),
        ('BANK_TRANSFER', 'Bank transfer'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payouts')
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    currency = models.CharField(max_length=3)
    destination_country = models.CharField(max_length=2)
    destination_currency = models.CharField(max_length=3)
    payout_method = models.CharField(max_length=32, choices=METHOD_CHOICES)
    destination_reference = models.CharField(max_length=100, blank=True)
    transaction_reference = models.CharField(max_length=40, unique=True, editable=False)
    provider_transaction_reference = models.CharField(max_length=128, null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=PAYOUT_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='payout_amount_positive',
            ),
            models.UniqueConstraint(
                fields=['payment'],
                condition=models.Q(status__in=['PAYOUT_PENDING', 'PAYOUT_PROCESSING', 'PAYOUT_PAID']),
                name='unique_active_payout_per_payment',
            ),
        ]

    def __str__(self):
        return self.transaction_reference

    def save(self, *args, **kwargs):
        if self.payment_id:
            payment = self.payment
            if self.freelancer_id and self.freelancer_id != payment.freelancer_id:
                raise ValidationError(
                    {'freelancer': 'Payout freelancer must match the payment freelancer.'}
                )
            self.freelancer = payment.freelancer
            self.amount = payment.amount
            self.currency = payment.currency
        if self.amount is None or self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be greater than zero.'})
        if not self.transaction_reference:
            self.transaction_reference = _generate_unique_reference(Payout, 'payout')
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'transaction_reference'}
        super().save(*args, **kwargs)

    def transition_to(self, new_status):
        """Move to a later payout state. Paid means the payout is confirmed."""
        allowed = self.TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValidationError(
                {'status': f'Cannot change payout status from {self.status} to {new_status}.'}
            )
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
