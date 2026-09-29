from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Job, User


def _user(username, role):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-pass-123",
        role=role,
        first_name=username,
    )


class JobPostingTests(TestCase):
    def test_client_can_post_a_job(self):
        client_user = _user("client", "CLIENT")
        api = APIClient()
        token = RefreshToken.for_user(client_user)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        response = api.post(
            reverse("jobs"),
            {
                "title": "Logo refresh",
                "description": "Update the brand mark.",
                "budget": "1500.00",
                "deadline": date(2026, 10, 30).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        job = Job.objects.get(title="Logo refresh")
        self.assertEqual(job.created_by, client_user)
        self.assertEqual(job.status, "OPEN")

    def test_freelancer_cannot_post_a_job(self):
        freelancer = _user("freelancer", "FREELANCER")
        api = APIClient()
        token = RefreshToken.for_user(freelancer)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        response = api.post(
            reverse("jobs"),
            {
                "title": "Logo refresh",
                "description": "Update the brand mark.",
                "budget": "1500.00",
                "deadline": "2026-10-30",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Job.objects.count(), 0)

    def test_refresh_token_issues_a_new_access_token(self):
        user = _user("client", "CLIENT")
        refresh = RefreshToken.for_user(user)
        response = APIClient().post(
            reverse("token-refresh"),
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("access"))
