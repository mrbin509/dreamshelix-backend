"""
DreamsHelix Models
- Custom User Model with Referral + OTP + Payment
- Transaction System (income tracking)
- Withdrawal System (admin approval)
- Payment System (Razorpay integration)
"""

import random
import string
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings


# 🔐 Generate unique referral code (FIXED: no circular import)
def generate_referral_code():
    prefix = "DH"
    length = 6

    while True:
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        code = f"{prefix}{random_part}"

        if not CustomUser.objects.filter(referral_code=code).exists():
            return code


# 👤 Custom User Model
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    referral_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        db_index=True
    )

    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )

    # 🔐 Verification
    is_verified = models.BooleanField(default=False)

    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    # 💰 Earnings
    active_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    passive_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # 💳 Payment
    is_paid = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    # 🔐 OTP validation
    def is_otp_valid(self):
        if not self.otp_created_at:
            return False
        return timezone.now() <= self.otp_created_at + timedelta(minutes=5)

    # 🔐 Auto-generate referral code
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)

    # 🔗 Referral link (FIXED: dynamic)
    def get_referral_link(self):
        base_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return f"{base_url}/register?ref={self.referral_code}"

    def __str__(self):
        return self.email


# Shortcut
User = settings.AUTH_USER_MODEL


# 💰 Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPE = (
        ('ACTIVE', 'Active Income'),
        ('PASSIVE', 'Passive Income'),
        ('WITHDRAWAL', 'Withdrawal'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPE)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['transaction_type']),
        ]

    def __str__(self):
        return f"{self.user} - {self.transaction_type} - ₹{self.amount}"


# 💸 Withdrawal Model
class Withdrawal(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    upi_id = models.CharField(max_length=100)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - ₹{self.amount} - {self.status}"

    def approve(self):
        """
        Approve withdrawal and deduct balance
        """
        if self.status != 'PENDING':
            return

        user = self.user
        total_balance = user.active_income + user.passive_income

        if self.amount > total_balance:
            raise ValueError("Insufficient balance")

        # ✅ SAFE deduction logic (no negative values)
        if user.active_income >= self.amount:
            user.active_income -= self.amount
        else:
            remaining = self.amount - user.active_income
            user.active_income = 0

            if user.passive_income >= remaining:
                user.passive_income -= remaining
            else:
                raise ValueError("Insufficient passive balance")

        user.save()

        self.status = 'APPROVED'
        self.processed_at = timezone.now()
        self.save()

        # 💰 Log transaction
        Transaction.objects.create(
            user=user,
            amount=self.amount,
            transaction_type='WITHDRAWAL',
            description="Withdrawal processed"
        )


# 💳 Payment Model
class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    razorpay_order_id = models.CharField(max_length=255)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - ₹{self.amount} - {'Verified' if self.is_verified else 'Pending'}"