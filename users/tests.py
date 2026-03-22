from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class UserTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create a referrer user
        self.referrer = User.objects.create_user(
            username="Referrer1",
            email="ref1@test.com",
            password="Testpass123!"
        )
        self.referrer.is_verified = True
        self.referrer.is_paid = True
        self.referrer.save()

    def test_register(self):
        """Test user registration"""
        url = reverse('register')

        data = {
            "username": "NewUser1",
            "email": "newuser1@test.com",
            "password": "Testpass123!",
            "password2": "Testpass123!",
            "referral_code": self.referrer.referral_code
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser1@test.com").exists())

    def test_login(self):
        """Test login after verification"""

        url = reverse('login')

        data = {
            "email": "ref1@test.com",
            "password": "Testpass123!"
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_user_dashboard(self):
        """Test user dashboard (wallet view)"""

        self.client.force_authenticate(user=self.referrer)

        url = reverse('user-detail')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.referrer.email)