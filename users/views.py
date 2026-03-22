"""
DreamsHelix Views
- Auth (Register, Login)
- OTP Verification
- Wallet + Withdrawal
- Admin Dashboard
- Payment Integration
"""

from decimal import Decimal
import hmac
import hashlib
import razorpay

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView

from .models import CustomUser, Transaction, Withdrawal, Payment
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    TransactionSerializer
)
from .fraud_utils import get_valid_referrer
from .utils import generate_otp


# 🔐 Admin Permission
class IsAdminUserCustom(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


# ✅ Home API
def home(request):
    return HttpResponse("DreamsHelix Backend is running!")


# 🚀 REGISTER
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "message": "User registered successfully. Please verify OTP.",
            "email": user.email
        }, status=status.HTTP_201_CREATED)


# 🔐 LOGIN
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data
            user = data['user']

            return Response({
                "message": "Login successful",
                "user": UserSerializer(user).data,
                "access": data['access'],
                "refresh": data['refresh']
            })

        return Response(serializer.errors, status=400)


# 👤 USER DETAILS
class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# 🔐 VERIFY OTP
class VerifyOTPView(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if user.is_verified:
            return Response({"message": "Already verified"})

        if user.otp != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        if not user.is_otp_valid():
            return Response({"error": "OTP expired"}, status=400)

        # ✅ Verify user
        user.is_verified = True
        user.otp = None
        user.save()

        # 🔥 APPLY REFERRAL AFTER VERIFICATION (SAFE)
        referral_code = request.session.get('pending_referral', None)

        if referral_code:
            referrer = get_valid_referrer(referral_code)

            # ✅ Check valid + paid
            if referrer and referrer.is_paid:

                # 🔒 Prevent duplicate linking
                if not user.referred_by:
                    user.referred_by = referrer
                    user.save()

                    # 💰 Active income
                    referrer.active_income += 500
                    referrer.save()

                    Transaction.objects.create(
                        user=referrer,
                        amount=500,
                        transaction_type='ACTIVE',
                        description=f"Referral bonus from {user.email}"
                    )

                    # 💰 Passive income (level 2)
                    if referrer.referred_by:
                        second = referrer.referred_by
                        second.passive_income += 100
                        second.save()

                        Transaction.objects.create(
                            user=second,
                            amount=100,
                            transaction_type='PASSIVE',
                            description=f"Passive income from {user.email}"
                        )

        # ✅ CLEANUP session (VERY IMPORTANT)
        if 'pending_referral' in request.session:
            del request.session['pending_referral']

        return Response({"message": "Account verified successfully"})


# 🔁 RESEND OTP
class ResendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        user.otp = generate_otp()
        user.otp_created_at = timezone.now()
        user.save()

        return Response({"message": "OTP resent successfully"})


# 💰 WALLET
class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        transactions = Transaction.objects.filter(user=user).order_by('-created_at')

        return Response({
            "email": user.email,
            "active_income": user.active_income,
            "passive_income": user.passive_income,
            "total_income": user.active_income + user.passive_income,
            "transactions": TransactionSerializer(transactions, many=True).data
        })


# 💸 WITHDRAW REQUEST
class WithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        try:
            amount = Decimal(request.data.get('amount'))
        except:
            return Response({"error": "Invalid amount"}, status=400)

        upi_id = request.data.get('upi_id')

        total_balance = user.active_income + user.passive_income

        if amount < 500:
            return Response({"error": "Minimum withdrawal is ₹500"}, status=400)

        if amount > total_balance:
            return Response({"error": "Insufficient balance"}, status=400)

        if Withdrawal.objects.filter(user=user, status='PENDING').exists():
            return Response({"error": "Pending request exists"}, status=400)

        Withdrawal.objects.create(user=user, amount=amount, upi_id=upi_id)

        return Response({"message": "Withdrawal request submitted"})


# 📊 ADMIN DASHBOARD
class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def get(self, request):
        return Response({
            "total_users": CustomUser.objects.count(),
            "verified_users": CustomUser.objects.filter(is_verified=True).count(),
            "total_active_income": CustomUser.objects.aggregate(total=Sum('active_income'))['total'] or 0,
            "total_passive_income": CustomUser.objects.aggregate(total=Sum('passive_income'))['total'] or 0,
            "total_transactions": Transaction.objects.count(),
            "pending_withdrawals": Withdrawal.objects.filter(status='PENDING').count(),
        })


# 🏆 TOP REFERRERS
class TopReferrersView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def get(self, request):
        users = CustomUser.objects.annotate(
            referral_count=Count('referrals')
        ).order_by('-referral_count')[:10]

        return Response([
            {
                "email": u.email,
                "referrals": u.referral_count,
                "active_income": u.active_income
            } for u in users
        ])


# 🚨 FRAUD MONITOR
class FraudMonitorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserCustom]

    def get(self, request):
        users = CustomUser.objects.annotate(
            referral_count=Count('referrals')
        ).filter(referral_count__gt=10)

        return Response([
            {
                "email": u.email,
                "referrals": u.referral_count
            } for u in users
        ])


# 💳 CREATE ORDER
class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        ))

        amount = 6999 * 100

        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        Payment.objects.create(
            user=request.user,
            amount=6999,
            razorpay_order_id=order['id']
        )

        return Response({
            "order_id": order['id'],
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID
        })


# 💳 VERIFY PAYMENT
class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            payment = Payment.objects.get(
                razorpay_order_id=request.data.get('order_id')
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        generated_signature = hmac.new(
            bytes(settings.RAZORPAY_KEY_SECRET, 'utf-8'),
            bytes(f"{request.data.get('order_id')}|{request.data.get('payment_id')}", 'utf-8'),
            hashlib.sha256
        ).hexdigest()

        if generated_signature == request.data.get('signature'):
            payment.is_verified = True
            payment.razorpay_payment_id = request.data.get('payment_id')
            payment.save()

            request.user.is_paid = True
            request.user.save()

            return Response({"message": "Payment successful"})

        return Response({"error": "Verification failed"}, status=400)