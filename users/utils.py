"""
Utility functions for DreamsHelix
- Secure OTP generation
"""

import secrets


def generate_otp(length=6):
    """
    Generate a secure numeric OTP

    Args:
        length (int): Length of OTP (default = 6)

    Returns:
        str: Secure OTP string
    """

    digits = "0123456789"
    otp = ''.join(secrets.choice(digits) for _ in range(length))
    return otp