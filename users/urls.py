from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    UserDetailView,
    VerifyOTPView,
    ResendOTPView,
    WalletView,
    WithdrawRequestView,
    AdminDashboardView,
    TopReferrersView,
    FraudMonitorView,
    CreateOrderView,
    VerifyPaymentView
)

urlpatterns = [
    # 🔐 Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    # 👤 User
    path('me/', UserDetailView.as_view(), name='user-detail'),

    # 🔐 OTP
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),

    # 💰 Wallet
    path('wallet/', WalletView.as_view(), name='wallet'),

    # 💸 Withdrawal
    path('withdraw/', WithdrawRequestView.as_view(), name='withdraw'),

    # 📊 Admin APIs
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/top-referrers/', TopReferrersView.as_view(), name='top-referrers'),
    path('admin/fraud-monitor/', FraudMonitorView.as_view(), name='fraud-monitor'),

    # 💳 Payment
    path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
]