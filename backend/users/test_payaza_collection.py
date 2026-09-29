import base64
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import Job, Payment, User

COLLECTION_URL = "https://api.payaza.africa/live/subsidiary/collections/v1/process-collection"
STATUS_URL = "https://api.payaza.africa/live/subsidiary/collections/v1/check-status"


class _Response:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)


def _user(username, role):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-pass-123",
        role=role,
        first_name="Amina",
        last_name="Otieno",
        phone_number="+254712345678",
    )


@override_settings(
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY="secret-test-key",
    PAYAZA_TENANT_ID="test",
    PAYAZA_PRODUCT_ID="app",
)
class PayazaKesCollectionTests(TestCase):
    def setUp(self):
        self.client_user = _user("client", "CLIENT")
        self.other_client = _user("other-client", "CLIENT")
        self.freelancer = _user("freelancer", "FREELANCER")
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)
        self.other_api = APIClient()
        self.other_api.force_authenticate(self.other_client)
        self.freelancer_api = APIClient()
        self.freelancer_api.force_authenticate(self.freelancer)
        self.payment = self._payment()

    def _payment(self, currency="KES", owner=None):
        owner = owner or self.client_user
        job = Job.objects.create(
            title="Design project",
            description="Work",
            budget=Decimal("110000.00"),
            deadline=date(2026, 10, 30),
            created_by=owner,
            status="IN_PROGRESS",
        )
        return Payment.objects.create(
            job=job,
            client=owner,
            freelancer=self.freelancer,
            amount=Decimal("110000.00"),
            currency=currency,
        )

    def _post(self, api=None, payment=None, bank_code="SAFKEN"):
        return (api or self.api).post(
            reverse("payment-payaza", args=[(payment or self.payment).id]),
            {"customer_bank_code": bank_code},
            format="json",
        )

    def test_client_initializes_collection_without_marking_it_received(self):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Response(200, {
                "response_code": "09",
                "response_message": "PENDING",
                "payment_token": "prov-ref-1",
                "transaction_reference": self.payment.transaction_reference,
            })

        with patch("users.payaza.requests.post", side_effect=fake_post):
            with self.assertLogs("users.payaza", level="INFO") as logs:
                response = self._post()

        encoded = base64.b64encode(b"public-test-key").decode("ascii")
        body = response.json()
        logged = "\n".join(logs.output)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["initialized"])
        self.assertEqual(body["payaza_response_code"], "09")
        self.assertEqual(captured["url"], COLLECTION_URL)
        self.assertEqual(captured["headers"]["Authorization"], f"Payaza {encoded}")
        self.assertTrue(captured["headers"]["Authorization"].startswith("Payaza "))
        self.assertEqual(captured["headers"]["X-TenantID"], "test")
        self.assertEqual(captured["headers"]["X-ProductID"], "app")
        self.assertEqual(captured["headers"]["Content-Type"], "application/json")
        self.assertEqual(captured["json"]["transaction_reference"], self.payment.transaction_reference)
        self.assertEqual(Decimal(str(captured["json"]["amount"])), Decimal("110000.00"))
        self.assertEqual(captured["json"]["currency_code"], "KES")
        self.assertEqual(captured["json"]["country_code"], "KE")
        self.assertEqual(captured["json"]["customer_bank_code"], "SAFKEN")
        self.assertEqual(captured["json"]["customer_number"], "254712345678")
        self.assertEqual(captured["json"]["customer_email"], self.client_user.email)
        self.assertEqual(captured["json"]["customer_first_name"], "Amina")
        self.assertEqual(captured["json"]["customer_last_name"], "Otieno")
        self.assertNotIn("secret-test-key", json.dumps(captured["headers"]))
        self.assertNotIn("secret-test-key", json.dumps(captured["json"]))
        self.assertNotIn("secret-test-key", response.content.decode())
        self.assertNotIn("public-test-key", response.content.decode())
        self.assertNotIn(encoded, response.content.decode())
        self.assertNotIn("secret-test-key", logged)
        self.assertNotIn("public-test-key", logged)
        self.assertNotIn("Authorization", logged)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)
        self.assertNotEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(self.payment.provider_transaction_reference, "prov-ref-1")

    def test_other_client_freelancer_and_anonymous_cannot_initialize(self):
        with patch("users.payaza.requests.post") as post:
            other = self._post(api=self.other_api)
            freelancer = self._post(api=self.freelancer_api)
            anonymous = APIClient().post(
                reverse("payment-payaza", args=[self.payment.id]),
                {"customer_bank_code": "SAFKEN"},
                format="json",
            )
        self.assertEqual(other.status_code, 404)
        self.assertEqual(freelancer.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)
        post.assert_not_called()

    def test_non_pending_and_non_kes_payments_are_rejected(self):
        processing = self._payment()
        processing.transition_to(Payment.PAYMENT_PROCESSING)
        received = self._payment()
        received.transition_to(Payment.PAYMENT_PROCESSING)
        received.transition_to(Payment.PAYMENT_RECEIVED)
        failed = self._payment()
        failed.transition_to(Payment.PAYMENT_FAILED)
        foreign = self._payment(currency="USD")

        with patch("users.payaza.requests.post") as post:
            processing_response = self._post(payment=processing)
            received_response = self._post(payment=received)
            failed_response = self._post(payment=failed)
            foreign_response = self._post(payment=foreign)

        self.assertEqual(processing_response.status_code, 400)
        self.assertEqual(processing_response.json()["error"], "invalid_payment_state")
        self.assertEqual(received_response.status_code, 400)
        self.assertEqual(received_response.json()["error"], "invalid_payment_state")
        self.assertEqual(failed_response.status_code, 400)
        self.assertEqual(failed_response.json()["error"], "invalid_payment_state")
        self.assertEqual(foreign_response.status_code, 400)
        self.assertEqual(foreign_response.json()["error"], "payment_not_payable")
        post.assert_not_called()
        received.refresh_from_db()
        self.assertEqual(received.status, Payment.PAYMENT_RECEIVED)

    def test_missing_customer_information_is_reported(self):
        self.client_user.last_name = ""
        self.client_user.save(update_fields=["last_name"])
        with patch("users.payaza.requests.post") as post:
            response = self._post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "missing_customer_information")
        self.assertIn("customer_last_name", response.json()["message"])
        post.assert_not_called()
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PAYMENT_PENDING)

    def test_payaza_rejection_timeout_and_malformed_body_do_not_change_payment(self):
        rejected = _Response(400, {"response_message": "Invalid API key public-test-key"})
        with patch("users.payaza.requests.post", return_value=rejected):
            rejection = self._post()
        self.assertEqual(rejection.status_code, 502)
        self.assertEqual(rejection.json()["error"], "payaza_rejected")
        self.assertNotIn("public-test-key", rejection.content.decode())
        self.assertNotIn("secret-test-key", rejection.content.decode())

        with patch("users.payaza.requests.post", side_effect=requests.Timeout):
            timeout = self._post()
        self.assertEqual(timeout.status_code, 504)
        self.assertEqual(timeout.json()["error"], "payaza_unavailable")

        with patch("users.payaza.requests.post", return_value=_Response(200, "not-json")):
            malformed = self._post()
        self.assertEqual(malformed.status_code, 502)
        self.assertEqual(malformed.json()["error"], "payaza_unavailable")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PAYMENT_PENDING)
        self.assertIsNone(self.payment.provider_transaction_reference)

    def test_repeated_initialization_does_not_create_another_provider_transaction(self):
        with patch(
            "users.payaza.requests.post",
            return_value=_Response(200, {
                "response_code": "09",
                "response_message": "PENDING",
                "payment_token": "prov-ref-1",
            }),
        ) as post:
            first = self._post()
            second = self._post()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json()["error"], "invalid_payment_state")
        self.assertEqual(post.call_count, 1)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.provider_transaction_reference, "prov-ref-1")
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)

    def test_status_initialized_does_not_mark_received_and_completed_does(self):
        self.payment.transition_to(Payment.PAYMENT_PROCESSING)
        initialized = _Response(200, {
            "response_code": "09",
            "transaction_status": "Initialized",
            "payer_account_number": "254712345678",
        })
        with patch("users.payaza.requests.get", return_value=initialized) as get:
            pending = self.api.get(reverse("payment-payaza-status", args=[self.payment.id]))
        self.assertEqual(pending.status_code, 200)
        self.assertFalse(pending.json()["local_status_changed"])
        self.assertNotIn("254712345678", pending.content.decode())
        self.assertEqual(get.call_args.args[0], STATUS_URL)
        self.assertEqual(get.call_args.kwargs["params"]["transaction_reference"], self.payment.transaction_reference)
        self.assertEqual(get.call_args.kwargs["params"]["country_code"], "KE")
        self.assertEqual(get.call_args.kwargs["headers"]["X-TenantID"], "test")
        self.assertEqual(get.call_args.kwargs["headers"]["X-ProductID"], "app")
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)

        completed = _Response(200, {
            "response_code": "00",
            "transaction_status": "Completed",
        })
        with patch("users.payaza.requests.get", return_value=completed):
            done = self.api.get(reverse("payment-payaza-status", args=[self.payment.id]))
        self.assertEqual(done.status_code, 200)
        self.assertTrue(done.json()["local_status_changed"])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
