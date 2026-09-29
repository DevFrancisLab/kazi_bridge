import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import Job, Payment, User

ENQUIRY_URL = "https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts/merchant/enquiry/main"
BANK_URL = "https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts/merchant/banks/KES"


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.text = json.dumps(payload)


@override_settings(
    DEBUG=True,
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY="secret-test-key",
    PAYAZA_TENANT_ID="test",
    PAYAZA_API_BASE_URL="https://api.payaza.africa/live",
    PAYAZA_KES_ACCOUNT_REFERENCE="",
    PAYAZA_PAYOUT_BANK_CODE="",
    PAYAZA_TRANSACTION_PIN="",
    PAYAZA_SENDER_NAME="",
    PAYAZA_SENDER_PHONE="",
    PAYAZA_SENDER_ADDRESS="",
)
class PayoutConfigDiagnosticTests(TestCase):
    def _mock_get(self, enquiry, banks):
        captured = []

        def fake_get(url, headers=None, timeout=None):
            captured.append({"url": url, "headers": headers})
            if url == ENQUIRY_URL:
                return enquiry
            if url == BANK_URL:
                return banks
            raise AssertionError(url)

        return captured, fake_get

    def test_kes_account_reference_is_returned(self):
        enquiry = _Response(200, {
            "status": True,
            "data": [
                {
                    "accountName": "KES Main",
                    "payazaAccountReference": "1010000009",
                    "status": "ACTIVE",
                    "currency": "KES",
                    "country": "KEN",
                    "productCode": "PAYOUT-MAIN-KES",
                    "accountBalance": 2500,
                }
            ],
        })
        banks = _Response(200, {"status": True, "data": []})
        captured, fake_get = self._mock_get(enquiry, banks)
        with patch("users.payaza.requests.get", side_effect=fake_get):
            response = self.client.get(reverse("payaza-test-payout-config"))

        self.assertEqual(response.status_code, 200)
        account = response.json()["main_account"]
        self.assertEqual(account["currency"], "KES")
        self.assertEqual(account["country"], "KEN")
        self.assertEqual(account["status"], "ACTIVE")
        self.assertEqual(account["account_name"], "KES Main")
        self.assertEqual(account["payaza_account_reference"], "1010000009")
        self.assertTrue(response.json()["payaza_account_reference_available"])
        self.assertNotIn("accountBalance", response.content.decode())
        self.assertNotIn("secret-test-key", response.content.decode())
        self.assertNotIn("public-test-key", response.content.decode())
        self.assertEqual({item["url"] for item in captured}, {ENQUIRY_URL, BANK_URL})
        for call in captured:
            self.assertEqual(set(call["headers"]), {"Authorization", "X-TenantID", "Content-Type"})
            self.assertNotIn("X-ProductID", call["headers"])
            self.assertNotIn("payout-receptor", call["url"])
        readiness = response.json()["readiness"]
        self.assertEqual(readiness["configuration"]["kes_account_reference"], "missing")
        self.assertEqual(readiness["configuration"]["payout_bank_code"], "missing")
        self.assertEqual(readiness["configuration"]["transaction_pin"], "missing")
        self.assertEqual(readiness["payout_count"], 0)

    @override_settings(
        PAYAZA_KES_ACCOUNT_REFERENCE="5010154966",
        PAYAZA_PAYOUT_BANK_CODE="SAFKEN",
        PAYAZA_TRANSACTION_PIN="419374",
        PAYAZA_SENDER_NAME="KaziBridge",
        PAYAZA_SENDER_PHONE="254700000001",
        PAYAZA_SENDER_ADDRESS="Nairobi",
    )
    def test_readiness_reports_configuration_without_values_or_payout_call(self):
        client_user = User.objects.create_user(
            username="client",
            email="client@example.com",
            password="test-pass-123",
            role="CLIENT",
            first_name="Client",
            last_name="Owner",
        )
        User.objects.create_user(
            id=14,
            username="freelancer",
            email="freelancer@example.com",
            password="test-pass-123",
            role="FREELANCER",
            first_name="",
            last_name="",
            phone_number="+254712345678",
        )
        job = Job.objects.create(
            title="Graphic Design",
            description="Work",
            budget=Decimal("2500.00"),
            deadline=date(2026, 10, 30),
            created_by=client_user,
            status="COMPLETED",
        )
        payment = Payment.objects.create(
            id=1,
            job=job,
            client=client_user,
            freelancer_id=14,
            amount=Decimal("2500.00"),
            currency="KES",
        )
        payment.transition_to(Payment.PAYMENT_PROCESSING)
        payment.transition_to(Payment.PAYMENT_RECEIVED)
        enquiry = _Response(200, {"data": []})
        banks = _Response(200, {"data": []})
        _, fake_get = self._mock_get(enquiry, banks)
        with patch("users.payaza.requests.get", side_effect=fake_get):
            with patch("users.payaza.requests.post") as post:
                response = self.client.get(reverse("payaza-test-payout-config"))
        readiness = response.json()["readiness"]
        body = response.content.decode()
        self.assertEqual(readiness["configuration"]["kes_account_reference"], "configured")
        self.assertEqual(readiness["configuration"]["payout_bank_code"], "configured")
        self.assertEqual(readiness["configuration"]["transaction_pin"], "configured")
        self.assertEqual(readiness["configuration"]["sender_name"], "configured")
        self.assertEqual(readiness["configuration"]["sender_phone"], "configured")
        self.assertEqual(readiness["configuration"]["sender_address"], "configured")
        self.assertEqual(readiness["freelancer"]["first_name"], "missing")
        self.assertEqual(readiness["freelancer"]["last_name"], "missing")
        self.assertEqual(readiness["freelancer"]["phone"], "valid")
        self.assertEqual(readiness["payment"]["status"], "PAYMENT_RECEIVED")
        self.assertEqual(readiness["payout_count"], 0)
        self.assertNotIn("5010154966", body)
        self.assertNotIn("SAFKEN", body)
        self.assertNotIn("419374", body)
        self.assertNotIn("CONFIGURED-TEST-CODE", body)
        self.assertNotIn("254700000001", body)
        self.assertNotIn("254712345678", body)
        self.assertNotIn("secret-test-key", body)
        self.assertNotIn("Authorization", body)
        post.assert_not_called()

    def test_missing_account_reference_is_reported(self):
        enquiry = _Response(200, {
            "data": [{"accountName": "KES Main", "currency": "KES", "country": "KEN", "status": "ACTIVE"}],
        })
        banks = _Response(200, {"data": []})
        _, fake_get = self._mock_get(enquiry, banks)
        with patch("users.payaza.requests.get", side_effect=fake_get):
            response = self.client.get(reverse("payaza-test-payout-config"))

        body = response.json()
        self.assertIsNone(body["main_account"]["payaza_account_reference"])
        self.assertFalse(body["payaza_account_reference_available"])
        self.assertEqual(
            body["payaza_account_reference_message"],
            "payazaAccountReference was not returned.",
        )

    def test_kes_bank_codes_are_returned(self):
        enquiry = _Response(200, {"data": []})
        banks = _Response(200, {
            "message": "List of banks for KES",
            "data": [
                {
                    "name": "Safaricom",
                    "code": "SAFKEN",
                    "type": "mobile_money",
                    "active": True,
                    "currency_code": "KES",
                    "country_code": "KEN",
                },
                {"name": "Example Bank", "code": "EXAMPLEBANK", "type": "bank", "active": True},
            ],
        })
        _, fake_get = self._mock_get(enquiry, banks)
        with patch("users.payaza.requests.get", side_effect=fake_get):
            response = self.client.get(reverse("payaza-test-payout-config"))

        codes = response.json()["kes_payout_bank_codes"]
        self.assertEqual(codes[0]["code"], "SAFKEN")
        self.assertEqual(codes[0]["name"], "Safaricom")
        self.assertEqual(codes[0]["type"], "mobile_money")
        self.assertEqual(codes[1]["code"], "EXAMPLEBANK")
        self.assertEqual(response.json()["kes_payout_bank_code_endpoint"], "verified")

    def test_bank_code_failure_does_not_guess_a_code(self):
        enquiry = _Response(200, {
            "data": [{
                "accountName": "KES Main",
                "currency": "KES",
                "payazaAccountReference": "1010000009",
            }],
        })
        banks = _Response(500, {"message": "unavailable secret-test-key"})
        _, fake_get = self._mock_get(enquiry, banks)
        with patch("users.payaza.requests.get", side_effect=fake_get):
            response = self.client.get(reverse("payaza-test-payout-config"))

        body = response.json()
        self.assertEqual(body["kes_payout_bank_codes"], [])
        self.assertEqual(body["bank_code_error"]["error"], "payaza_rejected")
        self.assertNotIn("secret-test-key", response.content.decode())
        self.assertNotIn("SAFKEN", response.content.decode())
        self.assertNotIn("MPESA", response.content.decode())
        self.assertEqual(body["main_account"]["payaza_account_reference"], "1010000009")

    @override_settings(DEBUG=False)
    def test_endpoint_is_hidden_when_debug_is_off(self):
        response = self.client.get(reverse("payaza-test-payout-config"))
        self.assertEqual(response.status_code, 404)
