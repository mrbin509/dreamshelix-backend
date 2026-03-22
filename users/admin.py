from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Withdrawal, Transaction, Payment


# 👤 CUSTOM USER ADMIN
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Admin panel for CustomUser
    """

    model = CustomUser

    list_display = (
        'id',
        'username',
        'email',
        'referred_by',
        'active_income',
        'passive_income',
        'is_verified',
        'is_paid',
        'is_staff'
    )

    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'is_verified',
        'is_paid'
    )

    search_fields = ('username', 'email', 'referral_code')
    ordering = ('-id',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),

        ('Referral Info', {
            'fields': (
                'referral_code',
                'referred_by',
                'active_income',
                'passive_income'
            )
        }),

        ('Verification', {
            'fields': ('is_verified', 'is_paid')
        }),

        ('Permissions', {
            'fields': (
                'is_staff',
                'is_active',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),

        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'password1',
                'password2',
                'is_staff',
                'is_active'
            ),
        }),
    )


# 💸 WITHDRAWAL ADMIN
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'status', 'created_at']
    list_filter = ['status']
    actions = ['approve_withdrawal']

    def approve_withdrawal(self, request, queryset):
        success = 0
        failed = 0

        for withdrawal in queryset:
            try:
                withdrawal.approve()
                success += 1
            except Exception:
                failed += 1

        self.message_user(
            request,
            f"{success} withdrawals approved, {failed} failed",
            messages.SUCCESS
        )

    approve_withdrawal.short_description = "Approve selected withdrawals"


# 💰 TRANSACTION ADMIN
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'transaction_type', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['user__email']


# 💳 PAYMENT ADMIN
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'is_verified', 'created_at']
    list_filter = ['is_verified']
    search_fields = ['user__email', 'razorpay_order_id']