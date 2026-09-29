from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Payment, Payout, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin with role field."""
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Role', {'fields': ('role',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'password1', 'password2', 'role'),
        }),
    )
    
    list_display = ('email', 'first_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_reference',
        'job',
        'amount',
        'currency',
        'status',
        'created_at',
    )
    list_filter = ('status', 'currency')
    search_fields = ('transaction_reference',)
    readonly_fields = (
        'transaction_reference',
        'provider_transaction_reference',
        'created_at',
        'updated_at',
    )


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_reference',
        'payment',
        'amount',
        'currency',
        'destination_country',
        'payout_method',
        'status',
        'created_at',
    )
    list_filter = ('status', 'currency', 'destination_country', 'payout_method')
    search_fields = ('transaction_reference',)
    readonly_fields = (
        'transaction_reference',
        'provider_transaction_reference',
        'created_at',
        'updated_at',
    )
