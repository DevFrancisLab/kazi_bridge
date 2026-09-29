import base64
import hashlib
import hmac
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import Earnings, Job, Payment, User

SECRET = "secret-test-key"


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


def _sign(raw_body):
    digest = hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha512).digest()
    return base64.b64encode(digest).decode("ascii")


def _status_result(outcome, provider=None, error=None, message=None):
    codes = {"completed": "00", "failed": "06", "pending": "09"}
    statuses = {"completed": "Completed", "failed": "Failed", "pending": "Initialized"}
    return {
        "ok": error is None,
        "error": error,
        "message": message,
        "http_status": None if error else 200,
        "initialized": False,
        "outcome": outcome,
        "provider_transaction_reference": provider,
        "response_code": None if error else codes[outcome],
        "response_message": None,
        "transaction_status": None if error else statuses[outcome],
    }


@override_settings(
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY=SECRET,
    PAYAZA_TENANT_ID="test",
    PAYAZA_PRODUCT_ID="app",
)
class PayazaCollectionWebhookTests(TestCase):
    def setUp(self):
        self.client_user = _user("client", "CLIENT")
        self.freelancer = _user("freelancer", "FREELANCER")
        self.api = APIClient()
        self.payment = self._payment()
        self.payment.transition_to(Payment.PAYMENT_PROCESSING)

    def _payment(self):
        job = Job.objects.create(
            title="Design project",
            description="Work",
            budget=Decimal("110000.00"),
            deadline=date(2026, 10, 30),
            created_by=self.client_user,
            status="IN_PROGRESS",
        )
        return Payment.objects.create(
            job=job,
            client=self.client_user,
            freelancer=self.freelancer,
            amount=Decimal("110000.00"),
            currency="KES",
        )

    def _body(self, payment=None, session_id="P-C-100", status_text="Completed", transaction_status="Funds Received"):
        payment = payment or self.payment
        payload = {
            "transaction_reference": session_id,
            "transaction_status": transaction_status,
            "merchant_reference": payment.transaction_reference,
            "status": status_text,
            "session_id": session_id,
            "channel": "KENYA_COLLECTIONS",
            "currency_code": "KES",
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def _post(self, raw, signature=None):
        return self.api.post(
            reverse("payment-payaza-webhook"),
            data=raw,
            content_type="application/json",
            HTTP_X_PAYAZA_SIGNATURE=signature if signature is not None else _sign(raw),
        )

    def test_successful_webhook_uses_verified_status_and_creates_one_earning(self):
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("completed"),
        ) as status_check:
            with self.assertLogs("users.payment_views", level="INFO") as logs:
                response = self._post(raw)
                duplicate = self._post(raw)

        self.payment.refresh_from_db()
        logged = "\n".join(logs.output)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["local_status_changed"])
        self.assertEqual(response.json()["payment_status"], Payment.PAYMENT_RECEIVED)
        self.assertEqual(duplicate.status_code, 200)
        self.assertFalse(duplicate.json()["local_status_changed"])
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(self.payment.provider_transaction_reference, "P-C-100")
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(status_check.call_count, 2)
        self.assertEqual(status_check.call_args.args[0].transaction_reference, self.payment.transaction_reference)
        self.assertNotIn(SECRET, json.dumps(response.json()))
        self.assertNotIn(SECRET, json.dumps(duplicate.json()))
        self.assertNotIn(SECRET, logged)
        self.assertNotIn("public-test-key", logged)

    def test_failed_verification_marks_payment_failed(self):
        raw = self._body(status_text="Completed", transaction_status="Funds Received")
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("failed"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.PAYMENT_FAILED)
        self.assertFalse(Earnings.objects.filter(payment=self.payment).exists())

    def test_pending_verification_leaves_processing_payment_unchanged(self):
        raw = self._body(status_text="Completed", transaction_status="Funds Received")
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("pending"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["local_status_changed"])
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)
        self.assertFalse(Earnings.objects.filter(payment=self.payment).exists())

    def test_unknown_transaction_reference_does_not_create_a_payment(self):
        before = Payment.objects.count()
        payload = {
            "merchant_reference": "KZB-20260929-DOESNOTEXIST",
            "session_id": "P-C-404",
            "status": "Completed",
        }
        raw = json.dumps(payload).encode("utf-8")
        with patch("users.payment_views.fetch_kes_collection_status") as status_check:
            response = self._post(raw)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "unknown_transaction_reference")
        self.assertEqual(Payment.objects.count(), before)
        status_check.assert_not_called()

    def test_missing_transaction_reference_is_rejected(self):
        raw = json.dumps({"status": "Completed", "session_id": "P-C-100"}).encode("utf-8")
        with patch("users.payment_views.fetch_kes_collection_status") as status_check:
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "missing_transaction_reference")
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)
        status_check.assert_not_called()

    def test_malformed_json_is_rejected(self):
        raw = b"{not-json"
        with patch("users.payment_views.fetch_kes_collection_status") as status_check:
            response = self._post(raw)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_webhook")
        status_check.assert_not_called()

    def test_already_received_webhook_does_not_duplicate_earnings(self):
        self.payment.transition_to(Payment.PAYMENT_RECEIVED)
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("completed"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["local_status_changed"])
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)

    def test_already_failed_webhook_does_not_change_status(self):
        self.payment.transition_to(Payment.PAYMENT_FAILED)
        raw = self._body(status_text="Failed", transaction_status="Transaction Failed")
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("failed"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.PAYMENT_FAILED)
        self.assertFalse(Earnings.objects.filter(payment=self.payment).exists())

    def test_cancelled_payment_is_left_unchanged(self):
        self.payment.transition_to(Payment.PAYMENT_CANCELLED)
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("completed"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.PAYMENT_CANCELLED)
        self.assertFalse(Earnings.objects.filter(payment=self.payment).exists())

    def test_status_query_success_is_what_marks_the_payment_received(self):
        raw = self._body(status_text="Failed", transaction_status="Transaction Failed")
        captured = {}

        def fake_get(url, params=None, headers=None, timeout=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return type("Response", (), {
                "status_code": 200,
                "text": json.dumps({
                    "response_code": "00",
                    "transaction_status": "Funds Received",
                    "transaction_reference": self.payment.transaction_reference,
                }),
            })()

        with patch("users.payaza.requests.get", side_effect=fake_get):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(captured["params"]["transaction_reference"], self.payment.transaction_reference)
        self.assertEqual(captured["params"]["country_code"], "KE")
        self.assertNotIn(SECRET, json.dumps(captured["headers"]))
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)

    def test_provider_verification_timeout_leaves_payment_processing(self):
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("unknown", error="payaza_unavailable", message="Payaza request timed out."),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["error"], "payaza_unavailable")
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)
        self.assertFalse(Earnings.objects.filter(payment=self.payment).exists())

    def test_provider_verification_unavailable_leaves_payment_processing(self):
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("unknown", error="payaza_unavailable", message="Could not connect to Payaza."),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)

    def test_echoed_kazi_reference_is_not_stored_as_provider_reference(self):
        local = self.payment.transaction_reference
        raw = self._body(session_id=local)
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("completed", provider=local),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.payment.provider_transaction_reference)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)

    def test_existing_provider_reference_is_not_replaced(self):
        self.payment.provider_transaction_reference = "prov-kept"
        self.payment.save(update_fields=["provider_transaction_reference", "updated_at"])
        raw = self._body(session_id="P-C-other")
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("pending", provider="prov-from-status"),
        ):
            response = self._post(raw)

        self.payment.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.provider_transaction_reference, "prov-kept")

    def test_webhook_does_not_require_jwt(self):
        raw = self._body()
        with patch(
            "users.payment_views.fetch_kes_collection_status",
            return_value=_status_result("pending"),
        ):
            response = self._post(raw)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payment_status"], Payment.PAYMENT_PROCESSING)

    def test_invalid_signature_is_rejected(self):
        raw = self._body()
        with patch("users.payment_views.fetch_kes_collection_status") as status_check:
            with self.assertLogs("users.payment_views", level="ERROR") as logs:
                response = self._post(raw, signature="not-a-valid-signature")

        self.payment.refresh_from_db()
        logged = "\n".join(logs.output)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_signature")
        self.assertEqual(self.payment.status, Payment.PAYMENT_PROCESSING)
        self.assertFalse(self.payment.provider_transaction_reference)
        status_check.assert_not_called()
        self.assertNotIn(SECRET, json.dumps(response.json()))
        self.assertNotIn(SECRET, logged)
