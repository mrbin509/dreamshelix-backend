"""
Serializers for DreamsHelix
- Secure signup with fraud detection
- OTP system
- Login with JWT
- Wallet + transaction serializers
"""

from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Transaction, Withdrawal
from .fraud_utils import (
    is_disposable_email,
    is_suspicious_email,
    is_ip_suspicious,
    is_referral_farming,
    is_multi_account,
    get_valid_referrer,
    is_self_referral
)
from .utils import generate_otp

User = get_user_model()


# 🔐 REGISTER SERIALIZER
# 🔐 REGISTER SERIALIZER
# 🔐 REGISTER SERIALIZER
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'referral_code')

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        password2 = data.get('password2')

        # ✅ Password match
        if password != password2:
            raise serializers.ValidationError("Passwords do not match")

        # 🚫 Fraud checks
        if is_disposable_email(email):
            raise serializers.ValidationError("Disposable emails are not allowed")

        if is_suspicious_email(email):
            raise serializers.ValidationError("Suspicious email pattern detected")

        if is_multi_account(email):
            raise serializers.ValidationError("Multiple account attempt detected")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        ip = request.META.get('REMOTE_ADDR')

        referral_code = validated_data.pop('referral_code', None)
        validated_data.pop('password2')

        email = validated_data.get('email')

        # 🚫 IP fraud check
        if is_ip_suspicious(ip):
            raise serializers.ValidationError("Too many accounts from this IP")

        # 🚫 Self referral
        if referral_code:
            if is_self_referral(email, referral_code):
                raise serializers.ValidationError("You cannot refer yourself")

        # ✅ Create user
        user = User.objects.create_user(**validated_data)

        # 🔐 Generate OTP
        user.otp = generate_otp()
        user.otp_created_at = timezone.now()
        user.save()

        # 🔥 DEBUG (IMPORTANT)
        print("🔥 OTP GENERATED:", user.otp)

        # 📩 Send Email (SAFE VERSION — WILL NOT BREAK API)
        try:
            send_mail(
                subject='DreamsHelix OTP Verification',
                message=f'Your OTP is {user.otp}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=True,   # ✅ CRITICAL FIX
            )
        except Exception as e:
            print("❌ EMAIL ERROR:", str(e))

        # ✅ Store referral
        if referral_code:
            request.session['pending_referral'] = referral_code

        return user


# 🔐 LOGIN SERIALIZER
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_verified:
            raise serializers.ValidationError("Please verify your email first")

        # 🔒 Optional: block unpaid users (if needed later)
        # if not user.is_paid:
        #     raise serializers.ValidationError("Please purchase the course first")

        refresh = RefreshToken.for_user(user)

        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


# 👤 USER SERIALIZER
class UserSerializer(serializers.ModelSerializer):
    referrals_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'active_income',
            'passive_income',
            'is_paid',
            'referrals_count'
        )

    def get_referrals_count(self, obj):
        return obj.referrals.count()


# 💰 TRANSACTION SERIALIZER
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'transaction_type', 'description', 'created_at']


# 💸 WITHDRAWAL SERIALIZER
class WithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdrawal
        fields = ['id', 'amount', 'upi_id', 'status', 'created_at']
        read_only_fields = ['status']