"""
Fraud Detection Utilities for DreamsHelix
- Prevent fake accounts, referral abuse, and spam
"""

import re
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from .models import CustomUser


# 🚫 Disposable email domains (expandable)
DISPOSABLE_DOMAINS = {
    "tempmail.com",
    "10minutemail.com",
    "mailinator.com",
    "guerrillamail.com",
    "yopmail.com"
}


# 🚫 Check disposable email
def is_disposable_email(email):
    if not email or '@' not in email:
        return True
    domain = email.split('@')[-1].lower()
    return domain in DISPOSABLE_DOMAINS


# 🚫 Detect suspicious email patterns
def is_suspicious_email(email):
    pattern = r'^[a-zA-Z]+[0-9]{4,}@'
    return re.match(pattern, email) is not None


# 🚫 IP abuse detection
def is_ip_suspicious(ip):
    if not ip:
        return False

    key = f"ip_attempts_{ip}"
    attempts = cache.get(key, 0)

    if attempts >= 5:
        return True

    cache.set(key, attempts + 1, timeout=3600)
    return False


# 🚫 Referral farming (time-based)
def is_referral_farming(referrer):
    if not referrer:
        return False

    today = timezone.now() - timedelta(days=1)

    count = CustomUser.objects.filter(
        referred_by=referrer,
        date_joined__gte=today
    ).count()

    return count >= 10


# 🚫 Multiple accounts detection (same domain abuse)
def is_multi_account(email):
    if not email or '@' not in email:
        return False

    domain = email.split('@')[-1]

    count = CustomUser.objects.filter(
        email__endswith=f"@{domain}"
    ).count()

    return count > 50  # relaxed threshold


# 🚫 Self referral check
def is_self_referral(email, referral_code):
    # ✅ FIX: handle empty referral
    if not referral_code:
        return False

    try:
        user = CustomUser.objects.get(referral_code=referral_code)
        return user.email == email
    except CustomUser.DoesNotExist:
        return False


# 🚫 Duplicate referral (same user reused)
def is_duplicate_referral(user, referrer):
    if not user or not referrer:
        return False
    return user.referred_by == referrer


# ✅ Get valid referrer
def get_valid_referrer(referral_code):
    # ✅ FIX: avoid DB hit if empty
    if not referral_code:
        return None

    try:
        return CustomUser.objects.get(referral_code=referral_code)
    except CustomUser.DoesNotExist:
        return None